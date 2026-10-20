"""Agenda: horários livres, horário de atendimento, conexão com o Google
e a ferramenta que a SelenIA usa na conversa.

Nenhum teste fala com o Google: a troca do código, a verificação da conta,
a revogação e o livre/ocupado são substituídos.
"""

from datetime import datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text

from app import models
from app.config import settings
from app.services import calendar, llm

TEST_SLUG = "teste-agenda"
TZ = ZoneInfo("America/Sao_Paulo")
WEEKDAYS_10_16 = {day: [{"start": "10:00", "end": "16:00"}] for day in ("mon", "tue", "wed", "thu", "fri")}
# Segunda, 28/09/2026, 8h em Brasília.
MONDAY_8AM = datetime(2026, 9, 28, 8, 0, tzinfo=TZ)


def _at(day, hour, minute=0):
    return datetime(2026, 9, day, hour, minute, tzinfo=TZ)


def _cleanup(db):
    existing = db.query(models.Professional).filter_by(slug=TEST_SLUG).first()
    if existing:
        db.delete(existing)
        db.commit()


@pytest.fixture
def professional(db):
    _cleanup(db)
    prof = models.Professional(slug=TEST_SLUG, name="Ana Agenda", session_minutes=50, working_hours=WEEKDAYS_10_16)
    db.add(prof)
    db.commit()
    yield prof
    db.expire_all()
    _cleanup(db)


@pytest.fixture
def google(monkeypatch):
    """Google de mentira. `google.tokens` é a resposta da troca do código."""
    state = SimpleNamespace(
        tokens={
            "scope": f"openid email {calendar.SCOPE_FREEBUSY}",
            "refresh_token": "refresh-de-teste",
            "id_token": "id-token-de-teste",
        },
        revoked=[],
        busy=[],
    )
    monkeypatch.setattr(settings, "google_client_id", "client-id-de-teste")
    monkeypatch.setattr(settings, "google_client_secret", "segredo-de-teste")
    monkeypatch.setattr(calendar, "_exchange_code", lambda code: state.tokens)
    monkeypatch.setattr(
        calendar.id_token, "verify_oauth2_token", lambda token, request, audience, **kwargs: {"email": "Agenda@Gmail.com"}
    )
    monkeypatch.setattr(calendar, "_revoke", state.revoked.append)
    monkeypatch.setattr(calendar, "busy_intervals", lambda connection, start, end: state.busy)
    return state


# ---------------------------------------------------------------------------
# Cálculo dos horários livres
# ---------------------------------------------------------------------------


def _half_hours(day, first, last):
    """Inícios de 30 em 30 minutos, de `first` a `last` (horas, com .5)."""
    out, t = [], first
    while t <= last:
        out.append(_at(day, int(t), 30 if t % 1 else 0))
        t += 0.5
    return out


def test_every_free_half_hour_start_where_the_session_fits():
    slots = calendar.free_slots(WEEKDAYS_10_16, 50, [], MONDAY_8AM, TZ, days=1)
    # Segunda: tudo começa antes das 12h de antecedência. Terça: de 10:00
    # a 15:00 (15:30 + 50 min passaria das 16h).
    assert slots == _half_hours(29, 10, 15)


def test_busy_time_removes_every_start_it_touches():
    busy = [(_at(29, 11, 30), _at(29, 12, 30))]
    slots = calendar.free_slots(WEEKDAYS_10_16, 50, busy, MONDAY_8AM, TZ, days=1)
    # 11:00, 11:30 e 12:00 encostam no ocupado; 10:30 (até 11:20) não.
    assert slots == [_at(29, 10), _at(29, 10, 30)] + _half_hours(29, 12.5, 15)


def test_a_busy_block_ending_exactly_at_the_start_does_not_block():
    busy = [(_at(29, 9), _at(29, 10))]
    slots = calendar.free_slots({"tue": [{"start": "10:00", "end": "11:00"}]}, 50, busy, MONDAY_8AM, TZ, days=1)
    assert slots == [_at(29, 10)]


