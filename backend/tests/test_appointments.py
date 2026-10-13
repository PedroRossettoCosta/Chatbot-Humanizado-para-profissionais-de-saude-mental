"""Pedidos de horário: a SelenIA reserva, a profissional confirma ou recusa.

O Google é substituído: o livre/ocupado vem de uma lista, e criar,
atualizar e apagar eventos só anota a chamada. O banco é o de verdade,
inclusive a trava por profissional e o índice único.
"""

import threading
import time
from datetime import datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app import models
from app.database import SessionLocal
from app.models import AppointmentStatus, Channel
from app.services import appointments, calendar, conversations, llm

TEST_SLUG = "teste-reserva"
TZ = ZoneInfo("America/Sao_Paulo")
MONDAY_8AM = datetime(2026, 9, 28, 8, 0, tzinfo=TZ)
TUESDAY_10 = "2026-09-29T10:00"
HOURS = {day: [{"start": "10:00", "end": "16:00"}] for day in ("mon", "tue", "wed", "thu", "fri")}
BOTH_SCOPES = f"openid email {calendar.SCOPE_FREEBUSY} {calendar.SCOPE_EVENTS}"


def _cleanup(db):
    existing = db.query(models.Professional).filter_by(slug=TEST_SLUG).first()
    if existing:
        db.delete(existing)
        db.commit()


@pytest.fixture
def google(monkeypatch):
    state = SimpleNamespace(busy=[], created=[], updated=[], deleted=[], create_delay=0)

    def create(connection, body):
        time.sleep(state.create_delay)
        state.created.append(body)
        return f"evento-{len(state.created)}"

    monkeypatch.setattr(calendar, "busy_intervals", lambda connection, start, end: state.busy)
    monkeypatch.setattr(calendar, "create_event", create)
    monkeypatch.setattr(calendar, "update_event", lambda c, event_id, body: state.updated.append((event_id, body)))
    monkeypatch.setattr(calendar, "delete_event", lambda c, event_id: state.deleted.append(event_id))
    return state


@pytest.fixture
def professional(db):
    _cleanup(db)
    prof = models.Professional(
        slug=TEST_SLUG,
        name="Ana Reserva",
        session_minutes=50,
        working_hours=HOURS,
        whatsapp_phone_number_id="555000111",
    )
    prof.calendar_connection = models.CalendarConnection(
        google_email="agenda@teste.local", refresh_token="refresh", scopes=BOTH_SCOPES
    )
    db.add(prof)
    db.commit()
    yield prof
    db.expire_all()
    _cleanup(db)


def _conversation(db, professional, external_id="5521955554444", channel=Channel.WHATSAPP):
    contact = conversations.get_or_create_contact(db, professional, channel, external_id)
    conversation, _ = conversations.get_or_create_conversation(db, contact)
    # Janela de 24h aberta, como se a pessoa tivesse acabado de escrever.
    conversation.last_contact_message_at = models._now()
    db.commit()
    return conversation


def _request(db, professional, conversation, code=TUESDAY_10, name="Beatriz"):
    return appointments.request(db, professional, conversation, code, name, now=MONDAY_8AM)


# ---------------------------------------------------------------------------
# Reserva
# ---------------------------------------------------------------------------


def test_request_holds_the_slot_for_24_hours_with_a_tentative_event(db, professional, google):
    conversation = _conversation(db, professional)
    booking = _request(db, professional, conversation)

    assert booking.appointment_id
    assert "Pedido registrado: terça, 29/09 às 10:00" in booking.text
    appointment = db.get(models.Appointment, booking.appointment_id)
    assert appointment.status == AppointmentStatus.TENTATIVE
    assert appointment.ends_at - appointment.starts_at == timedelta(minutes=50)
    assert appointment.expires_at == MONDAY_8AM + timedelta(hours=24)

    event = google.created[0]
    assert event["summary"] == "Sessão (a confirmar) · Beatriz"
    assert "+55 21 95555-4444" in event["description"]

    raw = db.execute(text("SELECT patient_name FROM appointments WHERE id = :id"), {"id": appointment.id}).scalar()
    assert raw != "Beatriz"  # cifrado no banco


