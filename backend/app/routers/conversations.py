"""Conversas no painel: listar, abrir, assumir, responder, devolver ao bot.

Todas exigem login, e só a dona da conversa enxerga ou age sobre ela.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.database import get_db
from app.models import ConversationState
from app.services import auth, conversations, handoff

router = APIRouter(prefix="/conversations", tags=["conversations"])

PREVIEW_LENGTH = 140

# Ordem da lista: o que precisa dela primeiro, depois as mais recentes.
_PRIORITY = {"emergency": 0, "awaiting": 1, "attention": 2, "other": 3}


def _get(db: Session, conversation_id: str, user: models.User) -> models.Conversation:
    conversation = db.get(models.Conversation, conversation_id)
    if not conversation or not user.owns(conversation.professional_id):
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    return conversation


def _base(conversation: models.Conversation, full_phone: bool) -> dict:
    contact = conversation.contact
    phone = conversations.contact_phone(contact) if full_phone else conversations.masked_phone(contact)
    if contact.channel == models.Channel.SIMULATOR:
        name = "Conversa de teste"
    else:
        name = contact.display_name or phone
    return {
        "id": conversation.id,
        "channel": contact.channel,
        "contact_name": name,
        "contact_phone": phone,
        "state": conversation.state,
        "needs_attention": conversation.needs_attention,
        "awaiting_reply_since": conversation.awaiting_reply_since,
        "last_message_at": conversation.last_message_at,
        "reply_window_closes_at": conversations.reply_window_closes_at(conversation),
        "reply_window_open": conversations.reply_window_open(conversation),
    }


def _detail(conversation: models.Conversation) -> schemas.ConversationOut:
    """A conversa aberta, com o número completo: numa emergência ela
    pode precisar ligar para a pessoa."""
    latest = max(conversation.alerts, key=lambda a: a.created_at, default=None)
    return schemas.ConversationOut(
        **_base(conversation, full_phone=True),
        latest_alert=schemas.AlertBrief(level=latest.level, created_at=latest.created_at) if latest else None,
        messages=[schemas.MessageOut.model_validate(m) for m in conversation.messages],
    )


def _priority(summary: schemas.ConversationSummary) -> str:
    if summary.state == ConversationState.EMERGENCY_HOLD:
        return "emergency"
    if summary.awaiting_reply_since:
        return "awaiting"
    if summary.needs_attention:
        return "attention"
    return "other"


@router.get("", response_model=list[schemas.ConversationSummary])
def list_conversations(
    professional_slug: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.current_user),
):
    professional = db.query(models.Professional).filter_by(slug=professional_slug).first()
    if not professional or not user.owns(professional.id):
        raise HTTPException(status_code=404, detail="Profissional não encontrado")

    rows = (
        db.query(models.Conversation)
        .options(joinedload(models.Conversation.contact))
        .filter_by(professional_id=professional.id)
        .all()
    )
    # Última mensagem de cada conversa numa consulta só (DISTINCT ON do Postgres).
    last_messages = {
        m.conversation_id: m
        for m in db.query(models.Message)
        .filter(models.Message.conversation_id.in_([c.id for c in rows]))
        .order_by(models.Message.conversation_id, models.Message.seq.desc())
        .distinct(models.Message.conversation_id)
    } if rows else {}

    summaries = []
    for conversation in rows:
        last = last_messages.get(conversation.id)
        summaries.append(
            schemas.ConversationSummary(
                **_base(conversation, full_phone=False),
                last_message=schemas.LastMessageOut(
                    role=last.role,
                    sent_by=last.sent_by,
                    preview=last.content[:PREVIEW_LENGTH],
                    created_at=last.created_at,
                )
                if last
                else None,
            )
        )
    summaries.sort(key=lambda s: s.last_message_at.timestamp() if s.last_message_at else 0, reverse=True)
    summaries.sort(key=lambda s: _PRIORITY[_priority(s)])
    return summaries


@router.get("/{conversation_id}", response_model=schemas.ConversationOut)
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.current_user),
):
    return _detail(_get(db, conversation_id, user))


@router.post("/{conversation_id}/take-over", response_model=schemas.ConversationOut)
def take_over(
    conversation_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.current_user),
):
    conversation = _get(db, conversation_id, user)
    handoff.take_over(db, conversation)
    return _detail(conversation)


@router.post("/{conversation_id}/release", response_model=schemas.ConversationOut)
def release(
    conversation_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.current_user),
):
    conversation = _get(db, conversation_id, user)
    handoff.release(db, conversation)
    return _detail(conversation)


@router.post("/{conversation_id}/messages", response_model=schemas.ConversationOut)
def send_message(
    conversation_id: str,
    payload: schemas.ProfessionalMessage,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.current_user),
):
    # No simulador a mensagem só é gravada; o envio pelo WhatsApp entra
    # com o webhook (02/10).
    conversation = _get(db, conversation_id, user)
    try:
        handoff.send_professional_message(db, conversation, payload.content)
    except handoff.ReplyWindowClosed:
        raise HTTPException(
            status_code=409,
            detail="Passaram 24 horas desde a última mensagem desta pessoa. Pelas regras do WhatsApp, "
            "você só pode responder quando ela escrever de novo.",
        )
    db.refresh(conversation)
    return _detail(conversation)
