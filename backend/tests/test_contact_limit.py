"""Limite de mensagens por hora, por pessoa.

Acima do limite o modelo não é chamado (nem a resposta, nem a camada 2
da triagem); a pessoa recebe um aviso fixo uma vez e a conversa fica
marcada para a profissional. A camada 1 da triagem continua, e outra
pessoa escrevendo ao mesmo tempo não é afetada.
"""

from datetime import timedelta

import pytest

from app import models
from app.config import settings
from app.models import AlertLevel, ConversationState
from app.services import llm, pipeline, triage

TEST_SLUG = "test-pytest-limite"
LIMIT = 3


@pytest.fixture
def calls(db, monkeypatch):
    monkeypatch.setattr(settings, "contact_messages_per_hour", LIMIT)
    calls = {"reply": 0, "triage": 0}

    def fake_reply(system_prompt, history, **_):
        calls["reply"] += 1
        return "resposta do bot"

    def fake_triage(history, audience=None):
        calls["triage"] += 1
        return llm.RiskClassification(nivel="normal", justificativa="teste")

    monkeypatch.setattr(llm, "generate_reply", fake_reply)
    monkeypatch.setattr(llm, "classify_risk", fake_triage)
    _cleanup(db)
    db.add(models.Professional(slug=TEST_SLUG, name="Marília Rossetto"))
    db.commit()
    yield calls
    _cleanup(db)


def _cleanup(db):
    existing = db.query(models.Professional).filter_by(slug=TEST_SLUG).first()
    if existing:
        db.delete(existing)
        db.commit()


def _send(client, text, session_id=None):
    payload = {"professional_slug": TEST_SLUG, "message": text, "session_id": session_id}
    return client.post("/chat/simulate", json=payload).json()


def _fill(client, session_id=None):
    """Manda mensagens até o limite; devolve o `session_id`."""
    first = _send(client, "oi", session_id)
    for _ in range(LIMIT - 1):
        _send(client, "oi", first["session_id"])
    return first["session_id"]


def test_up_to_the_limit_the_bot_answers(client, calls):
    session = _fill(client)
    assert calls == {"reply": LIMIT, "triage": LIMIT}
    assert _send(client, "oi", session)["reply"] == pipeline.RATE_LIMIT_TEMPLATE.format(name="Marília Rossetto")


def test_above_the_limit_one_notice_then_silence_without_the_model(db, client, calls):
    session = _fill(client)
    notice = _send(client, "mais uma", session)
    assert "SAMU (192)" in notice["reply"]
    after = _send(client, "e mais outra", session)
    assert after["reply"] is None
    # Nenhuma chamada paga depois do limite.
    assert calls == {"reply": LIMIT, "triage": LIMIT}

    conversation = db.get(models.Conversation, notice["conversation_id"])
    db.refresh(conversation)
    assert conversation.needs_attention
    assert conversation.state == ConversationState.ACTIVE
    # Todas as mensagens ficam gravadas para a profissional.
    contents = [m.content for m in conversation.messages]
    assert "e mais outra" in contents and contents.count(notice["reply"]) == 1


def test_rules_still_catch_risk_above_the_limit(db, client, calls):
    session = _fill(client)
    _send(client, "mais uma", session)
    risk = _send(client, "to pensando em me matar", session)
    assert risk["reply"] == triage.EMERGENCY_MESSAGE
    assert risk["triage_level"] == AlertLevel.EMERGENCY and risk["alert_created"]
    assert calls["triage"] == LIMIT


def test_another_person_is_not_affected(client, calls):
    session = _fill(client)
    _send(client, "mais uma", session)
    other = _send(client, "quanto custa?")
    assert other["reply"] == "resposta do bot"


def test_the_bot_comes_back_when_the_hour_passes(db, client, calls):
    session = _fill(client)
    over = _send(client, "mais uma", session)
    conversation = db.get(models.Conversation, over["conversation_id"])
    for message in conversation.messages:
        message.created_at -= timedelta(hours=1, minutes=1)
    db.commit()
    assert _send(client, "voltei", session)["reply"] == "resposta do bot"
