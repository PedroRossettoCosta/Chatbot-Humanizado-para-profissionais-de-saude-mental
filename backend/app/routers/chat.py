import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.models import Channel
from app.services import auth, notifications, pipeline

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/simulate", response_model=schemas.ChatResponse)
def simulate_chat(
    payload: schemas.ChatRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.current_user),
):
    """Canal simulado: o mesmo caminho do WhatsApp (`services/pipeline.py`),
    sem depender da Meta e sem a espera antes de responder.

    O `session_id` faz aqui o papel que o número de telefone faz no
    WhatsApp — é o identificador do contato dentro do canal.
    """
    # Só a própria profissional testa a MarIA dela: o simulador gasta a
    # chave da API e grava conversas no consultório.
    professional = db.query(models.Professional).filter_by(slug=payload.professional_slug).first()
    if not professional or not user.owns(professional.id):
        raise HTTPException(status_code=404, detail="Profissional não encontrado")

    session_id = payload.session_id or str(uuid.uuid4())
    received = pipeline.receive(db, professional, Channel.SIMULATOR, session_id, payload.message)
    conversation = received.conversation
    info = {"triage_level": received.triage_level, "alert_created": received.alert_id is not None}
    # O e-mail sai depois da resposta ao contato: um servidor de e-mail
    # lento não atrasa a mensagem de emergência.
    if received.alert_id:
        background_tasks.add_task(notifications.notify_alert, received.alert_id)
    if received.emergency:
        return _response(session_id, conversation, received.immediate[-1], received.disclaimer, **info)

    answer = pipeline.reply(db, professional, conversation, payload.message)
    if answer.alert_id:
        background_tasks.add_task(notifications.notify_alert, answer.alert_id)
        info["alert_created"] = True
    if answer.notify_request:
        background_tasks.add_task(notifications.notify_human_request, conversation.id)
    return _response(
        session_id, conversation, answer.text, received.disclaimer, answer.sources, handoff=answer.handoff, **info
    )


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
