import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.models import AlertLevel, Channel, ConversationState, MessageRole, SentBy
from app.services import auth, conversations, guidelines, handoff, llm, notifications, rag, triage

router = APIRouter(prefix="/chat", tags=["chat"])

HISTORY_LIMIT = 12

# Primeira mensagem de toda conversa, antes de qualquer resposta do
# modelo. Diz o nome da assistente e que ela é uma IA (o aviso de IA
# nunca sai do fluxo, ver planejamento-mvp-9out.md, seção 8).
AI_DISCLAIMER_TEMPLATE = (
    "Oi! Eu sou a {assistant}, assistente virtual com inteligência artificial "
    "de {name}. Posso tirar suas dúvidas sobre o atendimento. Não sou uma "
    "pessoa e não substituo consulta ou atendimento clínico."
)


@router.post("/simulate", response_model=schemas.ChatResponse)
def simulate_chat(
    payload: schemas.ChatRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.current_user),
):
    """Canal simulado: mesma lógica do WhatsApp, sem depender da Meta.

    O `session_id` faz aqui o papel que o número de telefone faz no
    WhatsApp — é o identificador do contato dentro do canal.
    """
    # Só a própria profissional testa a MarIA dela: o simulador gasta a
    # chave da API e grava conversas no consultório.
    professional = db.query(models.Professional).filter_by(slug=payload.professional_slug).first()
    if not professional or not user.owns(professional.id):
        raise HTTPException(status_code=404, detail="Profissional não encontrado")

    session_id = payload.session_id or str(uuid.uuid4())
    contact = conversations.get_or_create_contact(
        db, professional, Channel.SIMULATOR, external_id=session_id
    )
    conversation, is_new = conversations.get_or_create_conversation(db, contact)

    disclaimer = None
    if is_new:
        disclaimer = AI_DISCLAIMER_TEMPLATE.format(
            assistant=guidelines.ASSISTANT_NAME, name=professional.name
        )
        conversations.record_message(
            db, conversation, MessageRole.ASSISTANT, disclaimer, sent_by=SentBy.SYSTEM
        )

    user_message = conversations.record_message(db, conversation, MessageRole.USER, payload.message)

    # A triagem roda antes de tudo e em qualquer estado da conversa:
    # mesmo com a profissional no controle ou com um alerta anterior, um
    # novo sinal de risco sempre é registrado.
    history = conversations.recent_history(db, conversation, HISTORY_LIMIT)
    risk = triage.assess(payload.message, history, professional.audience_description)
    info = {"triage_level": risk.level if risk else "normal", "alert_created": False}
    if risk and risk.level in (AlertLevel.EMERGENCY, AlertLevel.POSSIBLE_RISK):
        alert = conversations.raise_safety_alert(
            db, conversation, user_message, risk.level, risk.trigger, risk.excerpt
        )
        # O e-mail sai depois da resposta ao contato: um servidor de
        # e-mail lento não atrasa a mensagem de emergência.
        background_tasks.add_task(notifications.notify_alert, alert.id)
        info["alert_created"] = True
    elif risk and risk.level == AlertLevel.INTENSE_SUFFERING:
        conversations.mark_needs_attention(db, conversation)
    # Na dúvida sobre segurança, a profissional é avisada e a conversa
    # segue normalmente; só a emergência interrompe o fluxo.
    if risk and risk.level == AlertLevel.EMERGENCY:
        conversations.record_message(
            db, conversation, MessageRole.ASSISTANT, triage.EMERGENCY_MESSAGE, sent_by=SentBy.SYSTEM
        )
        return _response(session_id, conversation, triage.EMERGENCY_MESSAGE, disclaimer, **info)

    # Com a profissional no controle, ou depois de um alerta, o bot fica
    # em silêncio. Não há retomada automática: só a profissional libera o
    # bot de novo, pelo painel (decisão da Marília em 23/09).
    if conversation.state in (ConversationState.HUMAN, ConversationState.EMERGENCY_HOLD):
        return _response(session_id, conversation, None, disclaimer, **info)

    # Recusa do bot ou pedido para falar com a profissional: texto fixo, sem passar pelo
    # modelo. Ver `services/handoff.py` (inclui o botão "Em consulta").
    request = handoff.classify_request(payload.message, professional)
    if request:
        already_awaiting = conversation.awaiting_reply_since is not None
        reply, alert = handoff.handle_human_request(db, professional, conversation, user_message, request)
        if alert:
            background_tasks.add_task(notifications.notify_alert, alert.id)
            info["alert_created"] = True
        elif not already_awaiting:
            # A recusa do bot já avisa pelo e-mail do alerta; o pedido
            # simples avisa uma vez, até ela responder.
            background_tasks.add_task(notifications.notify_human_request, conversation.id)
        return _response(session_id, conversation, reply, disclaimer, handoff=request, **info)

    chunks, metadatas = rag.query(professional.slug, payload.message)
    system_prompt = llm.build_system_prompt(professional, chunks)

    reply = llm.generate_reply(system_prompt, history)

    conversations.record_message(
        db, conversation, MessageRole.ASSISTANT, reply, sent_by=SentBy.BOT
    )

    sources = sorted({meta["filename"] for meta in metadatas}) if metadatas else []

    return _response(session_id, conversation, reply, disclaimer, sources, **info)


def _response(
    session_id, conversation, reply, disclaimer, sources=None, triage_level="normal", alert_created=False, handoff=None
) -> schemas.ChatResponse:
    return schemas.ChatResponse(
        session_id=session_id,
        conversation_id=conversation.id,
        state=conversation.state,
        reply=reply,
        sources=sources or [],
        disclaimer=disclaimer,
        triage_level=triage_level,
        alert_created=alert_created,
        handoff=handoff,
    )
