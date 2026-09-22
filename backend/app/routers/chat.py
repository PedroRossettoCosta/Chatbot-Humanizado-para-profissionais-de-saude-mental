import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.models import Channel, MessageRole, SentBy
from app.services import conversations, llm, rag

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

    conversations.record_message(db, conversation, MessageRole.USER, payload.message)

    chunks, metadatas = rag.query(professional.slug, payload.message)
    system_prompt = llm.build_system_prompt(professional.name, professional.voice_tone, chunks)
    history = conversations.recent_history(db, conversation, HISTORY_LIMIT)

    reply = llm.generate_reply(system_prompt, history)

    conversations.record_message(
        db, conversation, MessageRole.ASSISTANT, reply, sent_by=SentBy.BOT
    )

    sources = sorted({meta["filename"] for meta in metadatas}) if metadatas else []

    return schemas.ChatResponse(session_id=session_id, reply=reply, sources=sources, disclaimer=disclaimer)
