"""Tela de Conversas: lista, "Aguardando você", aviso por e-mail e janela de 24h."""

from datetime import timedelta

import pytest

from app import models
from app.models import Channel, ConversationState, MessageRole
from app.services import conversations, llm, notifications

TEST_SLUG = "test-pytest-inbox"


@pytest.fixture
def professional(db, monkeypatch):
    monkeypatch.setattr(llm, "generate_reply", lambda system_prompt, history: "resposta do bot")
    monkeypatch.setattr(notifications.settings, "smtp_host", "smtp.teste.local")
    _cleanup(db)
    prof = models.Professional(slug=TEST_SLUG, name="Marília Rossetto", alert_email="alertas@teste.local")
    db.add(prof)
    db.commit()
    yield prof
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
    response = client.get("/conversations", params={"professional_slug": TEST_SLUG})
    assert response.status_code == 200
    return response.json()


def test_list_puts_what_needs_the_professional_first(client, professional):
    calm = _send(client, "quanto custa a sessão?")
    asked = _send(client, "oi")
    _send(client, "quero falar com a Marília", asked["session_id"])
    emergency = _send(client, "to pensando em me matar")
    newest = _send(client, "vocês atendem online?")

    ids = [c["id"] for c in _list(client)]
    assert ids[:2] == [emergency["conversation_id"], asked["conversation_id"]]
    # Sem pendência, a mais recente vem antes.
    assert ids.index(newest["conversation_id"]) < ids.index(calm["conversation_id"])

    [summary] = [c for c in _list(client) if c["id"] == newest["conversation_id"]]
    assert summary["channel"] == Channel.SIMULATOR
    assert summary["contact_name"] == "Conversa de teste"
    assert summary["last_message"]["preview"] == "resposta do bot"
    assert summary["last_message"]["sent_by"] == "bot"
    assert summary["reply_window_open"] is True


def test_request_waits_for_reply_and_emails_once(client, professional, no_real_email):
    first = _send(client, "oi")
    _send(client, "quero falar com a Marília", first["session_id"])
    _send(client, "oi? quero falar com a Marília", first["session_id"])

    [email] = no_real_email
    assert email["Subject"] == notifications.HUMAN_REQUEST_SUBJECT
    assert email["To"] == "alertas@teste.local"
    assert "quero falar" not in email.get_content()

    conversation = client.get(f"/conversations/{first['conversation_id']}").json()
    assert conversation["awaiting_reply_since"]

    replied = client.post(f"/conversations/{first['conversation_id']}/messages", json={"content": "Oi, sou eu!"})
    assert replied.json()["awaiting_reply_since"] is None
    assert replied.json()["state"] == ConversationState.HUMAN


def test_bot_refusal_sends_only_the_alert_email(client, professional, no_real_email):
    first = _send(client, "oi")
    _send(client, "não quero falar com robô", first["session_id"])
    assert [e["Subject"] for e in no_real_email] == [notifications._LEVEL_TEXT["bot_refused"][0]]
    assert client.get(f"/conversations/{first['conversation_id']}").json()["awaiting_reply_since"]


def test_release_clears_waiting(client, professional):
    first = _send(client, "oi")
    _send(client, "quero falar com a Marília", first["session_id"])
    released = client.post(f"/conversations/{first['conversation_id']}/release").json()
    assert released["awaiting_reply_since"] is None
    assert released["state"] == ConversationState.ACTIVE


def test_reply_blocked_after_24h(db, client, professional):
    first = _send(client, "oi")
    conversation = db.get(models.Conversation, first["conversation_id"])
    conversation.last_contact_message_at = models._now() - timedelta(hours=24, minutes=1)
    db.commit()

    opened = client.get(f"/conversations/{first['conversation_id']}").json()
    assert opened["reply_window_open"] is False
    response = client.post(f"/conversations/{first['conversation_id']}/messages", json={"content": "Oi!"})
    assert response.status_code == 409

    # A pessoa escreveu de novo: a janela abre outra vez.
    _send(client, "oi de novo", first["session_id"])
    response = client.post(f"/conversations/{first['conversation_id']}/messages", json={"content": "Oi!"})
    assert response.status_code == 200


def test_whatsapp_number_is_masked_in_the_list_and_full_when_opened(db, client, professional):
    contact = conversations.get_or_create_contact(
        db, professional, Channel.WHATSAPP, "5521955554444", display_name=None
    )
    conversation, _ = conversations.get_or_create_conversation(db, contact)
    conversations.record_message(db, conversation, MessageRole.USER, "oi")

    [summary] = [c for c in _list(client) if c["id"] == conversation.id]
    assert summary["contact_phone"] == "+55 21 •••••-4444"
    assert summary["contact_name"] == "+55 21 •••••-4444"
    opened = client.get(f"/conversations/{conversation.id}").json()
    assert opened["contact_phone"] == "+55 21 95555-4444"
