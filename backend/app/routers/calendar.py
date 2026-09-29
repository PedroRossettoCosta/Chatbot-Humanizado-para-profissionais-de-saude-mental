"""Tela Agenda: conexão com o Google Agenda, prévia dos horários livres e
pedidos de horário (confirmar ou recusar).

O horário de atendimento é um campo da profissional e é salvo pelo
`PATCH /professionals/{slug}`. Regras em `services/calendar.py`.
"""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings
from app.database import get_db
from app.services import appointments, auth, calendar, conversations

router = APIRouter(prefix="/calendar", tags=["calendar"])


def _get_owned(db: Session, slug: str, user: models.User) -> models.Professional:
    professional = db.query(models.Professional).filter_by(slug=slug).first()
    if not professional or not user.owns(professional.id):
        raise HTTPException(status_code=404, detail="Profissional não encontrado")
    return professional


def _status(professional: models.Professional) -> schemas.CalendarStatus:
    connection = professional.calendar_connection
    return schemas.CalendarStatus(
        configured=calendar.is_configured(),
        connected=connection is not None,
        google_email=connection.google_email if connection else None,
        connected_at=connection.connected_at if connection else None,
        timezone=settings.agenda_timezone,
        requested_scopes=calendar.REQUESTED_SCOPES,
        ready=calendar.is_ready(professional),
        events_permission=calendar.has_events_permission(professional),
        can_book=calendar.can_book(professional),
    )


@router.get("/{slug}", response_model=schemas.CalendarStatus)
def get_status(slug: str, db: Session = Depends(get_db), user: models.User = Depends(auth.current_user)):
    return _status(_get_owned(db, slug, user))


@router.post("/{slug}/connect", response_model=schemas.CalendarStatus)
def connect(
    slug: str,
    payload: schemas.CalendarConnect,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.current_user),
):
    professional = _get_owned(db, slug, user)
    try:
        calendar.connect(db, professional, payload.code)
    except calendar.CalendarError as err:
        raise HTTPException(status_code=400, detail=str(err))
    db.refresh(professional)
    return _status(professional)


@router.delete("/{slug}/connect", response_model=schemas.CalendarStatus)
def disconnect(slug: str, db: Session = Depends(get_db), user: models.User = Depends(auth.current_user)):
    professional = _get_owned(db, slug, user)
    calendar.disconnect(db, professional)
    db.refresh(professional)
    return _status(professional)


@router.get("/{slug}/free-slots", response_model=list[schemas.FreeSlot])
def free_slots(slug: str, db: Session = Depends(get_db), user: models.User = Depends(auth.current_user)):
    """Os mesmos horários que a MarIA vê numa conversa agora."""
    professional = _get_owned(db, slug, user)
    try:
        slots = calendar.available_slots(professional)
    except calendar.CalendarError as err:
        raise HTTPException(status_code=409, detail=str(err))
    return [schemas.FreeSlot(starts_at=s, label=calendar.format_slot(s)) for s in slots]


def _appointment_out(appointment: models.Appointment) -> schemas.AppointmentOut:
    contact = appointment.conversation.contact if appointment.conversation else None
    return schemas.AppointmentOut(
        id=appointment.id,
        status=appointment.status,
        starts_at=appointment.starts_at,
        ends_at=appointment.ends_at,
        label=calendar.format_slot(appointment.starts_at),
        patient_name=appointment.patient_name,
        source=appointment.source or "maria",
        channel=contact.channel if contact else None,
        contact_phone=conversations.masked_phone(contact) if contact else None,
        conversation_id=appointment.conversation_id,
        created_at=appointment.created_at,
        expires_at=appointment.expires_at,
        decided_at=appointment.decided_at,
        contact_notified=appointment.contact_notified,
    )