def test_long_sessions_fit_inside_the_window():
    hours = {"tue": [{"start": "10:00", "end": "16:00"}]}
    slots = calendar.free_slots(hours, 90, [], MONDAY_8AM, TZ, days=1)
    assert slots == _half_hours(29, 10, 14.5)


def test_days_without_hours_and_weekends_have_no_slots():
    slots = calendar.free_slots(WEEKDAYS_10_16, 50, [], MONDAY_8AM, TZ, days=14)
    assert slots
    assert all(s.astimezone(TZ).weekday() < 5 for s in slots)
    assert calendar.free_slots({}, 50, [], MONDAY_8AM, TZ) == []


def test_a_full_day_offers_nothing():
    tuesday = _at(29, 10).date()
    slots = calendar.free_slots(
        WEEKDAYS_10_16, 50, [], MONDAY_8AM, TZ, days=2, booked_per_day={tuesday: 2}, max_per_day=2
    )
    assert slots and all(s.date() != tuesday for s in slots)


# ---------------------------------------------------------------------------
# Horário de atendimento no perfil
# ---------------------------------------------------------------------------


def test_working_hours_are_saved_and_returned(client, professional):
    hours = {"mon": [{"start": "08:00", "end": "12:00"}, {"start": "13:00", "end": "17:00"}], "sat": []}
    response = client.patch(f"/professionals/{TEST_SLUG}", json={"working_hours": hours})
    assert response.status_code == 200
    assert response.json()["working_hours"] == hours


@pytest.mark.parametrize(
    "hours",
    [
        {"mon": [{"start": "16:00", "end": "10:00"}]},  # fim antes do início
        {"mon": [{"start": "10:00", "end": "13:00"}, {"start": "12:00", "end": "16:00"}]},  # sobreposição
        {"mon": [{"start": "25:00", "end": "26:00"}]},  # hora inválida
        {"segunda": [{"start": "10:00", "end": "16:00"}]},  # dia desconhecido
    ],
)
def test_invalid_working_hours_are_refused(client, professional, hours):
    assert client.patch(f"/professionals/{TEST_SLUG}", json={"working_hours": hours}).status_code == 422


# ---------------------------------------------------------------------------
# Conexão com o Google
# ---------------------------------------------------------------------------


def test_connect_stores_the_access_encrypted_and_disconnect_revokes(client, db, professional, google):
    status = client.get(f"/calendar/{TEST_SLUG}").json()
    assert status["configured"] and not status["connected"] and not status["ready"]

    status = client.post(f"/calendar/{TEST_SLUG}/connect", json={"code": "codigo"}).json()
    assert status["connected"] and status["ready"]
    assert status["google_email"] == "agenda@gmail.com"

    raw = db.execute(
        text("SELECT refresh_token FROM calendar_connections WHERE professional_id = :id"), {"id": professional.id}
    ).scalar()
    assert raw and raw != "refresh-de-teste"

    status = client.delete(f"/calendar/{TEST_SLUG}/connect").json()
    assert not status["connected"]
    assert google.revoked == ["refresh-de-teste"]
    assert db.query(models.CalendarConnection).filter_by(professional_id=professional.id).count() == 0


def test_connect_refuses_when_the_calendar_permission_was_unchecked(client, professional, google):
    google.tokens["scope"] = "openid email"
    response = client.post(f"/calendar/{TEST_SLUG}/connect", json={"code": "codigo"})
    assert response.status_code == 400
    assert "permissão da agenda" in response.json()["detail"]


def test_connect_refuses_without_long_lived_access(client, professional, google):
    del google.tokens["refresh_token"]
    response = client.post(f"/calendar/{TEST_SLUG}/connect", json={"code": "codigo"})
    assert response.status_code == 400
    assert "myaccount.google.com/permissions" in response.json()["detail"]


def test_connect_is_off_without_the_client_secret(client, professional, google, monkeypatch):
    monkeypatch.setattr(settings, "google_client_secret", "")
    assert client.get(f"/calendar/{TEST_SLUG}").json()["configured"] is False
    assert client.post(f"/calendar/{TEST_SLUG}/connect", json={"code": "codigo"}).status_code == 400


