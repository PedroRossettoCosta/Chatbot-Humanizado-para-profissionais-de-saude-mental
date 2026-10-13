"""Alertas no painel: listar, abrir (registra o visto) e marcar como revisado.

Não há rota para editar nem apagar alerta: a trilha só cresce (RNF05).
Liberar a SelenIA depois de uma emergência é a rota da conversa
(`POST /conversations/{id}/release`), que também entra na trilha.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.database import get_db
from app.services import alerts, auth, conversations

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _get(db: Session, alert_id: str, user: models.User) -> models.SafetyAlert:
    alert = db.get(models.SafetyAlert, alert_id)
    if not alert or not user.owns(alert.professional_id):
        raise HTTPException(status_code=404, detail="Alerta não encontrado")
    return alert


def _summary(alert: models.SafetyAlert, full_phone: bool) -> dict:
    conversation = alert.conversation
    name, phone = conversations.contact_label(conversation.contact, full_phone)
    reviewed_at = alerts.reviewed_at(alert)
    return {
        "id": alert.id,
        "level": alert.level,
        "trigger_text": alerts.trigger_text(alert.trigger),
        "excerpt": alert.excerpt,
        "created_at": alert.created_at,
        "status": "reviewed" if reviewed_at else "new",
        "reviewed_at": reviewed_at,
        "conversation_id": conversation.id,
        "conversation_state": conversation.state,
        "channel": conversation.contact.channel,
        "contact_name": name,
        "contact_phone": phone,
    }


def _detail(alert: models.SafetyAlert) -> schemas.AlertOut:
    return schemas.AlertOut(**_summary(alert, full_phone=True), timeline=alerts.timeline(alert))


@router.get("", response_model=list[schemas.AlertSummary])
def list_alerts(
    professional_slug: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.current_user),
):
    professional = db.query(models.Professional).filter_by(slug=professional_slug).first()
    if not professional or not user.owns(professional.id):
        raise HTTPException(status_code=404, detail="Profissional não encontrado")

    rows = (
        db.query(models.SafetyAlert)
        .options(
            joinedload(models.SafetyAlert.events),
            joinedload(models.SafetyAlert.conversation).joinedload(models.Conversation.contact),
        )
        .filter_by(professional_id=professional.id)
        .order_by(models.SafetyAlert.created_at.desc())
        .all()
    )
    summaries = [schemas.AlertSummary(**_summary(a, full_phone=False)) for a in rows]
    # Os não revisados primeiro; dentro de cada grupo, os mais recentes.
    summaries.sort(key=lambda s: s.status != "new")
    return summaries


@router.get("/{alert_id}", response_model=schemas.AlertOut)
def get_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.current_user),
):
    return _detail(_get(db, alert_id, user))


@router.post("/{alert_id}/view", response_model=schemas.AlertOut)
def view_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.current_user),
):
    """O painel chama ao abrir o alerta; só a primeira vez entra na trilha."""
    alert = _get(db, alert_id, user)
    alerts.mark_viewed(db, alert)
    return _detail(alert)


@router.post("/{alert_id}/review", response_model=schemas.AlertOut)
def review_alert(
    alert_id: str,
    payload: schemas.AlertReview,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.current_user),
):
    alert = _get(db, alert_id, user)
    try:
        alerts.mark_reviewed(db, alert, payload.note)
    except alerts.AlreadyReviewed:
        raise HTTPException(status_code=409, detail="Este alerta já foi revisado.")
    return _detail(alert)
