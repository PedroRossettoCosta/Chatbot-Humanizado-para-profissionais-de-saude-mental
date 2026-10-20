"""Webhook do WhatsApp: desafio, assinatura, mensagens, espera e envio."""

import asyncio
import hashlib
import hmac
import json

import pytest

from app import models
from app.config import settings
from app.models import AlertLevel, Channel, ConversationState, MessageRole, SentBy
from app.services import handoff, llm, triage, whatsapp, whatsapp_inbox

TEST_SLUG = "test-pytest-webhook"
PHONE_ID = "999000111"
SENDER = "5521955554444"
SECRET = "segredo-de-teste"


@pytest.fixture
def professional(db, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", SECRET)
    monkeypatch.setattr(settings, "whatsapp_verify_token", "senha-do-desafio")
    monkeypatch.setattr(settings, "reply_debounce_seconds", 0)
    replies = []

    def fake_reply(system_prompt, history, **_):
        replies.append(history)
        return "resposta do bot"

    monkeypatch.setattr(llm, "generate_reply", fake_reply)
    _cleanup(db)
    db.add(models.Professional(slug=TEST_SLUG, name="Marília Rossetto", whatsapp_phone_number_id=PHONE_ID))
    db.commit()
    yield replies
    _cleanup(db)


def _cleanup(db):
    existing = db.query(models.Professional).filter_by(slug=TEST_SLUG).first()
    if existing:
        db.delete(existing)
        db.commit()


_counter = iter(range(10_000))


def _payload(text=None, kind="text", message_id=None, sender=SENDER, phone_id=PHONE_ID, media=None):
    message = {"from": sender, "id": message_id or f"wamid.teste.{next(_counter)}", "type": kind}
    if kind == "text":
        message["text"] = {"body": text}
    if media:
        message[kind] = media
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "metadata": {"phone_number_id": phone_id},
                            "contacts": [{"wa_id": sender, "profile": {"name": "Ana Teste"}}],
                            "messages": [message],
                        },
                    }
                ]
            }
        ],
    }


def _post(client, payload, secret=SECRET):
    body = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return client.post(
        "/webhook/whatsapp",
        content=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": signature},
    )


def _sent_texts(calls):
    return [body["text"]["body"] for _, body in calls if body.get("type") == "text"]


def _conversation(db):
    db.expire_all()
    professional = db.query(models.Professional).filter_by(slug=TEST_SLUG).one()
    [conversation] = professional.conversations
    return conversation


def test_meta_challenge(client, professional):
    ok = client.get(
        "/webhook/whatsapp",
        params={"hub.mode": "subscribe", "hub.verify_token": "senha-do-desafio", "hub.challenge": "12345"},
    )
    assert ok.status_code == 200 and ok.text == "12345"
    wrong = client.get(
        "/webhook/whatsapp", params={"hub.mode": "subscribe", "hub.verify_token": "outra", "hub.challenge": "1"}
    )
    assert wrong.status_code == 403


def test_bad_signature_is_refused_and_nothing_is_recorded(db, client, professional, no_real_whatsapp):
    assert _post(client, _payload("oi"), secret="segredo-errado").status_code == 401
    assert client.post("/webhook/whatsapp", json=_payload("oi")).status_code == 401
    assert db.query(models.Professional).filter_by(slug=TEST_SLUG).one().conversations == []
    assert no_real_whatsapp == []


