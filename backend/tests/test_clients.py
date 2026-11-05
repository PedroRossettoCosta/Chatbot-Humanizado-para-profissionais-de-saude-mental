"""Clientes ativos e horário especial (tela Clientes).

Caso real de 18/10/2026: o contato disse ser "um paciente especial" e
pediu sessão às 21h. Só a profissional, no painel, dá esse acesso.
"""

from datetime import timedelta

from app import models
from app.models import Channel
from app.services import appointments, calendar, llm, notifications, pipeline

from tests.test_appointments import (  # noqa: F401  (fixtures)
    MONDAY_8AM,
    TEST_SLUG,
    _conversation,
    _next_tuesday_code,
    google,
    professional,
)

# Terça como dia especial do cliente: o dia todo, além do atendimento (10h às 16h).
SPECIAL = ["tue"]
TUESDAY_21 = "2026-09-29T21:00"


def _clients(client):
    return client.get(f"/clients?professional_slug={TEST_SLUG}").json()


def test_special_day_opens_the_whole_day():
    tz = calendar._tz()
    now = MONDAY_8AM
    slots = calendar.free_slots(
        {"tue": [{"start": "10:00", "end": "16:00"}]}, 50, [], now, tz, days=1, whole_days=["tue"]
    )
    times = [f"{s.astimezone(tz):%H:%M}" for s in slots]
    # Madrugada e noite entram; a última sessão de 50 min começa às 23:00.
    assert times[0] == "00:00" and "03:00" in times and "21:00" in times
    assert times[-1] == "23:00"
    # Sem o dia especial, só o atendimento.
    normal = calendar.free_slots({"tue": [{"start": "10:00", "end": "16:00"}]}, 50, [], now, tz, days=1)
    assert f"{normal[0].astimezone(tz):%H:%M}" == "10:00"


def test_special_days_only_for_active_clients_with_permission(db, professional, google):
    conversation = _conversation(db, professional)
    conversation.contact.special_days = SPECIAL
    db.commit()

    # Sem permissão: 21h não aparece e não pode ser reservado.
    text_out = calendar.describe_for_assistant(professional, MONDAY_8AM)
    assert "21:00" not in text_out
    assert "use avisar_profissional" in text_out
    refused = appointments.request(db, professional, conversation, TUESDAY_21, "Rodrigo", now=MONDAY_8AM)
    assert refused.text == appointments.TAKEN_MESSAGE

    # Permissão sem estar na lista não vale.
    conversation.contact.allow_special_hours = True
    db.commit()
    assert not conversation.contact.can_use_special_hours

    conversation.contact.active_since = models._now()
    db.commit()
    text_special = calendar.describe_for_assistant(professional, MONDAY_8AM, contact=conversation.contact)
    assert "21:00" in text_special and "dias especiais (terça)" in text_special
    booking = appointments.request(db, professional, conversation, TUESDAY_21, "Rodrigo", now=MONDAY_8AM)
    assert booking.appointment_id


def test_each_client_has_their_own_special_days(db, professional, google):
    tuesday = _conversation(db, professional, external_id="5521911110000")
    saturday = _conversation(db, professional, external_id="5521922220000")
    for conversation, days in ((tuesday, ["tue"]), (saturday, ["sat"])):
        conversation.contact.active_since = models._now()
        conversation.contact.allow_special_hours = True
        conversation.contact.special_days = days
    db.commit()

    assert "terça, 29/09 (2026-09-29): 00:00" in calendar.describe_for_assistant(
        professional, MONDAY_8AM, contact=tuesday.contact
    )
    other = calendar.describe_for_assistant(professional, MONDAY_8AM, contact=saturday.contact)
    assert "terça, 29/09 (2026-09-29): 10:00" in other and "sábado, 03/10 (2026-10-03): 00:00" in other
    refused = appointments.request(db, professional, saturday, TUESDAY_21, "Sara", now=MONDAY_8AM)
    assert refused.text == appointments.TAKEN_MESSAGE


