"""Tela de Alertas: lista, trilha de auditoria, visto e revisado."""

import pytest

from app import models
from app.config import settings
from app.models import AlertEventType, AlertLevel
from app.services import llm

TEST_SLUG = "test-pytest-alertas"


@pytest.fixture
def professional(db, monkeypatch):
    monkeypatch.setattr(llm, "generate_reply", lambda system_prompt, history, **_: "resposta do bot")
    monkeypatch.setattr(settings, "smtp_host", "smtp.teste.local")
    _cleanup(db)
    db.add(models.Professional(slug=TEST_SLUG, name="Marília Rossetto", alert_email="marilia@exemplo.com"))
    db.commit()
    yield
    _cleanup(db)


def _cleanup(db):
    existing = db.query(models.Professional).filter_by(slug=TEST_SLUG).first()
    if existing:
        db.delete(existing)
        db.commit()


def _send(client, text, session_id=None):
    payload = {"professional_slug": TEST_SLUG, "message": text, "session_id": session_id}
    return client.post("/chat/simulate", json=payload).json()


def _list(client):
    response = client.get("/alerts", params={"professional_slug": TEST_SLUG})
    assert response.status_code == 200
    return response.json()


def test_list_shows_unreviewed_first_with_trigger_and_excerpt(client, professional):
    first = _send(client, "to pensando em me matar")
    refused = _send(client, "não quero falar com robô")

    [newest, oldest] = _list(client)
    assert newest["level"] == AlertLevel.BOT_REFUSED
    assert oldest["level"] == AlertLevel.EMERGENCY
    assert oldest["excerpt"] == "to pensando em me matar"
    assert oldest["trigger_text"] == "Regra fixa: ideação suicida"
    assert oldest["conversation_state"] == "emergency_hold"
    assert oldest["contact_name"] == "Conversa de teste"
    assert {a["status"] for a in _list(client)} == {"new"}

    client.post(f"/alerts/{newest['id']}/review", json={})
    assert [a["id"] for a in _list(client)] == [oldest["id"], newest["id"]]
    assert first["conversation_id"] == oldest["conversation_id"]
    assert refused["conversation_id"] == newest["conversation_id"]


def test_timeline_tells_what_happened_in_order(client, professional):
    _send(client, "to pensando em me matar")
    [alert] = _list(client)

    opened = client.post(f"/alerts/{alert['id']}/view").json()
    kinds = [item["kind"] for item in opened["timeline"]]
    assert kinds == ["created", "action", AlertEventType.NOTIFIED, AlertEventType.VIEWED]
    assert "SAMU 192" in opened["timeline"][1]["detail"]

    # Abrir de novo não repete o "visto": conta a primeira vez.
    again = client.post(f"/alerts/{alert['id']}/view").json()
    assert [i["kind"] for i in again["timeline"]].count(AlertEventType.VIEWED) == 1


def test_review_is_recorded_once_with_note(client, professional):
    _send(client, "to pensando em me matar")
    [alert] = _list(client)

    reviewed = client.post(f"/alerts/{alert['id']}/review", json={"note": "Liguei, está com a família."}).json()
    assert reviewed["status"] == "reviewed"
    assert reviewed["timeline"][-1]["kind"] == AlertEventType.REVIEWED
    assert reviewed["timeline"][-1]["detail"] == "Liguei, está com a família."
    assert reviewed["timeline"][-1]["actor"] == "professional"

    assert client.post(f"/alerts/{alert['id']}/review", json={}).status_code == 409


def test_release_from_alert_screen_enters_the_trail(client, professional):
    _send(client, "to pensando em me matar")
    [alert] = _list(client)
    client.post(f"/conversations/{alert['conversation_id']}/release")

    opened = client.get(f"/alerts/{alert['id']}").json()
    assert opened["conversation_state"] == "active"
    assert opened["timeline"][-1]["kind"] == AlertEventType.BOT_RELEASED


def test_no_route_edits_or_deletes_an_alert(client, professional):
    _send(client, "to pensando em me matar")
    [alert] = _list(client)
    assert client.delete(f"/alerts/{alert['id']}").status_code == 405
    assert client.patch(f"/alerts/{alert['id']}", json={"level": "normal"}).status_code == 405
