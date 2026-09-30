from datetime import timedelta

import pytest

from app import models
from app.models import AlertEventType, AlertLevel, ConversationState, SentBy
from app.services import handoff, llm

TEST_SLUG = "test-pytest-handoff"


@pytest.fixture
def professional(db, monkeypatch):
    monkeypatch.setattr(llm, "generate_reply", lambda system_prompt, history: "resposta do bot")
    _cleanup(db)
    db.add(models.Professional(slug=TEST_SLUG, name="Marília Rossetto"))
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
    response = client.post("/chat/simulate", json=payload)
    assert response.status_code == 200
    return response.json()


PROF = models.Professional(slug="x", name="Marília Rossetto")


@pytest.mark.parametrize(
    "text",
    [
        "quero falar com uma pessoa",
        "nao quero falar com robo",
        "Não quero conversar com IA, quero falar com a Marília",
        "prefiro ser atendida por uma pessoa de verdade",
        "chega de robô",
        # Erros de digitação reais do teste no simulador (25/09).
        "eu nao quero flaar co um robo eu quero falar com o pedro msm",
        "n quero fala c bot",
        # Caso real do teste pelo WhatsApp (30/09): pede a pessoa e
        # recusa o bot na mesma frase, sem o verbo "não quero".
        "Eu quero falar com ele não um robô ou ia",
        "quero a Marília, não uma IA",
    ],
)
def test_detects_bot_refusal(text):
    assert handoff.classify_request(text, PROF) == handoff.HumanRequest.REFUSES_BOT


@pytest.mark.parametrize(
    "text",
    [
        "Tem como conversar com a psicóloga?",
        "posso falar direto com ela?",
        "queria falar com a Marília",
        "me passa pra ela por favor",
    ],
)
def test_detects_request_for_professional(text):
    assert handoff.classify_request(text, PROF) == handoff.HumanRequest.WANTS_PROFESSIONAL


@pytest.mark.parametrize(
    "text",
    [
        "você é humana?",
        "quanto custa a sessão?",
        "preciso falar sobre meu término",
        "falei com ela ontem",
        "não quero ir hoje, ia chover",
        "não quero que meu namorado pense que sou um robô",
        "você não é um robô, né?",
        "me sinto como se não fosse uma pessoa, mas um robô",
    ],
)
def test_ignores_other_messages(text):
    assert handoff.classify_request(text, PROF) is None


@pytest.mark.parametrize("in_session", [False, True])
def test_bot_refusal_stops_bot_and_alerts_without_emergency_text(db, client, professional, in_session):
    if in_session:
        client.put(f"/professionals/{TEST_SLUG}/in-session", json={"minutes": 50})
    first = _send(client, "oi")

    refused = _send(client, "não quero falar com robô", first["session_id"])
    expected = handoff.BOT_REFUSED_IN_SESSION_MESSAGE if in_session else handoff.BOT_REFUSED_MESSAGE
    assert refused["reply"] == expected.format(name="Marília Rossetto")
    assert "192" not in refused["reply"] and "188" not in refused["reply"]
    assert refused["state"] == ConversationState.HUMAN
    assert _send(client, "alô?", first["session_id"])["reply"] is None

    db.expire_all()
    conversation = db.get(models.Conversation, first["conversation_id"])
    [alert] = conversation.alerts
    assert alert.level == AlertLevel.BOT_REFUSED
    assert alert.trigger == "handoff:recusa_bot"
    assert conversation.awaiting_reply_since is not None


def test_human_request_hands_over_and_silences_bot(client, professional):
    first = _send(client, "oi")
    assert first["state"] == ConversationState.ACTIVE

    asked = _send(client, "quero falar com a Marília", first["session_id"])
    assert asked["reply"] == handoff.HANDOFF_MESSAGE.format(name="Marília Rossetto")
    assert asked["state"] == ConversationState.HUMAN

    after = _send(client, "oi? alguém?", first["session_id"])
    assert after["reply"] is None


def test_in_session_offers_help_and_keeps_bot(client, professional):
    assert client.put(f"/professionals/{TEST_SLUG}/in-session", json={"minutes": 50}).json()["in_session"]

    first = _send(client, "oi")
    asked = _send(client, "posso falar com ela?", first["session_id"])
    assert asked["reply"] == handoff.IN_SESSION_MESSAGE.format(name="Marília Rossetto")
    assert asked["state"] == ConversationState.ACTIVE
    conversation = client.get(f"/conversations/{first['conversation_id']}").json()
    assert conversation["awaiting_reply_since"]

    # O bot continua ajudando enquanto ela está em atendimento.
    assert _send(client, "quanto custa?", first["session_id"])["reply"] == "resposta do bot"


def test_in_session_turns_itself_off(db, client, professional):
    client.put(f"/professionals/{TEST_SLUG}/in-session", json={"minutes": 50})
    prof = db.query(models.Professional).filter_by(slug=TEST_SLUG).one()
    prof.in_session_until = models._now() - timedelta(minutes=1)
    db.commit()
    assert client.get(f"/professionals/{TEST_SLUG}").json()["in_session"] is False


def test_in_session_until_turned_off(client, professional):
    on = client.put(f"/professionals/{TEST_SLUG}/in-session", json={"minutes": None}).json()
    assert on["in_session"] and on["in_session_until"] is None
    off = client.delete(f"/professionals/{TEST_SLUG}/in-session").json()
    assert off["in_session"] is False


def test_professional_reply_takes_over_and_release_gives_back(client, professional):
    first = _send(client, "oi")
    conversation_id = first["conversation_id"]

    replied = client.post(f"/conversations/{conversation_id}/messages", json={"content": "Oi, aqui é a Marília!"})
    body = replied.json()
    assert body["state"] == ConversationState.HUMAN
    assert body["messages"][-1]["sent_by"] == SentBy.PROFESSIONAL
    assert _send(client, "oi Marília", first["session_id"])["reply"] is None

    released = client.post(f"/conversations/{conversation_id}/release").json()
    assert released["state"] == ConversationState.ACTIVE
    assert _send(client, "e o valor?", first["session_id"])["reply"] == "resposta do bot"


def test_release_after_emergency_is_audited(db, client, professional):
    first = _send(client, "to pensando em me matar")
    assert first["state"] == ConversationState.EMERGENCY_HOLD

    # Assumir não tira a conversa da espera de emergência.
    taken = client.post(f"/conversations/{first['conversation_id']}/take-over").json()
    assert taken["state"] == ConversationState.EMERGENCY_HOLD

    client.post(f"/conversations/{first['conversation_id']}/release")
    db.expire_all()
    conversation = db.get(models.Conversation, first["conversation_id"])
    assert conversation.state == ConversationState.ACTIVE
    [alert] = conversation.alerts
    assert AlertEventType.BOT_RELEASED in [e.event_type for e in alert.events]