def test_no_secret_configured_refuses_everything(client, professional, monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_app_secret", "")
    assert _post(client, _payload("oi"), secret="").status_code == 401


def test_text_message_gets_disclaimer_and_reply(db, client, professional, no_real_whatsapp):
    assert _post(client, _payload("quanto custa a sessão?")).status_code == 200

    sent = _sent_texts(no_real_whatsapp)
    assert sent[0].startswith("Oi! Eu sou a SelenIA")
    assert sent[1] == "resposta do bot"
    assert all(to_phone == PHONE_ID for to_phone, _ in no_real_whatsapp)
    assert any(body.get("typing_indicator") for _, body in no_real_whatsapp)

    conversation = _conversation(db)
    assert conversation.contact.channel == Channel.WHATSAPP
    assert conversation.contact.display_name == "Ana Teste"
    assert conversation.last_contact_message_at is not None


def test_sent_messages_keep_the_meta_id(db, client, professional, no_real_whatsapp):
    _post(client, _payload("quanto custa a sessão?"))
    outgoing = [m for m in _conversation(db).messages if m.role == MessageRole.ASSISTANT]
    assert len(outgoing) == 2
    assert all(m.external_id and m.external_id.startswith("wamid.teste.saida") for m in outgoing)
    assert not any(m.delivery_failed for m in outgoing)


def test_refused_by_meta_shows_as_not_delivered(db, client, professional, monkeypatch):
    def refuse(phone_number_id, to, text):
        raise whatsapp.SendError("131042")

    monkeypatch.setattr(whatsapp, "send_text", refuse)
    _post(client, _payload("quanto custa a sessão?"))
    conversation = _conversation(db)
    outgoing = [m for m in conversation.messages if m.role == MessageRole.ASSISTANT]
    assert [m.delivery_failed for m in outgoing] == [True, True]

    detail = client.get(f"/conversations/{conversation.id}").json()
    assert [m["delivery_failed"] for m in detail["messages"]] == [True, False, True]


def test_meta_resend_is_processed_once(db, client, professional, no_real_whatsapp):
    payload = _payload("oi", message_id="wamid.repetido")
    _post(client, payload)
    _post(client, payload)
    conversation = _conversation(db)
    assert [m.role for m in conversation.messages].count(MessageRole.USER) == 1


def test_number_without_professional_is_ignored(client, professional, no_real_whatsapp):
    assert _post(client, _payload("oi", phone_id="000")).status_code == 200
    assert no_real_whatsapp == []


def test_emergency_goes_out_right_away_without_bot_reply(db, client, professional, no_real_whatsapp):
    _post(client, _payload("to pensando em me matar"))
    sent = _sent_texts(no_real_whatsapp)
    assert sent[-1] == triage.EMERGENCY_MESSAGE
    assert "resposta do bot" not in sent
    conversation = _conversation(db)
    assert conversation.state == ConversationState.EMERGENCY_HOLD
    assert [a.level for a in conversation.alerts] == [AlertLevel.EMERGENCY]


def test_audio_is_recorded_and_answered_with_fixed_text(db, client, professional, no_real_whatsapp):
    _post(client, _payload(kind="audio"))
    sent = _sent_texts(no_real_whatsapp)
    assert sent[-1] == whatsapp_inbox.UNSUPPORTED_MESSAGE
    conversation = _conversation(db)
    assert "[Áudio]" in [m.content for m in conversation.messages]
    assert conversation.alerts == []


def test_status_updates_are_ignored(client, professional, no_real_whatsapp):
    payload = _payload("oi")
    value = payload["entry"][0]["changes"][0]["value"]
    del value["messages"]
    value["statuses"] = [{"id": "wamid.x", "status": "read"}]
    assert _post(client, payload).status_code == 200
    assert no_real_whatsapp == []


def test_broken_messages_get_one_reply(db, professional, no_real_whatsapp):
    """Com a espera, as mensagens quebradas viram uma resposta só."""

    def inbound(text, n):
        return whatsapp.Inbound(PHONE_ID, SENDER, f"wamid.junta.{n}", "text", text, "Ana")

    # Nenhuma das partes, sozinha, é pedido para falar com a profissional.
    assert handoff.classify_request("oi, eu quero falar", models.Professional(name="Marília")) is None
    assert handoff.classify_request("com a Marília", models.Professional(name="Marília")) is None
    first = whatsapp_inbox.receive_now(inbound("oi, eu quero falar", 1))
    whatsapp_inbox.receive_now(inbound("com a Marília", 2))
    outcome = whatsapp_inbox.reply_now((PHONE_ID, SENDER), first.conversation_id)

    # Juntas, as duas partes são um pedido para falar com a profissional.
    assert outcome.notify_request is True
    conversation = _conversation(db)
    assert conversation.awaiting_reply_since is not None
    replies = [m for m in conversation.messages if m.sent_by in (SentBy.BOT,)]
    assert replies == []
    assert _sent_texts(no_real_whatsapp).count("resposta do bot") == 0


def test_wait_restarts_and_replies_once(db, professional, no_real_whatsapp, monkeypatch):
    """Duas mensagens dentro da espera: uma resposta só, com as duas no histórico."""
    monkeypatch.setattr(settings, "reply_debounce_seconds", 0.3)

    def inbound(text, n):
        return whatsapp.Inbound(PHONE_ID, SENDER, f"wamid.espera.{n}", "text", text, "Ana")

    async def scenario():
        await whatsapp_inbox.handle([inbound("oi", 1)])
        await asyncio.sleep(0.1)
        await whatsapp_inbox.handle([inbound("quanto custa?", 2)])
        # Ainda dentro da espera recomeçada: nada respondido.
        await asyncio.sleep(0.15)
        assert "resposta do bot" not in _sent_texts(no_real_whatsapp)
        [waiting] = whatsapp_inbox._pending.values()
        await waiting  # termina a espera e a resposta

    asyncio.run(scenario())
    assert _sent_texts(no_real_whatsapp).count("resposta do bot") == 1
    [history] = professional
    assert [m["content"] for m in history if m["role"] == "user"][-2:] == ["oi", "quanto custa?"]


def test_panel_reply_goes_out_through_whatsapp(db, client, professional, no_real_whatsapp):
    _post(client, _payload("oi"))
    conversation = _conversation(db)
    response = client.post(f"/conversations/{conversation.id}/messages", json={"content": "Oi, aqui é a Marília"})
    assert response.status_code == 200
    assert _sent_texts(no_real_whatsapp)[-1] == "Oi, aqui é a Marília"
    db.expire_all()
    [mine] = [m for m in _conversation(db).messages if m.sent_by == SentBy.PROFESSIONAL]
    assert mine.external_id.startswith("wamid.teste.saida")


def test_panel_reply_not_recorded_when_meta_refuses(db, client, professional, monkeypatch):
    _post(client, _payload("oi"))
    conversation = _conversation(db)

    def refuse(phone_number_id, body):
        raise whatsapp.SendError("HTTP 400")

    monkeypatch.setattr(whatsapp, "_post", refuse)
    response = client.post(f"/conversations/{conversation.id}/messages", json={"content": "Oi!"})
    assert response.status_code == 502
    assert [m for m in _conversation(db).messages if m.sent_by == SentBy.PROFESSIONAL] == []


def test_tunnel_only_lets_the_webhook_through(client, professional, monkeypatch):
    monkeypatch.setattr(settings, "public_webhook_host", "algo.ngrok-free.dev")
    public = {"Host": "algo.ngrok-free.dev"}
    assert client.get("/health", headers=public).status_code == 404
    assert client.get("/conversations", params={"professional_slug": "x"}, headers=public).status_code == 404
    challenge = client.get(
        "/webhook/whatsapp",
        params={"hub.mode": "subscribe", "hub.verify_token": "senha-do-desafio", "hub.challenge": "7"},
        headers=public,
    )
    assert challenge.status_code == 200
    # Pela máquina (sem o endereço público), a API continua normal.
    assert client.get("/health").status_code == 200


def _media_message(db, client, kind, media):
    _post(client, _payload(kind=kind, media=media))
    conversation = _conversation(db)
    [message] = [m for m in conversation.messages if m.media_id]
    return conversation, message


def test_photo_keeps_only_the_meta_reference(db, client, professional, no_real_whatsapp):
    conversation, message = _media_message(
        db, client, "image", {"id": "midia-1", "mime_type": "image/jpeg", "sha256": "x"}
    )
    assert (message.media_type, message.media_id, message.media_mime) == ("image", "midia-1", "image/jpeg")
    assert message.content == "[Imagem]"
    # A SelenIA continua sem ler: aviso fixo de que só lê texto.
    assert _sent_texts(no_real_whatsapp)[-1] == whatsapp_inbox.UNSUPPORTED_MESSAGE
    body = client.get(f"/conversations/{conversation.id}").json()
    shown = [m for m in body["messages"] if m["media_type"]]
    assert shown[0]["id"] == message.id and shown[0]["media_mime"] == "image/jpeg"


def test_panel_fetches_the_file_from_meta_on_demand(db, client, professional, monkeypatch):
    conversation, message = _media_message(db, client, "audio", {"id": "midia-2", "mime_type": "audio/ogg; codecs=opus"})
    asked = []

    def fake_graph(method, path, body=None, params=None):
        asked.append(path)
        return {"url": "https://lookaside.example/arquivo", "mime_type": "audio/ogg"}

    monkeypatch.setattr(whatsapp, "_graph", fake_graph)
    monkeypatch.setattr(whatsapp, "_download", lambda url: b"OGG-bytes")
    response = client.get(f"/conversations/{conversation.id}/messages/{message.id}/media")
    assert response.status_code == 200
    assert response.content == b"OGG-bytes"
    assert response.headers["content-type"].startswith("audio/ogg")
    assert response.headers["cache-control"] == "private, no-store"
    assert asked == ["midia-2"]


def test_unknown_document_type_is_a_download(db, client, professional, monkeypatch):
    conversation, message = _media_message(
        db, client, "document", {"id": "midia-3", "mime_type": "text/html", "filename": "exame página.html"}
    )
    assert message.media_filename == "exame página.html"
    monkeypatch.setattr(whatsapp, "_graph", lambda *a, **k: {"url": "https://x", "mime_type": "text/html"})
    monkeypatch.setattr(whatsapp, "_download", lambda url: b"<script>")
    response = client.get(f"/conversations/{conversation.id}/messages/{message.id}/media")
    assert response.headers["content-type"] == "application/octet-stream"
    assert response.headers["content-disposition"].startswith("attachment;")
    assert "exame%20p%C3%A1gina.html" in response.headers["content-disposition"]


def test_expired_file_is_explained(db, client, professional, monkeypatch):
    conversation, message = _media_message(db, client, "image", {"id": "midia-4", "mime_type": "image/png"})

    def gone(method, path, body=None, params=None):
        raise whatsapp.MetaError("não existe", 100)

    monkeypatch.setattr(whatsapp, "_graph", gone)
    response = client.get(f"/conversations/{conversation.id}/messages/{message.id}/media")
    assert response.status_code == 410
    assert "30 dias" in response.json()["detail"]


def test_media_of_another_conversation_is_not_found(db, client, professional):
    conversation, message = _media_message(db, client, "image", {"id": "midia-5", "mime_type": "image/png"})
    text_message = next(m for m in conversation.messages if not m.media_id)
    assert client.get(f"/conversations/{conversation.id}/messages/{text_message.id}/media").status_code == 404