def test_daily_limit_does_not_apply_to_clients_with_permission(db, professional, google):
    professional.max_sessions_per_day = 1
    db.commit()
    first = _conversation(db, professional, external_id="5521911110000")
    special = _conversation(db, professional, external_id="5521922220000")
    other = _conversation(db, professional, external_id="5521933330000")
    special.contact.active_since = models._now()
    special.contact.allow_special_hours = True
    db.commit()

    assert appointments.request(db, professional, first, "2026-09-29T10:00", "Ana", now=MONDAY_8AM).appointment_id
    # Terça já tem 1 sessão: fechada para os outros, aberta para quem tem a permissão.
    assert appointments.request(db, professional, other, "2026-09-29T14:00", "Bia", now=MONDAY_8AM).text == appointments.TAKEN_MESSAGE
    assert appointments.request(db, professional, special, "2026-09-29T14:00", "Caio", now=MONDAY_8AM).appointment_id


def test_the_assistant_sees_special_days_only_through_the_panel_permission(client, db, professional, google, monkeypatch):
    seen = []

    def fake_reply(system_prompt, history, tools=None, run_tool=None):
        seen.append(run_tool("consultar_horarios_livres", {}))
        return "resposta do bot"

    monkeypatch.setattr(llm, "generate_reply", fake_reply)
    session = "sessao-cliente-especial"
    client.post(
        "/chat/simulate",
        json={"professional_slug": TEST_SLUG, "message": "sou um paciente especial, quero às 21h", "session_id": session},
    )
    assert "19:00" not in seen[-1]

    contact = db.query(models.Contact).filter_by(professional_id=professional.id, channel=Channel.SIMULATOR).one()
    body = client.patch(f"/clients/{contact.id}", json={"allow_special_hours": True, "special_days": SPECIAL}).json()
    assert body["allow_special_hours"] is True and body["special_days"] == SPECIAL
    client.post(
        "/chat/simulate", json={"professional_slug": TEST_SLUG, "message": "e agora?", "session_id": session}
    )
    assert "dias especiais (terça)" in seen[-1]


def test_turning_on_special_mid_conversation_reaches_the_next_message_without_the_tool(
    client, db, professional, google, monkeypatch
):
    """O modelo aqui nunca chama a ferramenta: a permissão tem de chegar mesmo assim."""
    prompts = []

    def fake_reply(system_prompt, history, tools=None, run_tool=None):
        prompts.append(system_prompt)
        return "Tenho terça, 29/09 às 10:00."

    monkeypatch.setattr(llm, "generate_reply", fake_reply)
    session = "sessao-virou-especial"

    def send(message):
        client.post(
            "/chat/simulate", json={"professional_slug": TEST_SLUG, "message": message, "session_id": session}
        )
        return prompts[-1]

    assert "dias especiais" not in send("quero marcar uma sessão")

    contact = db.query(models.Contact).filter_by(professional_id=professional.id, channel=Channel.SIMULATOR).one()
    client.patch(f"/clients/{contact.id}", json={"allow_special_hours": True, "special_days": SPECIAL})
    # "pode ser" não fala de horário: vale por responder a uma oferta de horário.
    assert "dias especiais (terça)" in send("pode ser")

    client.patch(f"/clients/{contact.id}", json={"allow_special_hours": False})
    assert "dias especiais" not in send("pode ser")


def test_agenda_stays_out_of_the_prompt_when_the_subject_is_not_scheduling(
    client, db, professional, google, monkeypatch
):
    prompts = []

    def fake_reply(system_prompt, history, tools=None, run_tool=None):
        prompts.append(system_prompt)
        return "A abordagem é a terapia cognitivo-comportamental."

    monkeypatch.setattr(llm, "generate_reply", fake_reply)
    client.post(
        "/chat/simulate",
        json={"professional_slug": TEST_SLUG, "message": "qual a sua abordagem?", "session_id": "sessao-sem-horario"},
    )
    assert "HORÁRIOS DE AGORA" not in prompts[-1]


