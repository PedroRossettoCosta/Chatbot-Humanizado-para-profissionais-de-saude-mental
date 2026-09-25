"""Ações da profissional sobre uma conversa: assumir, responder, devolver ao bot.

Ainda sem login (entra na semana 2, ver planejamento-mvp-9out.md): hoje
qualquer um que saiba o id da conversa consegue chamar estas rotas.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services import handoff

router = APIRouter(prefix="/conversations", tags=["conversations"])


def _get(db: Session, conversation_id: str) -> models.Conversation:
    conversation = db.get(models.Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    return conversation


@router.get("/{conversation_id}", response_model=schemas.ConversationOut)
def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    return _get(db, conversation_id)


@router.post("/{conversation_id}/take-over", response_model=schemas.ConversationOut)
def take_over(conversation_id: str, db: Session = Depends(get_db)):
    conversation = _get(db, conversation_id)
    handoff.take_over(db, conversation)
    return conversation


@router.post("/{conversation_id}/release", response_model=schemas.ConversationOut)
def release(conversation_id: str, db: Session = Depends(get_db)):
    conversation = _get(db, conversation_id)
    handoff.release(db, conversation)
    return conversation


@router.post("/{conversation_id}/messages", response_model=schemas.ConversationOut)
def send_message(conversation_id: str, payload: schemas.ProfessionalMessage, db: Session = Depends(get_db)):
    # No simulador a mensagem só é gravada; o envio pelo WhatsApp entra
    # com o webhook (semana 2).
    conversation = _get(db, conversation_id)
    handoff.send_professional_message(db, conversation, payload.content)
    db.refresh(conversation)
    return conversation
