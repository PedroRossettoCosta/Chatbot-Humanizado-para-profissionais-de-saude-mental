"""Em consulta pelo botão ou pela agenda, a SelenIA sabendo disso e os
avisos guardados até o fim da consulta (Pedro, 03/11/2026)."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app import models
from app.config import settings
from app.services import availability, calendar, handoff, llm, notifications

TEST_SLUG = "test-pytest-em-consulta"
NOW = datetime(2026, 11, 3, 21, 30, tzinfo=timezone.utc)


def _block(start_min: int, end_min: int) -> tuple[datetime, datetime]:
    return NOW + timedelta(minutes=start_min), NOW + timedelta(minutes=end_min)


# ---------------------------------------------------------------------------
# Leitura da agenda
# ---------------------------------------------------------------------------


def test_no_block_now_is_not_in_session():
    assert availability.session_end_from_busy([_block(30, 80)], NOW) is None


def test_block_happening_now_ends_at_its_end():
    assert availability.session_end_from_busy([_block(-20, 30)], NOW) == NOW + timedelta(minutes=30)


def test_back_to_back_sessions_count_as_one():
    busy = [_block(-20, 30), _block(30, 80), _block(100, 150)]
    assert availability.session_end_from_busy(busy, NOW) == NOW + timedelta(minutes=80)


def test_all_day_block_is_not_a_session():
    assert availability.session_end_from_busy([_block(-600, 840)], NOW) is None


def _fake_professional(**kw):
    base = dict(id="prof-x", is_in_session=False, in_session_until=None, calendar_connection=object())
    return SimpleNamespace(**{**base, **kw})


@pytest.fixture(autouse=True)
def fresh_cache():
    availability.clear_cache()
    yield
    availability.clear_cache()


def test_agenda_turns_session_on(monkeypatch):
    monkeypatch.setattr(calendar, "busy_intervals", lambda connection, start, end: [_block(-10, 40)])
    status = availability.current(_fake_professional(), NOW)
    assert status == availability.Availability(True, NOW + timedelta(minutes=40), availability.SOURCE_AGENDA)


def test_button_wins_over_agenda(monkeypatch):
    monkeypatch.setattr(calendar, "busy_intervals", lambda connection, start, end: [_block(-10, 40)])
    until = NOW + timedelta(minutes=90)
    status = availability.current(_fake_professional(is_in_session=True, in_session_until=until), NOW)
    assert status == availability.Availability(True, until, availability.SOURCE_MANUAL)


def test_google_failure_means_not_in_session(monkeypatch):
    def fail(*_):
        raise calendar.CalendarError("fora do ar")

    monkeypatch.setattr(calendar, "busy_intervals", fail)
    assert availability.current(_fake_professional(), NOW) == availability.NOT_IN_SESSION


def test_agenda_is_read_once_per_minute(monkeypatch):
    calls = []
    monkeypatch.setattr(calendar, "busy_intervals", lambda *a: calls.append(1) or [])
    professional = _fake_professional()
    availability.current(professional, NOW)
    availability.current(professional, NOW)
    assert len(calls) == 1


def test_without_calendar_never_calls_google(monkeypatch):
    monkeypatch.setattr(calendar, "busy_intervals", lambda *a: pytest.fail("não devia chamar o Google"))
    assert availability.current(_fake_professional(calendar_connection=None), NOW) == availability.NOT_IN_SESSION


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------


def _prompt_professional():
    return SimpleNamespace(
        name="Marília Rossetto", pronouns=None, extra_never_say=None, audience_description=None,
        service_info=None, session_minutes=None, payment_methods=None, voice_tone=None,
        working_hours=None, calendar_connection=None, voice_examples=None,
    )


def test_prompt_tells_until_when_in_session():
    until = datetime(2026, 11, 4, 1, 19, tzinfo=timezone.utc)  # 22:19 em Brasília
    status = availability.Availability(True, until, availability.SOURCE_AGENDA)
    prompt = llm.build_system_prompt(_prompt_professional(), [], status)
    assert "está em atendimento agora, até as 22:19" in prompt
    # Fica fora da parte com cache: muda ao longo do dia.
    assert "até as 22:19" in prompt.partition(llm.CONTEXT_HEADER)[2]


def test_prompt_open_session_has_no_time():
    status = availability.Availability(True, None, availability.SOURCE_MANUAL)
    prompt = llm.build_system_prompt(_prompt_professional(), [], status)
    assert "sem horário certo para terminar" in prompt


def test_prompt_out_of_session_says_nothing():
    prompt = llm.build_system_prompt(_prompt_professional(), [], availability.NOT_IN_SESSION)
    assert "\nAGORA\n" not in prompt


# ---------------------------------------------------------------------------
# Conversa e e-mails
# ---------------------------------------------------------------------------


@pytest.fixture
def professional(db, monkeypatch):
    monkeypatch.setattr(llm, "generate_reply", lambda system_prompt, history, **_: "resposta do bot")
    monkeypatch.setattr(settings, "smtp_host", "smtp.teste.local")
    _cleanup(db)
    db.add(models.Professional(slug=TEST_SLUG, name="Marília Rossetto", alert_email="marilia@exemplo.com"))
    db.commit()
    yield db.query(models.Professional).filter_by(slug=TEST_SLUG).one()
    _cleanup(db)


def _cleanup(db):
    existing = db.query(models.Professional).filter_by(slug=TEST_SLUG).first()
    if existing:
        db.delete(existing)
        db.commit()


def _send(client, text, session_id=None):
    payload = {"professional_slug": TEST_SLUG, "message": text, "session_id": session_id}
    response = client.post("/chat/simulate", json=payload)
    assert response.status_code == 200
    return response.json()


def test_agenda_session_shows_time_to_contact_and_panel(client, professional, monkeypatch):
    until = models._now() + timedelta(minutes=40)
    monkeypatch.setattr(availability, "_busy_around", lambda prof, now: [(now - timedelta(minutes=10), until)])

    shown = client.get(f"/professionals/{TEST_SLUG}").json()
    assert shown["in_session"] and shown["in_session_source"] == "agenda"

    first = _send(client, "oi")
    asked = _send(client, "posso falar com ela?", first["session_id"])
    assert asked["reply"] == handoff.IN_SESSION_UNTIL_MESSAGE.format(
        name="Marília Rossetto", until=availability.format_until(until)
    )


def test_requests_wait_for_end_of_session_in_one_email(db, client, professional, no_real_email):
    client.put(f"/professionals/{TEST_SLUG}/in-session", json={"minutes": 50})
    a = _send(client, "oi")
    _send(client, "quero falar com a Marília", a["session_id"])
    b = _send(client, "boa noite")
    _send(client, "posso falar com ela?", b["session_id"])
    assert no_real_email == []  # nada sai durante a consulta

    db.expire_all()
    assert db.get(models.Professional, professional.id).held_notices_since is not None
    notifications.send_held_notices()
    assert no_real_email == []  # ainda em consulta

    client.delete(f"/professionals/{TEST_SLUG}/in-session")
    notifications.send_held_notices()
    [email] = no_real_email
    assert "2 pessoas" in email["Subject"]
    body = email.get_content()
    assert "2 pessoas: pediu para falar com você" in body
    assert "Marília" not in body.split("Olá, Marília Rossetto.")[1]  # nada da conversa
    db.expire_all()
    assert db.get(models.Professional, professional.id).held_notices_since is None

    notifications.send_held_notices()
    assert len(no_real_email) == 1  # o resumo sai uma vez só


def test_answered_requests_leave_the_summary(db, client, professional, no_real_email):
    client.put(f"/professionals/{TEST_SLUG}/in-session", json={"minutes": 50})
    a = _send(client, "oi")
    _send(client, "quero falar com a Marília", a["session_id"])
    # Ela respondeu pelo painel durante a consulta.
    client.post(f"/conversations/{a['conversation_id']}/messages", json={"content": "oi, aqui é a Marília"})
    client.delete(f"/professionals/{TEST_SLUG}/in-session")
    notifications.send_held_notices()
    assert no_real_email == []
    db.expire_all()
    assert db.get(models.Professional, professional.id).held_notices_since is None


def test_safety_alerts_never_wait(client, professional, no_real_email):
    client.put(f"/professionals/{TEST_SLUG}/in-session", json={"minutes": 50})
    _send(client, "to pensando em me matar")
    [email] = no_real_email
    assert "EMERGÊNCIA" in email["Subject"]