def test_busy_or_unknown_slots_are_refused(db, professional, google):
    conversation = _conversation(db, professional)
    google.busy = [(datetime(2026, 9, 29, 10, 0, tzinfo=TZ), datetime(2026, 9, 29, 11, 0, tzinfo=TZ))]
    assert _request(db, professional, conversation).text == appointments.TAKEN_MESSAGE
    assert _request(db, professional, conversation, code="2026-09-29T10:30").text == appointments.TAKEN_MESSAGE
    assert "inválido" in _request(db, professional, conversation, code="terça 10h").text
    assert "nome" in _request(db, professional, conversation, code="2026-09-29T11:00", name=" ").text
    assert google.created == []
    assert db.query(models.Appointment).filter_by(professional_id=professional.id).count() == 0


def test_a_second_person_cannot_take_a_held_slot(db, professional, google):
    first = _conversation(db, professional, "5521911111111")
    second = _conversation(db, professional, "5521922222222")
    assert _request(db, professional, first).appointment_id
    # O Google de mentira não sabe do evento criado: quem barra é o banco.
    assert _request(db, professional, second).text == appointments.TAKEN_MESSAGE


def test_two_people_at_the_same_time_get_one_slot(db, professional, google):
    first = _conversation(db, professional, "5521911111111")
    second = _conversation(db, professional, "5521922222222")
    google.create_delay = 0.3  # alarga a janela em que os dois pedidos se cruzam
    results = {}
    start = threading.Barrier(2)

    def book(key, conversation_id):
        session = SessionLocal()
        try:
            prof = session.get(models.Professional, professional.id)
            conv = session.get(models.Conversation, conversation_id)
            start.wait()
            results[key] = appointments.request(session, prof, conv, TUESDAY_10, key, now=MONDAY_8AM)
        finally:
            session.close()

    threads = [threading.Thread(target=book, args=(k, c.id)) for k, c in (("Ana", first), ("Bia", second))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    booked = [r for r in results.values() if r.appointment_id]
    assert len(booked) == 1
    assert len(google.created) == 1
    assert sum(r.text == appointments.TAKEN_MESSAGE for r in results.values()) == 1


def test_the_database_refuses_two_active_requests_for_the_same_slot(db, professional, google):
    conversation = _conversation(db, professional)
    start = datetime(2026, 9, 29, 10, 0, tzinfo=TZ)
    for _ in range(2):
        db.add(
            models.Appointment(
                professional_id=professional.id,
                conversation_id=conversation.id,
                starts_at=start,
                ends_at=start + timedelta(minutes=50),
                status=AppointmentStatus.TENTATIVE,
            )
        )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_a_new_time_on_the_same_day_replaces_the_pending_request(db, professional, google):
    conversation = _conversation(db, professional)
    first = _request(db, professional, conversation)
    second = _request(db, professional, conversation, code="2026-09-29T14:00")
    assert second.appointment_id
    old = db.get(models.Appointment, first.appointment_id)
    db.refresh(old)
    assert old.status == AppointmentStatus.CANCELLED
    assert google.deleted == ["evento-1"]


def test_one_session_per_day_but_many_days_are_fine(db, professional, google):
    conversation = _conversation(db, professional)
    tuesday = _request(db, professional, conversation)
    wednesday = _request(db, professional, conversation, code="2026-09-30T11:00")
    thursday = _request(db, professional, conversation, code="2026-10-01T11:00")
    assert tuesday.appointment_id and wednesday.appointment_id and thursday.appointment_id
    active = appointments.active_for_contact(db, conversation, MONDAY_8AM)
    assert len(active) == 3 and google.deleted == []

    # Com a terça confirmada, outro horário na terça é recusado.
    confirmed = db.get(models.Appointment, tuesday.appointment_id)
    confirmed.status = AppointmentStatus.CONFIRMED
    db.commit()
    refused = _request(db, professional, conversation, code="2026-09-29T15:00")
    assert refused.appointment_id is None and "uma sessão por dia" in refused.text

    note = appointments.pending_note(db, conversation, MONDAY_8AM)
    assert "terça, 29/09 às 10:00 (confirmada)" in note
    assert "quarta, 30/09 às 11:00 (aguardando confirmação)" in note


def test_pending_requests_have_a_ceiling_per_person(db, professional, google, monkeypatch):
    monkeypatch.setattr(appointments.settings, "max_pending_requests", 2)
    conversation = _conversation(db, professional)
    assert _request(db, professional, conversation).appointment_id
    assert _request(db, professional, conversation, code="2026-09-30T11:00").appointment_id
    refused = _request(db, professional, conversation, code="2026-10-01T11:00")
    assert refused.appointment_id is None and "o máximo" in refused.text

    # Trocar o horário de um dia que já tem pedido continua valendo.
    swapped = _request(db, professional, conversation, code="2026-09-29T14:00")
    assert swapped.appointment_id

    # Outra pessoa não é afetada.
    other = _conversation(db, professional, "5521933333333")
    assert _request(db, professional, other, code="2026-10-01T11:00").appointment_id

    # Sessão confirmada não conta no teto.
    confirmed = db.get(models.Appointment, swapped.appointment_id)
    confirmed.status = AppointmentStatus.CONFIRMED
    db.commit()
    assert _request(db, professional, conversation, code="2026-10-02T11:00").appointment_id
    assert "no máximo 2 pedidos" in appointments.pending_note(db, conversation, MONDAY_8AM)


def test_an_overdue_request_no_longer_holds_the_slot(db, professional, google):
    first = _conversation(db, professional, "5521911111111")
    second = _conversation(db, professional, "5521922222222")
    booking = _request(db, professional, first)
    appointment = db.get(models.Appointment, booking.appointment_id)
    appointment.expires_at = MONDAY_8AM - timedelta(minutes=1)
    db.commit()
    assert _request(db, professional, second).appointment_id is None  # índice: o vencido ainda é "tentative"
    assert appointments.expire_overdue(db, now=MONDAY_8AM) == [appointment.id]
    assert _request(db, professional, second).appointment_id
    assert "evento-1" in google.deleted


def test_max_sessions_per_day_closes_the_day(db, professional, google):
    professional.max_sessions_per_day = 1
    db.commit()
    first = _conversation(db, professional, "5521911111111")
    second = _conversation(db, professional, "5521922222222")
    assert _request(db, professional, first).appointment_id
    # Terça já tem 1 sessão: outro horário na terça é recusado; quarta, não.
    assert _request(db, professional, second, code="2026-09-29T14:00").text == appointments.TAKEN_MESSAGE
    assert _request(db, professional, second, code="2026-09-30T14:00").appointment_id


# ---------------------------------------------------------------------------
# Decisão da profissional
# ---------------------------------------------------------------------------


def test_approve_confirms_the_event_and_tells_the_person(client, db, professional, google, no_real_whatsapp):
    conversation = _conversation(db, professional)
    booking = appointments.request(db, professional, conversation, _next_tuesday_code(), "Beatriz")

    response = client.post(f"/calendar/appointments/{booking.appointment_id}/approve")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "confirmed" and body["contact_notified"] is True
    event_id, event = google.updated[0]
    assert event_id == "evento-1" and event["summary"] == "Sessão · Beatriz"
    sent = no_real_whatsapp[-1][1]["text"]["body"]
    assert sent.startswith("Sua sessão com Ana Reserva está confirmada para")

    assert client.post(f"/calendar/appointments/{booking.appointment_id}/reject").status_code == 409


def test_reject_frees_the_slot_even_with_the_whatsapp_window_closed(client, db, professional, google, no_real_whatsapp):
    conversation = _conversation(db, professional)
    booking = appointments.request(db, professional, conversation, _next_tuesday_code(), "Beatriz")
    conversation.last_contact_message_at = models._now() - timedelta(hours=25)
    db.commit()

    body = client.post(f"/calendar/appointments/{booking.appointment_id}/reject").json()
    assert body["status"] == "rejected" and body["contact_notified"] is False
    assert google.deleted == ["evento-1"]
    assert no_real_whatsapp == []


def test_list_shows_pending_first_with_masked_phone(client, db, professional, google):
    conversation = _conversation(db, professional)
    appointments.request(db, professional, conversation, _next_tuesday_code(), "Beatriz")
    items = client.get(f"/calendar/{TEST_SLUG}/appointments").json()
    assert items[0]["status"] == "tentative"
    assert items[0]["patient_name"] == "Beatriz"
    assert items[0]["contact_phone"] == "+55 21 •••••-4444"


# ---------------------------------------------------------------------------
# A SelenIA na conversa
# ---------------------------------------------------------------------------


def test_booking_tool_only_with_permission_to_create_events(client, db, professional, google, monkeypatch):
    calls = []

    def fake_reply(system_prompt, history, tools=None, run_tool=None):
        calls.append((system_prompt, [t["name"] for t in tools or []]))
        if tools and len(tools) > 1:
            run_tool("pedir_agendamento", {"codigo": _next_tuesday_code(), "nome": "Beatriz"})
        return "resposta do bot"

    monkeypatch.setattr(llm, "generate_reply", fake_reply)
    sent = []
    monkeypatch.setattr("app.services.notifications.notify_appointment_request", sent.append)

    client.post("/chat/simulate", json={"professional_slug": TEST_SLUG, "message": "quero marcar"})
    prompt, tool_names = calls[-1]
    assert tool_names == ["consultar_horarios_livres", "pedir_agendamento", "pedir_remarcacao", "pedir_cancelamento"]
    assert "Nunca diga que a sessão está confirmada" in prompt
    assert len(sent) == 1  # e-mail para a profissional confirmar

    professional.calendar_connection.scopes = f"openid email {calendar.SCOPE_FREEBUSY}"
    db.commit()
    client.post("/chat/simulate", json={"professional_slug": TEST_SLUG, "message": "quero marcar"})
    assert calls[-1][1] == ["consultar_horarios_livres"]


def test_slot_list_carries_codes_and_the_pending_request(db, professional, google):
    conversation = _conversation(db, professional)
    _request(db, professional, conversation)
    text_out = calendar.describe_for_assistant(
        professional, MONDAY_8AM, pending=appointments.pending_note(db, conversation, MONDAY_8AM)
    )
    assert "terça, 29/09 às 10:00 (aguardando confirmação)" in text_out
    # O pedido das 10:00 (50 min) ocupa as 10:00 e as 10:30.
    assert "(2026-09-29): 11:00, 11:30" in text_out
    assert "ex.: 2026-09-29T10:00" in text_out


def _next_tuesday_code():
    """Uma terça às 10h daqui a mais de 12h, para testes que usam o relógio real."""
    now = datetime.now(TZ)
    day = now.date() + timedelta(days=2)
    while day.weekday() != 1:
        day += timedelta(days=1)
    return f"{day:%Y-%m-%d}T10:00"


# ---------------------------------------------------------------------------
# Calendário do painel
# ---------------------------------------------------------------------------


def test_professional_books_a_session_from_the_panel(client, db, professional, google):
    code = _next_tuesday_code()
    response = client.post(
        f"/calendar/{TEST_SLUG}/events",
        json={"kind": "session", "title": "Carla", "starts_at": code, "minutes": 50},
    )
    assert response.status_code == 201
    assert google.created[-1]["summary"] == "Sessão · Carla"
    appointment = db.query(models.Appointment).filter_by(professional_id=professional.id).one()
    assert appointment.status == AppointmentStatus.CONFIRMED and appointment.source == "panel"
    assert appointment.conversation_id is None

    items = client.get(f"/calendar/{TEST_SLUG}/appointments").json()
    assert items[0]["source"] == "panel" and items[0]["channel"] is None

    # O mesmo horário não pode ser marcado de novo.
    again = client.post(
        f"/calendar/{TEST_SLUG}/events",
        json={"kind": "session", "title": "Dani", "starts_at": code, "minutes": 50},
    )
    assert again.status_code == 409


def test_a_block_only_goes_to_google(client, db, professional, google):
    response = client.post(
        f"/calendar/{TEST_SLUG}/events",
        json={"kind": "block", "title": "Supervisão", "starts_at": _next_tuesday_code(), "minutes": 60},
    )
    assert response.status_code == 201
    assert google.created[-1]["summary"] == "Supervisão"
    assert db.query(models.Appointment).filter_by(professional_id=professional.id).count() == 0


def test_panel_sessions_count_toward_the_daily_limit(db, professional, google):
    professional.max_sessions_per_day = 1
    db.commit()
    appointments.create_by_professional(db, professional, "session", "Carla", "2026-09-29T15:00", 50)
    conversation = _conversation(db, professional)
    assert _request(db, professional, conversation).text == appointments.TAKEN_MESSAGE


def test_week_view_marks_maria_events(client, db, professional, google, monkeypatch):
    conversation = _conversation(db, professional)
    booking = appointments.request(db, professional, conversation, _next_tuesday_code(), "Beatriz")
    start = datetime(2026, 9, 29, 10, 0, tzinfo=TZ)
    monkeypatch.setattr(
        calendar,
        "list_events",
        lambda connection, first, last: [
            {"id": "evento-1", "title": "Sessão (a confirmar) · Beatriz", "starts_at": start,
             "ends_at": start + timedelta(minutes=50), "all_day": False, "busy": True},
            {"id": "outro", "title": "Dentista", "starts_at": start, "ends_at": start, "all_day": False, "busy": True},
        ],
    )
    events = client.get(f"/calendar/{TEST_SLUG}/events?start=2026-09-28").json()
    assert events[0]["kind"] == "maria_tentative" and events[0]["appointment_id"] == booking.appointment_id
    assert events[1]["kind"] == "google" and events[1]["title"] == "Dentista"


def test_week_view_needs_the_events_permission(client, db, professional, google):
    professional.calendar_connection.scopes = f"openid email {calendar.SCOPE_FREEBUSY}"
    db.commit()
    assert client.get(f"/calendar/{TEST_SLUG}/events?start=2026-09-28").status_code == 409


def test_max_sessions_per_day_is_validated(client, professional):
    assert client.patch(f"/professionals/{TEST_SLUG}", json={"max_sessions_per_day": 0}).status_code == 422
    assert client.patch(f"/professionals/{TEST_SLUG}", json={"max_sessions_per_day": 6}).json()["max_sessions_per_day"] == 6


# ---------------------------------------------------------------------------
# Remarcar e cancelar (pedidos pela pessoa; a profissional confirma)
# ---------------------------------------------------------------------------


def _next_code(weekday, hour="11:00"):
    """Próximo dia da semana (0 = segunda) depois da terça de `_next_tuesday_code`."""
    tuesday = datetime.strptime(_next_tuesday_code()[:10], "%Y-%m-%d").date()
    day = tuesday + timedelta(days=1)
    while day.weekday() != weekday:
        day += timedelta(days=1)
    return f"{day:%Y-%m-%d}T{hour}"


def _confirmed_session(client, db, professional):
    conversation = _conversation(db, professional)
    booking = appointments.request(db, professional, conversation, _next_tuesday_code(), "Beatriz")
    assert client.post(f"/calendar/appointments/{booking.appointment_id}/approve").status_code == 200
    return conversation, db.get(models.Appointment, booking.appointment_id)


def _last_text(no_real_whatsapp):
    return no_real_whatsapp[-1][1]["text"]["body"]


def test_reschedule_keeps_the_old_session_until_the_professional_confirms(
    client, db, professional, google, no_real_whatsapp
):
    conversation, old = _confirmed_session(client, db, professional)
    thursday = _next_code(3)
    booking = appointments.request_reschedule(db, professional, conversation, _next_tuesday_code(), thursday)
    assert booking.appointment_id and "continua marcada" in booking.text
    db.refresh(old)
    assert old.status == AppointmentStatus.CONFIRMED  # a antiga continua de pé

    listed = {a["id"]: a for a in client.get(f"/calendar/{TEST_SLUG}/appointments").json()}
    new = listed[booking.appointment_id]
    assert new["kind"] == "reschedule" and new["awaiting_decision"] and new["replaces_label"]

    assert client.post(f"/calendar/appointments/{booking.appointment_id}/approve").status_code == 200
    db.expire_all()
    assert db.get(models.Appointment, old.id).status == AppointmentStatus.CANCELLED
    assert db.get(models.Appointment, booking.appointment_id).status == AppointmentStatus.CONFIRMED
    assert old.calendar_event_id in google.deleted
    assert _last_text(no_real_whatsapp).startswith("Ana Reserva confirmou a troca")


def test_rejected_reschedule_leaves_the_old_session(client, db, professional, google, no_real_whatsapp):
    conversation, old = _confirmed_session(client, db, professional)
    booking = appointments.request_reschedule(db, professional, conversation, _next_tuesday_code(), _next_code(3))
    assert client.post(f"/calendar/appointments/{booking.appointment_id}/reject").status_code == 200
    db.expire_all()
    assert db.get(models.Appointment, old.id).status == AppointmentStatus.CONFIRMED
    assert "continua marcada" in _last_text(no_real_whatsapp)


def test_reschedule_rules(client, db, professional, google):
    conversation, _ = _confirmed_session(client, db, professional)
    tuesday = _next_tuesday_code()
    assert appointments.request_reschedule(db, professional, conversation, "2026-01-01T10:00", _next_code(3)).text == (
        appointments.NOT_FOUND
    )
    # Outra pessoa não mexe na sessão da Beatriz.
    other = _conversation(db, professional, "5521933333333")
    assert appointments.request_reschedule(db, professional, other, tuesday, _next_code(3)).appointment_id is None
    # Um pedido de troca por vez.
    assert appointments.request_reschedule(db, professional, conversation, tuesday, _next_code(3)).appointment_id
    second = appointments.request_reschedule(db, professional, conversation, tuesday, _next_code(4))
    assert second.appointment_id is None and "Já há um pedido de troca" in second.text


def test_cancel_of_a_confirmed_session_waits_for_the_professional(client, db, professional, google, no_real_whatsapp):
    conversation, session = _confirmed_session(client, db, professional)
    booking = appointments.request_cancel(db, professional, conversation, _next_tuesday_code())
    assert booking.appointment_id == session.id and "Nunca diga que já está cancelada" in booking.text
    db.refresh(session)
    assert session.status == AppointmentStatus.CONFIRMED and session.cancel_requested_at

    [listed] = [a for a in client.get(f"/calendar/{TEST_SLUG}/appointments").json() if a["id"] == session.id]
    assert listed["kind"] == "cancel" and listed["awaiting_decision"]
    assert "cancelamento pedido" in appointments.pending_note(db, conversation)

    assert client.post(f"/calendar/appointments/{session.id}/approve").status_code == 200
    db.refresh(session)
    assert session.status == AppointmentStatus.CANCELLED
    assert session.calendar_event_id in google.deleted
    assert _last_text(no_real_whatsapp).startswith("Ana Reserva confirmou o cancelamento")


def test_rejected_cancel_keeps_the_session(client, db, professional, google, no_real_whatsapp):
    conversation, session = _confirmed_session(client, db, professional)
    appointments.request_cancel(db, professional, conversation, _next_tuesday_code())
    assert client.post(f"/calendar/appointments/{session.id}/reject").status_code == 200
    db.refresh(session)
    assert session.status == AppointmentStatus.CONFIRMED and session.cancel_requested_at is None
    assert "continua marcada" in _last_text(no_real_whatsapp)


def test_a_pending_request_can_be_withdrawn_right_away(db, professional, google):
    conversation = _conversation(db, professional)
    booking = appointments.request(db, professional, conversation, _next_tuesday_code(), "Beatriz")
    withdrawn = appointments.request_cancel(db, professional, conversation, _next_tuesday_code())
    assert withdrawn.appointment_id is None and "desfeito" in withdrawn.text
    assert db.get(models.Appointment, booking.appointment_id).status == AppointmentStatus.CANCELLED
    assert google.deleted == ["evento-1"]
