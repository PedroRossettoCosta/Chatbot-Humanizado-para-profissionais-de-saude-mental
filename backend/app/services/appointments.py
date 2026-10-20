"""Pedidos de horário: a SelenIA reserva, a profissional decide.

Fluxo (decisão do Pedro em 28/09/2026):

1. Na conversa, a pessoa escolhe um dos horários livres e diz o nome. A
   SelenIA chama `pedir_agendamento`, que cai em `request`: cria um evento
   "Sessão (a confirmar) · nome" na agenda da profissional e um
   `Appointment` provisório, válido por 24 horas. A profissional recebe
   um e-mail.
2. No painel (tela Agenda), ela confirma ou recusa. A pessoa recebe um
   texto fixo com a decisão, se a janela de 24h do WhatsApp ainda
   estiver aberta.
3. Sem decisão em 24 horas, o pedido expira, o evento sai da agenda e a
   profissional recebe um e-mail (`expire_overdue`, chamado a cada
   poucos minutos em `main.py`). Até lá, um pedido vencido já não
   segura o horário nem pode ser confirmado.

Uma sessão por dia por pessoa (decisão do Pedro em 28/09/2026): a mesma
pessoa pode ter sessões em dias diferentes, mas não duas no mesmo dia.
Um pedido novo no dia de um pedido ainda aguardando substitui o
anterior (ela mudou o horário); no dia de uma sessão confirmada, é
recusado. A conta é pelo contato, não pela conversa.

Remarcar e cancelar (decisão do Pedro em 12/10/2026, a partir do
feedback de 30/09: alguém com o celular da pessoa não pode desmarcar
sozinho):

- **Remarcar** (`request_reschedule`): o horário novo fica reservado
  como pedido ligado à sessão antiga (`replaces_id`). Quando a
  profissional confirma, a sessão antiga é cancelada e sai do Google; se
  recusar, a antiga continua.
- **Cancelar** (`request_cancel`): sessão confirmada ganha
  `cancel_requested_at` e continua de pé até a profissional confirmar o
  cancelamento. Pedido ainda não confirmado a pessoa pode desistir na
  hora, porque nada estava marcado.

Duas pessoas no mesmo horário: `request` roda com uma trava por
profissional no Postgres (`pg_advisory_xact_lock`), então dois pedidos
da mesma profissional nunca são conferidos ao mesmo tempo. Com a trava,
confere de novo o Google e os pedidos ativos no banco. O índice único
`uq_appointment_active_slot` é a rede de segurança.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from zoneinfo import ZoneInfo

from sqlalchemy import or_, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.models import AppointmentStatus, Channel, MessageRole, SentBy
from app.services import calendar, clients, conversations, whatsapp

logger = logging.getLogger(__name__)

HOLD = timedelta(hours=24)

# Textos fixos enviados à pessoa quando a profissional decide. Não passam
# pelo modelo. Pendentes de aprovação da Marília.
CONFIRMED_MESSAGE = "Sua sessão com {name} está confirmada para {when}. Até lá!"
REJECTED_MESSAGE = (
    "{name} não vai conseguir atender em {when}. "
    "Se quiser, posso ver outros horários com você."
)
RESCHEDULE_CONFIRMED_MESSAGE = "{name} confirmou a troca: sua sessão passou de {old} para {when}. Até lá!"
RESCHEDULE_REJECTED_MESSAGE = (
    "{name} não vai conseguir atender em {when}. Sua sessão de {old} continua marcada. "
    "Se quiser, posso ver outros horários com você."
)
CANCEL_CONFIRMED_MESSAGE = "{name} confirmou o cancelamento da sua sessão de {when}."
CANCEL_REJECTED_MESSAGE = (
    "{name} não confirmou o cancelamento: sua sessão de {when} continua marcada. "
    "Se precisar, fale direto com {name} por aqui."
)

TENTATIVE_TITLE = "Sessão (a confirmar) · {patient}"
CONFIRMED_TITLE = "Sessão · {patient}"
# Cores do Google Agenda: 5 = amarelo (a confirmar), 10 = verde (confirmado).
TENTATIVE_COLOR = "5"
CONFIRMED_COLOR = "10"


TAKEN_MESSAGE = "Esse horário não está mais livre. Consulte os horários de novo e ofereça outros."


class AppointmentError(Exception):
    """Pedido ou decisão recusados. A mensagem pode ir para a tela."""


@dataclass
class Booking:
    """Resultado de `request`: o texto para a SelenIA e o pedido criado."""

    text: str
    appointment_id: str | None = None


def _event_description(appointment: models.Appointment) -> str:
    if appointment.conversation is None:
        return "Marcado pelo painel da SelenIA."
    contact = appointment.conversation.contact
    if contact.channel == Channel.SIMULATOR:
        origin = "Pedido feito no simulador do painel (teste)."
    else:
        phone = conversations.contact_phone(contact) or "número não informado pelo WhatsApp"
        origin = f"Pedido feito pelo WhatsApp.\nTelefone: {phone}"
    return (
        f"{origin}\n\nMarcado pela SelenIA. Confirme ou recuse no painel: {settings.frontend_url}/agenda\n"
        "Sem decisão em 24 horas, este horário é liberado."
    )


def _event_body(appointment: models.Appointment, confirmed: bool) -> dict:
    tz = settings.agenda_timezone
    title = CONFIRMED_TITLE if confirmed else TENTATIVE_TITLE
    return {
        "summary": title.format(patient=appointment.patient_name),
        "description": _event_description(appointment),
        "colorId": CONFIRMED_COLOR if confirmed else TENTATIVE_COLOR,
        "start": {"dateTime": appointment.starts_at.isoformat(), "timeZone": tz},
        "end": {"dateTime": appointment.ends_at.isoformat(), "timeZone": tz},
    }


def _holding(now: datetime):
    """Pedidos que seguram o horário: confirmados e provisórios no prazo."""
    return or_(
        models.Appointment.status == AppointmentStatus.CONFIRMED,
        (models.Appointment.status == AppointmentStatus.TENTATIVE) & (models.Appointment.expires_at > now),
    )


def active_for_contact(
    db: Session, conversation: models.Conversation, now: datetime | None = None
) -> list[models.Appointment]:
    """Pedidos e sessões que esta pessoa tem de pé, em qualquer conversa."""
    return (
        db.query(models.Appointment)
        .join(models.Conversation, models.Appointment.conversation_id == models.Conversation.id)
        .filter(models.Conversation.contact_id == conversation.contact_id, _holding(now or models._now()))
        .order_by(models.Appointment.starts_at)
        .all()
    )


def _local_day(moment: datetime):
    return moment.astimezone(ZoneInfo(settings.agenda_timezone)).date()


def pending_note(db: Session, conversation: models.Conversation, now: datetime | None = None) -> str | None:
    """Linhas para a SelenIA saber o que esta pessoa já tem marcado."""
    current = active_for_contact(db, conversation, now)
    if not current:
        return None
    lines = []
    for a in current:
        when = calendar.format_slot(a.starts_at)
        if a.status == AppointmentStatus.CONFIRMED:
            state = "confirmada, cancelamento pedido" if a.cancel_requested_at else "confirmada"
        elif a.replaces is not None:
            state = f"aguardando confirmação, troca da sessão de {calendar.format_slot(a.replaces.starts_at)}"
        else:
            state = "aguardando confirmação"
        lines.append(f"- {when} ({state}) [código {calendar.slot_code(a.starts_at)}]")
    return (
        "Esta pessoa já tem:\n" + "\n".join(lines) + "\n"
        "Ela pode ter uma sessão por dia: um pedido novo num dia que ainda aguarda confirmação troca o "
        "horário daquele dia; num dia com sessão confirmada, não dá para marcar outra. Ela pode ter no "
        f"máximo {settings.max_pending_requests} pedidos aguardando confirmação ao mesmo tempo."
    )


def _overlaps(db: Session, professional: models.Professional, start: datetime, end: datetime, now: datetime) -> bool:
    return (
        db.query(models.Appointment)
        .filter(
            models.Appointment.professional_id == professional.id,
            _holding(now),
            models.Appointment.starts_at < end,
            models.Appointment.ends_at > start,
        )
        .first()
        is not None
    )


def request(
    db: Session,
    professional: models.Professional,
    conversation: models.Conversation,
    code: str,
    patient_name: str,
    now: datetime | None = None,
) -> Booking:
    """Reserva provisória pedida pela SelenIA. Devolve o texto da ferramenta.

    Nunca levanta exceção: qualquer recusa volta como texto para a SelenIA
    explicar à pessoa.
    """
    name = (patient_name or "").strip()[:80]
    start = calendar.parse_slot_code(code)
    if not name:
        return Booking("Falta o nome da pessoa. Pergunte o nome antes de pedir o horário.")
    if start is None:
        return Booking("Código de horário inválido. Use um código da lista de consultar_horarios_livres.")
    if not calendar.can_book(professional):
        return Booking(f"A reserva não está disponível. Diga que vai passar o pedido para {professional.name} confirmar.")

    now = now or models._now()
    end = start + timedelta(minutes=professional.session_minutes)
    connection = professional.calendar_connection

    # Trava por profissional até o fim da transação: dois pedidos dela
    # esperam um pelo outro, nunca conferem a agenda ao mesmo tempo.
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": f"agenda:{professional.id}"})

    # Uma sessão por dia por pessoa: só o que ela já tem no mesmo dia importa.
    same_day = [a for a in active_for_contact(db, conversation, now) if _local_day(a.starts_at) == start.date()]
    confirmed = next((a for a in same_day if a.status == AppointmentStatus.CONFIRMED), None)
    if confirmed:
        db.rollback()
        return Booking(
            f"Esta pessoa já tem sessão confirmada nesse dia ({calendar.format_slot(confirmed.starts_at)}) e só "
            f"pode ter uma sessão por dia. Ofereça outro dia; para mudar a sessão confirmada, diga que vai "
            f"passar o pedido para {professional.name}."
        )
    previous = same_day[0] if same_day else None
    if previous and previous.starts_at == start:
        db.rollback()
        return Booking(f"Este horário já está pedido por esta pessoa e aguarda {professional.name} confirmar.")

    # Teto de pedidos aguardando confirmação: sem ele, uma pessoa pedia um
    # horário em cada dia e segurava a agenda por 24h. Trocar o horário
    # de um dia que já tem pedido não aumenta a conta.
    if previous is None:
        # Pedido de troca não conta: ele substitui uma sessão, não soma.
        waiting = [
            a
            for a in active_for_contact(db, conversation, now)
            if a.status == AppointmentStatus.TENTATIVE and a.replaces_id is None
        ]
        if len(waiting) >= settings.max_pending_requests:
            db.rollback()
            return Booking(
                f"Esta pessoa já tem {len(waiting)} pedidos aguardando {professional.name} confirmar, o máximo "
                f"ao mesmo tempo. Não peça outro horário agora: diga que, assim que {professional.name} "
                f"responder aos pedidos, a pessoa pode pedir mais. Ainda dá para trocar o horário de um dia que "
                f"já tem pedido."
            )

    taken = TAKEN_MESSAGE
    if _overlaps(db, professional, start, end, now):
        db.rollback()
        return Booking(taken)
    try:
        free = calendar.available_slots(professional, now, contact=conversation.contact)
    except calendar.CalendarError:
        db.rollback()
        return Booking(f"Não foi possível consultar a agenda agora. Diga que vai confirmar com {professional.name}.")
    if start not in free:
        db.rollback()
        return Booking(taken)

    appointment = models.Appointment(
        professional_id=professional.id,
        conversation_id=conversation.id,
        calendar_id="primary",
        starts_at=start,
        ends_at=end,
        status=AppointmentStatus.TENTATIVE,
        patient_name=name,
        expires_at=now + HOLD,
    )
    appointment.conversation = conversation
    try:
        appointment.calendar_event_id = calendar.create_event(connection, _event_body(appointment, confirmed=False))
    except calendar.CalendarError:
        db.rollback()
        return Booking(f"Não foi possível reservar na agenda agora. Diga que vai passar o pedido para {professional.name}.")

    db.add(appointment)
    try:
        db.flush()
    except IntegrityError:
        # Só chega aqui se algo escapou da trava: desfaz o evento criado.
        db.rollback()
        _delete_event_quietly(connection, appointment.calendar_event_id)
        return Booking(taken)

    if previous:
        # A mesma pessoa trocou o horário daquele dia: o pedido anterior sai.
        previous.status = AppointmentStatus.CANCELLED
        previous.decided_at = now
        _delete_event_quietly(connection, previous.calendar_event_id)
    db.commit()
    return Booking(
        f"Pedido registrado: {calendar.format_slot(start)}, em nome de {name}. "
        f"Está aguardando {professional.name} confirmar; a pessoa recebe a confirmação por aqui.",
        appointment_id=appointment.id,
    )


def _delete_event_quietly(connection, event_id: str | None) -> None:
    if not connection or not event_id:
        return
    try:
        calendar.delete_event(connection, event_id)
    except calendar.CalendarError:
        logger.warning("não foi possível apagar um evento da agenda")


def create_by_professional(
    db: Session, professional: models.Professional, kind: str, title: str, code: str, minutes: int
) -> models.Appointment | None:
    """A profissional marca pelo calendário do painel.

    Sessão: evento "Sessão · nome" e um `Appointment` confirmado, que conta
    no limite por dia e ocupa o horário para a SelenIA. Outro compromisso:
    só o evento no Google (a SelenIA já o vê como ocupado). Levanta
    `AppointmentError` se o horário da sessão já estiver ocupado.
    """
    start = calendar.parse_slot_code(code)
    if start is None:
        raise AppointmentError("Data ou horário inválido.")
    if not calendar.has_events_permission(professional):
        raise AppointmentError("Conecte o Google Agenda com a permissão de eventos.")
    connection = professional.calendar_connection
    end = start + timedelta(minutes=minutes)
    title = title.strip()
    tz = settings.agenda_timezone

    if kind == "block":
        calendar.create_event(
            connection,
            {"summary": title, "start": {"dateTime": start.isoformat(), "timeZone": tz},
             "end": {"dateTime": end.isoformat(), "timeZone": tz}},
        )
        return None

    now = models._now()
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": f"agenda:{professional.id}"})
    busy = calendar.busy_intervals(connection, start, end)
    if busy or _overlaps(db, professional, start, end, now):
        db.rollback()
        raise AppointmentError("Esse horário já tem outro compromisso na agenda.")
    appointment = models.Appointment(
        professional_id=professional.id,
        calendar_id="primary",
        starts_at=start,
        ends_at=end,
        status=AppointmentStatus.CONFIRMED,
        source="panel",
        patient_name=title[:80],
        decided_at=now,
    )
    try:
        appointment.calendar_event_id = calendar.create_event(connection, _event_body(appointment, confirmed=True))
    except calendar.CalendarError as err:
        db.rollback()
        raise AppointmentError(str(err))
    db.add(appointment)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        _delete_event_quietly(connection, appointment.calendar_event_id)
        raise AppointmentError("Esse horário já tem outro compromisso na agenda.")
    return appointment


# ---------------------------------------------------------------------------
# Decisão da profissional
# ---------------------------------------------------------------------------


def _tell_contact(db: Session, appointment: models.Appointment, message: str) -> bool:
    """Grava o texto fixo na conversa e envia pelo canal. Devolve se chegou."""
    conversation = appointment.conversation
    contact = conversation.contact
    if contact.channel == Channel.WHATSAPP:
        if not conversations.reply_window_open(conversation):
            return False
        phone_number_id = appointment.professional.whatsapp_phone_number_id
        if not phone_number_id:
            return False
        try:
            external_id = whatsapp.send_text(phone_number_id, contact.external_id, message)
        except whatsapp.SendError as exc:
            logger.error("falha ao avisar a pessoa sobre o pedido de horário: %s", exc)
            return False
        conversations.record_message(db, conversation, MessageRole.ASSISTANT, message, sent_by=SentBy.SYSTEM, external_id=external_id)
        return True
    # Simulador: fica na conversa de teste.
    conversations.record_message(db, conversation, MessageRole.ASSISTANT, message, sent_by=SentBy.SYSTEM)
    return True


def _pending(db: Session, appointment: models.Appointment) -> None:
    db.refresh(appointment)
    if appointment.status != AppointmentStatus.TENTATIVE:
        raise AppointmentError("Este pedido já foi decidido.")
    if appointment.expires_at <= models._now():
        raise AppointmentError("Este pedido passou de 24 horas e o horário foi liberado.")


def _awaiting_cancel(appointment: models.Appointment) -> bool:
    return appointment.status == AppointmentStatus.CONFIRMED and appointment.cancel_requested_at is not None


def approve(db: Session, appointment: models.Appointment) -> models.Appointment:
    """Confirma o que está pendente: horário novo, troca ou cancelamento."""
    db.refresh(appointment)
    professional = appointment.professional
    if _awaiting_cancel(appointment):
        _delete_event_quietly(professional.calendar_connection, appointment.calendar_event_id)
        appointment.status = AppointmentStatus.CANCELLED
        appointment.decided_at = models._now()
        db.commit()
        when = calendar.format_slot(appointment.starts_at)
        message = CANCEL_CONFIRMED_MESSAGE.format(name=professional.name, when=when)
        appointment.contact_notified = _tell_contact(db, appointment, message)
        db.commit()
        return appointment

    _pending(db, appointment)
    connection = professional.calendar_connection
    if connection is None:
        raise AppointmentError("Reconecte o Google Agenda para confirmar.")
    try:
        calendar.update_event(connection, appointment.calendar_event_id, _event_body(appointment, confirmed=True))
    except calendar.CalendarError as err:
        raise AppointmentError(str(err))
    now = models._now()
    appointment.status = AppointmentStatus.CONFIRMED
    appointment.decided_at = now
    # Sessão confirmada: a pessoa entra na lista de clientes ativos.
    if appointment.conversation is not None:
        clients.activate(db, appointment.conversation.contact)
    old = appointment.replaces
    if old is not None and old.status in (AppointmentStatus.CONFIRMED, AppointmentStatus.TENTATIVE):
        # Troca confirmada: a data antiga sai do banco e do Google.
        _delete_event_quietly(connection, old.calendar_event_id)
        old.status = AppointmentStatus.CANCELLED
        old.decided_at = now
    db.commit()
    when = calendar.format_slot(appointment.starts_at)
    if old is not None:
        message = RESCHEDULE_CONFIRMED_MESSAGE.format(
            name=professional.name, old=calendar.format_slot(old.starts_at), when=when
        )
    else:
        message = CONFIRMED_MESSAGE.format(name=professional.name, when=when)
    appointment.contact_notified = _tell_contact(db, appointment, message)
    db.commit()
    return appointment


def reject(db: Session, appointment: models.Appointment) -> models.Appointment:
    """Recusa o que está pendente. Numa troca ou num cancelamento, a
    sessão que já existia continua marcada."""
    db.refresh(appointment)
    professional = appointment.professional
    when = calendar.format_slot(appointment.starts_at)
    if _awaiting_cancel(appointment):
        appointment.cancel_requested_at = None
        db.commit()
        message = CANCEL_REJECTED_MESSAGE.format(name=professional.name, when=when)
        appointment.contact_notified = _tell_contact(db, appointment, message)
        db.commit()
        return appointment

    _pending(db, appointment)
    _delete_event_quietly(professional.calendar_connection, appointment.calendar_event_id)
    appointment.status = AppointmentStatus.REJECTED
    appointment.decided_at = models._now()
    db.commit()
    old = appointment.replaces
    if old is not None:
        message = RESCHEDULE_REJECTED_MESSAGE.format(
            name=professional.name, old=calendar.format_slot(old.starts_at), when=when
        )
    else:
        message = REJECTED_MESSAGE.format(name=professional.name, when=when)
    appointment.contact_notified = _tell_contact(db, appointment, message)
    db.commit()
    return appointment


# ---------------------------------------------------------------------------
# Remarcar e cancelar, pedidos pela pessoa na conversa
# ---------------------------------------------------------------------------

NOT_FOUND = (
    "Não há sessão desta pessoa nesse horário. Use o código da sessão que aparece na lista de "
    "consultar_horarios_livres, em 'Esta pessoa já tem'."
)


def _find_session(db: Session, conversation: models.Conversation, code: str, now: datetime):
    start = calendar.parse_slot_code(code)
    if start is None:
        return None
    return next((a for a in active_for_contact(db, conversation, now) if a.starts_at == start), None)


def request_reschedule(
    db: Session,
    professional: models.Professional,
    conversation: models.Conversation,
    current_code: str,
    new_code: str,
    now: datetime | None = None,
) -> Booking:
    """A pessoa quer trocar uma sessão por outro horário. Reserva o novo
    como pedido; a antiga só sai quando a profissional confirmar."""
    now = now or models._now()
    current = _find_session(db, conversation, current_code, now)
    if current is None:
        return Booking(NOT_FOUND)
    if current.status == AppointmentStatus.TENTATIVE:
        return Booking(
            "Essa sessão ainda é um pedido sem confirmação. Para mudar, use pedir_agendamento com o novo "
            "horário (no mesmo dia, ele substitui o pedido) ou pedir_cancelamento para desistir dele."
        )
    if current.cancel_requested_at:
        return Booking(f"Já há um pedido de cancelamento dessa sessão aguardando {professional.name}.")
    if any(a.replaces_id == current.id for a in active_for_contact(db, conversation, now)):
        return Booking(f"Já há um pedido de troca dessa sessão aguardando {professional.name} confirmar.")

    start = calendar.parse_slot_code(new_code)
    if start is None:
        return Booking("Código de horário inválido. Use um código da lista de consultar_horarios_livres.")
    if not calendar.can_book(professional):
        return Booking(f"A troca não está disponível. Diga que vai passar o pedido para {professional.name}.")
    end = start + timedelta(minutes=professional.session_minutes)
    connection = professional.calendar_connection

    db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": f"agenda:{professional.id}"})
    others = [a for a in active_for_contact(db, conversation, now) if a.id != current.id]
    if any(_local_day(a.starts_at) == start.date() for a in others):
        db.rollback()
        return Booking(
            "Esta pessoa já tem outra sessão ou pedido nesse dia, e só pode ter uma por dia. Ofereça outro dia."
        )
    if _overlaps(db, professional, start, end, now):
        db.rollback()
        return Booking(TAKEN_MESSAGE)
    try:
        free = calendar.available_slots(professional, now, contact=conversation.contact)
    except calendar.CalendarError:
        db.rollback()
        return Booking(f"Não foi possível consultar a agenda agora. Diga que vai confirmar com {professional.name}.")
    if start not in free:
        db.rollback()
        return Booking(TAKEN_MESSAGE)

    appointment = models.Appointment(
        professional_id=professional.id,
        conversation_id=conversation.id,
        calendar_id="primary",
        starts_at=start,
        ends_at=end,
        status=AppointmentStatus.TENTATIVE,
        patient_name=current.patient_name,
        expires_at=now + HOLD,
        replaces_id=current.id,
    )
    appointment.conversation = conversation
    appointment.replaces = current
    try:
        appointment.calendar_event_id = calendar.create_event(connection, _event_body(appointment, confirmed=False))
    except calendar.CalendarError:
        db.rollback()
        return Booking(f"Não foi possível reservar na agenda agora. Diga que vai passar o pedido para {professional.name}.")
    db.add(appointment)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        _delete_event_quietly(connection, appointment.calendar_event_id)
        return Booking(TAKEN_MESSAGE)
    old = calendar.format_slot(current.starts_at)
    return Booking(
        f"Pedido de troca registrado: de {old} para {calendar.format_slot(start)}. Está aguardando "
        f"{professional.name} confirmar; até lá, a sessão de {old} continua marcada, e a pessoa recebe a "
        "resposta por aqui. Nunca diga que a troca já foi feita.",
        appointment_id=appointment.id,
    )


def request_cancel(
    db: Session,
    professional: models.Professional,
    conversation: models.Conversation,
    code: str,
    now: datetime | None = None,
) -> Booking:
    """A pessoa quer cancelar. Sessão confirmada vira pedido para a
    profissional; pedido ainda sem confirmação é desfeito na hora."""
    now = now or models._now()
    current = _find_session(db, conversation, code, now)
    if current is None:
        return Booking(NOT_FOUND)
    when = calendar.format_slot(current.starts_at)
    if current.status == AppointmentStatus.TENTATIVE:
        _delete_event_quietly(professional.calendar_connection, current.calendar_event_id)
        current.status = AppointmentStatus.CANCELLED
        current.decided_at = now
        db.commit()
        if current.replaces is not None:
            kept = calendar.format_slot(current.replaces.starts_at)
            return Booking(f"Pedido de troca desfeito. A sessão de {kept} continua marcada.")
        return Booking(f"Pedido de {when} desfeito: o horário foi liberado.")
    if current.cancel_requested_at:
        return Booking(f"O cancelamento dessa sessão já está aguardando {professional.name} confirmar.")
    current.cancel_requested_at = now
    # A resposta da profissional vai para a conversa em que a pessoa pediu.
    current.conversation_id = conversation.id
    db.commit()
    return Booking(
        f"Pedido de cancelamento registrado para {when}. Está aguardando {professional.name} confirmar; até "
        "lá, a sessão continua marcada, e a pessoa recebe a resposta por aqui. Nunca diga que já está cancelada.",
        appointment_id=current.id,
    )


# ---------------------------------------------------------------------------
# Validade
# ---------------------------------------------------------------------------


def expire_overdue(db: Session, now: datetime | None = None) -> list[str]:
    """Libera os pedidos provisórios vencidos. Devolve os ids expirados.

    Não avisa a pessoa: depois de 24h, a janela do WhatsApp quase sempre
    já fechou. A profissional recebe e-mail (quem chama envia).
    """
    now = now or models._now()
    query = db.query(models.Appointment).filter(
        models.Appointment.status == AppointmentStatus.TENTATIVE,
        models.Appointment.expires_at <= now,
    )
    expired = []
    for appointment in query.all():
        _delete_event_quietly(appointment.professional.calendar_connection, appointment.calendar_event_id)
        appointment.status = AppointmentStatus.EXPIRED
        appointment.decided_at = now
        expired.append(appointment.id)
    if expired:
        db.commit()
    return expired
