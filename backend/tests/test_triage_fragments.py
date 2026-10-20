"""Frase de risco quebrada em várias mensagens seguidas."""

from datetime import timedelta

import pytest

from app import models
from app.models import AlertLevel, ConversationState, MessageRole
from app.services import llm, triage

TEST_SLUG = "test-pytest-fragmentos"


@pytest.mark.parametrize(
    "previous, text, trigger",
    [
        (["eu to pensando"], "em me matar", "camada1:suicidio:juntas"),
        (["oi", "acho que vou"], "me cortar hoje", "camada1:automutilacao:juntas"),
        (["tomei todos os"], "remedios da caixa", "camada1:tentativa_em_andamento:juntas"),
        (["sinceramente queria"], "dormir e nao acordar", "camada1:desejo_de_morrer:juntas"),
    ],
)
def test_rule_matches_the_messages_together(previous, text, trigger):
    resultado = triage.check_rules(text, previous)
    assert resultado.trigger == trigger
    assert resultado.excerpt == " / ".join([*previous, text])


def test_signal_already_alerted_is_not_repeated():
    # "quero morrer" já gerou alerta sozinho; o "oi?" seguinte não repete.
    assert triage.check_rules("oi?", ["quero morrer"]) is None


def test_single_message_signal_keeps_its_own_trigger():
    resultado = triage.check_rules("to pensando em me matar", ["oi"])
    assert resultado.trigger == "camada1:suicidio"
    assert resultado.excerpt == "to pensando em me matar"


def test_most_severe_level_wins_across_messages():
    # Sozinha, "quero morrer" é dúvida; com a anterior, vira tentativa.
    resultado = triage.check_rules("remedios, quero morrer", ["tomei todos os"])
    assert resultado.level == AlertLevel.EMERGENCY


def test_unrelated_messages_stay_normal():
    assert triage.check_rules("quanto custa a sessão?", ["oi", "tudo bem?"]) is None


@pytest.fixture
def professional(db, monkeypatch):
    monkeypatch.setattr(llm, "generate_reply", lambda system_prompt, history, **_: "resposta do bot")
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
    return client.post("/chat/simulate", json=payload).json()


def test_broken_emergency_in_the_chat_triggers_protocol(db, client, professional):
    first = _send(client, "eu to pensando")
    assert first["triage_level"] == "normal"

    second = _send(client, "em me matar", first["session_id"])
    assert second["triage_level"] == AlertLevel.EMERGENCY
    assert second["reply"] == triage.EMERGENCY_MESSAGE
    assert second["state"] == ConversationState.EMERGENCY_HOLD

    db.expire_all()
    [alert] = db.get(models.Conversation, first["conversation_id"]).alerts
    assert alert.trigger == "camada1:suicidio:juntas"
    assert alert.excerpt == "eu to pensando / em me matar"


def test_messages_far_apart_are_not_joined(db, client, professional):
    first = _send(client, "eu to pensando")
    old = (
        db.query(models.Message)
        .filter_by(conversation_id=first["conversation_id"], role=MessageRole.USER)
        .one()
    )
    old.created_at = models._now() - timedelta(minutes=6)
    db.commit()

    second = _send(client, "em me matar", first["session_id"])
    assert second["triage_level"] == "normal"