@router.get("/{slug}/appointments", response_model=list[schemas.AppointmentOut])
def list_appointments(slug: str, db: Session = Depends(get_db), user: models.User = Depends(auth.current_user)):
    """Pedidos de horário: os que aguardam primeiro (mais próximos antes),
    depois os já decididos (mais recentes antes), até 50."""
    professional = _get_owned(db, slug, user)
    rows = (
        db.query(models.Appointment)
        .filter(
            models.Appointment.professional_id == professional.id,
            models.Appointment.status != models.AppointmentStatus.CANCELLED,
        )
        .order_by(models.Appointment.created_at.desc())
        .limit(50)
        .all()
    )
    pending = sorted((a for a in rows if a.status == models.AppointmentStatus.TENTATIVE), key=lambda a: a.starts_at)
    decided = [a for a in rows if a.status != models.AppointmentStatus.TENTATIVE]
    return [_appointment_out(a) for a in pending + decided]


def _get_appointment(db: Session, appointment_id: str, user: models.User) -> models.Appointment:
    appointment = db.get(models.Appointment, appointment_id)
    if appointment is None or not user.owns(appointment.professional_id):
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    return appointment


@router.post("/appointments/{appointment_id}/approve", response_model=schemas.AppointmentOut)
def approve(appointment_id: str, db: Session = Depends(get_db), user: models.User = Depends(auth.current_user)):
    appointment = _get_appointment(db, appointment_id, user)
    try:
        appointments.approve(db, appointment)
    except appointments.AppointmentError as err:
        raise HTTPException(status_code=409, detail=str(err))
    return _appointment_out(appointment)


@router.post("/appointments/{appointment_id}/reject", response_model=schemas.AppointmentOut)
def reject(appointment_id: str, db: Session = Depends(get_db), user: models.User = Depends(auth.current_user)):
    appointment = _get_appointment(db, appointment_id, user)
    try:
        appointments.reject(db, appointment)
    except appointments.AppointmentError as err:
        raise HTTPException(status_code=409, detail=str(err))
    return _appointment_out(appointment)


@router.get("/{slug}/events", response_model=list[schemas.CalendarEvent])
def week_events(
    slug: str,
    start: date = Query(description="Primeiro dia da semana (AAAA-MM-DD)"),
    days: int = Query(default=7, ge=1, le=31),
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.current_user),
):
    """Eventos para o calendário do painel, com os títulos (só para ela)."""
    professional = _get_owned(db, slug, user)
    if not calendar.has_events_permission(professional):
        raise HTTPException(status_code=409, detail="Conecte o Google Agenda com a permissão de eventos para ver o calendário.")
    tz = ZoneInfo(settings.agenda_timezone)
    first = datetime.combine(start, time(0), tzinfo=tz)
    last = first + timedelta(days=days)
    try:
        events = calendar.list_events(professional.calendar_connection, first, last)
    except calendar.CalendarError as err:
        raise HTTPException(status_code=502, detail=str(err))
    ours = {
        a.calendar_event_id: a
        for a in professional.appointments
        if a.calendar_event_id and a.status in models.ACTIVE_APPOINTMENT_STATUSES
    }
    out = []
    for e in events:
        appointment = ours.get(e["id"])
        kind = "google"
        if appointment is not None:
            kind = "maria_tentative" if appointment.status == models.AppointmentStatus.TENTATIVE else "maria_confirmed"
        out.append(
            schemas.CalendarEvent(
                id=e["id"],
                title=e["title"],
                starts_at=e["starts_at"],
                ends_at=e["ends_at"],
                all_day=e["all_day"],
                kind=kind,
                appointment_id=appointment.id if appointment else None,
            )
        )
    return out


@router.post("/{slug}/events", status_code=201)
def create_event(
    slug: str,
    payload: schemas.CalendarEventCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.current_user),
):
    """A profissional marca uma sessão ou outro compromisso pelo painel."""
    professional = _get_owned(db, slug, user)
    try:
        appointments.create_by_professional(
            db, professional, payload.kind, payload.title, payload.starts_at, payload.minutes
        )
    except (appointments.AppointmentError, calendar.CalendarError) as err:
        raise HTTPException(status_code=409, detail=str(err))
    return {"ok": True}
