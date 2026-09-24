import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.models import AlertLevel, Channel, ConversationState, MessageRole, SentBy
from app.services import conversations, llm, rag, triage

router = APIRouter(prefix="/chat", tags=["chat"])

HISTORY_LIMIT = 12

AI_DISCLAIMER_TEMPLATE = (
    "Olá! Este é um assistente virtual (inteligência artificial) para dúvidas "
    "iniciais sobre o atendimento de {name}. Não sou uma pessoa e não substituo "
    "consulta ou atendimento clínico."
)


@router.post("/simulate", response_model=schemas.ChatResponse)
def simulate_chat(payload: schemas.ChatRequest, db: Session = Depends(get_db)):
    """Canal simulado: mesma lógica do WhatsApp, sem depender da Meta.

    O `session_id` faz aqui o papel que o número de telefone faz no
    WhatsApp — é o identificador do contato dentro do canal.
    """
    professional = db.query(models.Professional).filter_by(slug=payload.professional_slug).first()
    if not professional:
        raise HTTPException(status_code=404, detail="Profissional não encontrado")

    session_id = payload.session_id or str(uuid.uuid4())
    contact = conversations.get_or_create_contact(
        db, professional, Channel.SIMULATOR, external_id=session_id
    )
    conversation, is_new = conversations.get_or_create_conversation(db, contact)

    disclaimer = None
    if is_new:
        disclaimer = AI_DISCLAIMER_TEMPLATE.format(name=professional.name)
        conversations.record_message(
            db, conversation, MessageRole.ASSISTANT, disclaimer, sent_by=SentBy.SYSTEM
        )

    user_message = conversations.record_message(db, conversation, MessageRole.USER, payload.message)

    # A triagem roda antes de tudo e em qualquer estado da conversa:
    # mesmo com a profissional no controle ou com um alerta anterior, um
    # novo sinal de risco sempre é registrado.
    history = conversations.recent_history(db, conversation, HISTORY_LIMIT)
    risk = triage.assess(payload.message, history, professional.audience_description)
    if risk and risk.level in (AlertLevel.EMERGENCY, AlertLevel.POSSIBLE_RISK):
        conversations.raise_safety_alert(
            db, conversation, user_message, risk.level, risk.trigger, risk.excerpt
        )
    elif risk and risk.level == AlertLevel.INTENSE_SUFFERING:
        conversations.mark_needs_attention(db, conversation)
    # Na dúvida sobre segurança, a profissional é avisada e a conversa
    # segue normalmente; só a emergência interrompe o fluxo.
    if risk and risk.level == AlertLevel.EMERGENCY:
        conversations.record_message(
            db, conversation, MessageRole.ASSISTANT, triage.EMERGENCY_MESSAGE, sent_by=SentBy.SYSTEM
        )
        return schemas.ChatResponse(
            session_id=session_id, reply=triage.EMERGENCY_MESSAGE, disclaimer=disclaimer
        )

    # Com a profissional no controle, ou depois de um alerta, o bot fica
    # em silêncio. Não há retomada automática: só a profissional libera o
    # bot de novo, pelo painel (decisão da Marília em 23/09).
    if conversation.state in (ConversationState.HUMAN, ConversationState.EMERGENCY_HOLD):
        return schemas.ChatResponse(session_id=session_id, reply=None, disclaimer=disclaimer)

    chunks, metadatas = rag.query(professional.slug, payload.message)
    system_prompt = llm.build_system_prompt(professional.name, professional.voice_tone, chunks)

    reply = llm.generate_reply(system_prompt, history)

    conversations.record_message(
        db, conversation, MessageRole.ASSISTANT, reply, sent_by=SentBy.BOT
    )

    sources = sorted({meta["filename"] for meta in metadatas}) if metadatas else []

    return schemas.ChatResponse(session_id=session_id, reply=reply, sources=sources, disclaimer=disclaimer)