def test_free_slots_preview_needs_a_connection(client, professional, google):
    assert client.get(f"/calendar/{TEST_SLUG}/free-slots").status_code == 409
    client.post(f"/calendar/{TEST_SLUG}/connect", json={"code": "codigo"})
    slots = client.get(f"/calendar/{TEST_SLUG}/free-slots").json()
    assert slots and " às " in slots[0]["label"]


# ---------------------------------------------------------------------------
# A SelenIA na conversa
# ---------------------------------------------------------------------------


def test_tool_text_lists_slots_and_admits_failure(db, professional, google, monkeypatch):
    calendar.connect(db, professional, "codigo")
    text_ok = calendar.describe_for_assistant(professional, MONDAY_8AM)
    assert "Agora é segunda, 28/09/2026" in text_ok
    assert "- terça, 29/09 (2026-09-29): 10:00, 10:30, 11:00" in text_ok

    def broken(connection, start, end):
        raise calendar.CalendarError("fora do ar")

    monkeypatch.setattr(calendar, "busy_intervals", broken)
    text_fail = calendar.describe_for_assistant(professional, MONDAY_8AM)
    assert "Não foi possível consultar a agenda" in text_fail
    assert " às " not in text_fail.split("\n", 1)[1]


def test_reply_gets_the_agenda_tool_only_when_ready(client, db, professional, google, monkeypatch):
    calls = []

    def fake_reply(system_prompt, history, tools=None, run_tool=None):
        calls.append((system_prompt, tools, run_tool("consultar_horarios_livres", {})))
        return "resposta do bot"

    monkeypatch.setattr(llm, "generate_reply", fake_reply)

    client.post("/chat/simulate", json={"professional_slug": TEST_SLUG, "message": "vocês atendem sábado?"})
    prompt, tools, _ = calls[-1]
    assert tools == [llm.ASK_PROFESSIONAL_TOOL]
    assert "segunda: 10:00 às 16:00" in prompt and "não tem acesso à agenda" in prompt

    calendar.connect(db, professional, "codigo")
    client.post("/chat/simulate", json={"professional_slug": TEST_SLUG, "message": "tem horário semana que vem?"})
    prompt, tools, tool_text = calls[-1]
    assert tools == [llm.ASK_PROFESSIONAL_TOOL, llm.AGENDA_TOOL]
    assert "consultar_horarios_livres" in prompt
    assert "Horários livres" in tool_text


def test_prompt_without_hours_says_the_professional_confirms():
    prof = SimpleNamespace(name="Ana", working_hours=None, session_minutes=None, calendar_connection=None)
    assert llm._format_agenda(prof) == llm.AGENDA_NONE.format(name="Ana")


def test_list_events_reads_timed_all_day_and_skips_cancelled(monkeypatch):
    items = [
        {"id": "a", "summary": "Sessão", "start": {"dateTime": "2026-09-29T10:00:00-03:00"},
         "end": {"dateTime": "2026-09-29T10:50:00-03:00"}},
        {"id": "b", "start": {"date": "2026-09-30"}, "end": {"date": "2026-10-01"}, "transparency": "transparent"},
        {"id": "c", "status": "cancelled", "start": {"date": "2026-09-30"}, "end": {"date": "2026-10-01"}},
    ]
    urls = []
    monkeypatch.setattr(calendar, "_events_call", lambda c, method, url, body=None: urls.append(url) or {"items": items})
    events = calendar.list_events(None, _at(28, 0), _at(28, 0) + timedelta(days=7))
    assert [e["id"] for e in events] == ["a", "b"]
    assert events[0]["title"] == "Sessão" and events[0]["starts_at"] == _at(29, 10)
    assert events[1]["all_day"] and events[1]["title"] == "(sem título)" and not events[1]["busy"]
    assert "singleEvents=true" in urls[0] and "%2B" not in urls[0]  # UTC-3 vira "-03:00", sem "+"