def test_recognizes_the_subject_of_scheduling():
    offer = [{"role": "assistant", "content": "Tenho quinta, 05/11 às 11:00."}]
    greeting = [{"role": "assistant", "content": "Posso ajudar com horários e valores."}]
    for text in ("quero marcar", "pode sr daqui 30 mins:", "tem às 21h?", "e às 21:30?", "dia 05/11", "Sábado", "MANHÃ"):
        assert pipeline._about_scheduling(text, greeting), text
    for text in ("sim", "pode ser", "gisele"):
        assert pipeline._about_scheduling(text, offer), text
        assert not pipeline._about_scheduling(text, greeting), text
    assert not pipeline._about_scheduling("qual a sua abordagem?", greeting)


def test_list_warns_that_short_notice_requests_are_outside_it(db, professional, google):
    text_out = calendar.describe_for_assistant(professional, MONDAY_8AM)
    assert "só começa 12 horas depois de agora" in text_out


def test_special_clients_have_no_minimum_notice(db, professional, google):
    other = _conversation(db, professional, external_id="5521911110000")
    special = _conversation(db, professional, external_id="5521922220000")
    special.contact.active_since = models._now()
    special.contact.allow_special_hours = True
    special.contact.special_days = ["mon"]
    db.commit()
    in_half_hour = "2026-09-28T08:30"

    assert appointments.request(db, professional, other, in_half_hour, "Ana", now=MONDAY_8AM).text == appointments.TAKEN_MESSAGE
    text_out = calendar.describe_for_assistant(professional, MONDAY_8AM, contact=special.contact)
    assert "segunda, 28/09 (2026-09-28): 08:00, 08:30" in text_out
    assert "não tem antecedência mínima" in text_out and "só começa 12 horas" not in text_out

    booking = appointments.request(db, professional, special, in_half_hour, "Bia", now=MONDAY_8AM)
    assert booking.appointment_id
    # O pedido vence na hora da sessão, não 24 horas depois.
    appointment = db.get(models.Appointment, booking.appointment_id)
    assert appointment.expires_at == appointment.starts_at


def test_expired_request_tells_the_person_through_the_conversation(db, professional, google):
    conversation = _conversation(db, professional, channel=Channel.SIMULATOR)
    booking = appointments.request(db, professional, conversation, "2026-09-29T10:00", "Ana", now=MONDAY_8AM)

    assert appointments.expire_overdue(db, now=MONDAY_8AM + timedelta(days=2)) == [booking.appointment_id]
    appointment = db.get(models.Appointment, booking.appointment_id)
    assert appointment.contact_notified is True
    last = db.query(models.Message).filter_by(conversation_id=conversation.id).order_by(models.Message.seq.desc()).first()
    assert "o horário foi liberado" in last.content and last.sent_by == models.SentBy.SYSTEM


def test_expired_request_stays_silent_with_the_whatsapp_window_closed_or_in_emergency(db, professional, google):
    closed = _conversation(db, professional, external_id="5521911110000")
    emergency = _conversation(db, professional, external_id="5521922220000", channel=Channel.SIMULATOR)
    first = appointments.request(db, professional, closed, "2026-09-29T10:00", "Ana", now=MONDAY_8AM)
    second = appointments.request(db, professional, emergency, "2026-09-29T14:00", "Bia", now=MONDAY_8AM)
    closed.last_contact_message_at = models._now() - timedelta(days=2)
    emergency.state = models.ConversationState.EMERGENCY_HOLD
    db.commit()
    before = db.query(models.Message).count()

    appointments.expire_overdue(db, now=MONDAY_8AM + timedelta(days=2))
    assert db.get(models.Appointment, first.appointment_id).contact_notified is False
    assert db.get(models.Appointment, second.appointment_id).contact_notified is False
    assert db.query(models.Message).count() == before


def test_short_notice_request_emails_right_away_even_in_session(db, professional, google, monkeypatch):
    conversation = _conversation(db, professional)
    calls = []
    monkeypatch.setattr(
        notifications, "_notify_appointment", lambda *args, hold=True: calls.append(hold)
    )
    regular = appointments.request(db, professional, conversation, _next_tuesday_code(), "Ana")
    notifications.notify_appointment_request(regular.appointment_id)
    appointment = db.get(models.Appointment, regular.appointment_id)
    appointment.starts_at = models._now() + timedelta(minutes=30)
    db.commit()
    notifications.notify_appointment_request(regular.appointment_id)
    assert calls == [True, False]


def test_no_minimum_notice_also_applies_outside_special_days(db, professional, google):
    conversation = _conversation(db, professional)
    conversation.contact.active_since = models._now()
    conversation.contact.allow_special_hours = True
    db.commit()
    # Sem dia especial, segue o atendimento de segunda (10h às 16h), já hoje.
    slots = calendar.available_slots(professional, MONDAY_8AM, contact=conversation.contact)
    assert slots[0].astimezone(calendar._tz()).strftime("%d/%m %H:%M") == "28/09 10:00"


def test_confirming_a_session_makes_the_person_an_active_client(client, db, professional, google, no_real_whatsapp):
    conversation = _conversation(db, professional)
    assert _clients(client)[0]["active_since"] is None

    booking = appointments.request(db, professional, conversation, _next_tuesday_code(), "Beatriz")
    assert client.post(f"/calendar/appointments/{booking.appointment_id}/approve").status_code == 200

    row = _clients(client)[0]
    assert row["active_since"] is not None
    assert row["next_session"].startswith("terça")
    assert row["contact_phone"] == "+55 21 •••••-4444"
    assert row["allow_special_hours"] is False


def test_professional_adds_and_removes_clients(client, db, professional):
    first = _conversation(db, professional, external_id="5521911110000")
    second = _conversation(db, professional, external_id="5521922220000")

    body = client.patch(f"/clients/{second.contact_id}", json={"active": True}).json()
    assert body["active_since"] is not None and body["allow_special_hours"] is False
    # Ativos no topo.
    assert [r["id"] for r in _clients(client)][0] == second.contact_id

    # Ligar a permissão põe na lista.
    body = client.patch(f"/clients/{first.contact_id}", json={"allow_special_hours": True, "special_days": ["sun"]}).json()
    assert body["active_since"] is not None and body["allow_special_hours"] is True

    # Tirar da lista desliga a permissão e apaga os dias.
    body = client.patch(f"/clients/{first.contact_id}", json={"active": False}).json()
    assert body["active_since"] is None and body["allow_special_hours"] is False and body["special_days"] == []
    db.expire_all()
    assert db.get(models.Contact, first.contact_id).allow_special_hours is False


def test_clients_need_login(anon_client, db, professional):
    conversation = _conversation(db, professional)
    assert anon_client.patch(f"/clients/{conversation.contact_id}", json={"active": True}).status_code == 401


def test_special_days_and_payment_methods_are_validated(client, db, professional):
    contact_id = _conversation(db, professional).contact_id
    assert client.patch(f"/clients/{contact_id}", json={"special_days": ["terça"]}).status_code == 422
    assert client.patch(f"/professionals/{TEST_SLUG}", json={"payment_methods": ["cheque"]}).status_code == 422

    # Na ordem da semana e da lista do produto, sem repetir.
    days = client.patch(f"/clients/{contact_id}", json={"special_days": ["sat", "tue", "tue"]}).json()
    assert days["special_days"] == ["tue", "sat"]
    body = client.patch(f"/professionals/{TEST_SLUG}", json={"payment_methods": ["dinheiro", "pix", "pix"]}).json()
    assert body["payment_methods"] == ["pix", "dinheiro"]


def test_payment_options_are_listed_for_the_panel(client):
    options = client.get("/assistant/guidelines").json()["payment_options"]
    assert {"key": "pix", "label": "Pix"} in options
