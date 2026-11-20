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


def _review_and_release(client, db, conversation_id):
    db.expire_all()
    for alert in db.get(models.Conversation, conversation_id).alerts:
        client.post(f"/alerts/{alert.id}/review", json={})
    assert client.post(f"/conversations/{conversation_id}/release").status_code == 200


def _model_reads_context(monkeypatch):
    """Camada 2 que, como o modelo real, lê as mensagens recentes juntas:
    vê "me matar" em qualquer ponto do histórico e classifica emergência."""

    def classify(history, audience=None):
        risky = any("me matar" in m["content"] for m in history if m["role"] == MessageRole.USER)
        return llm.RiskClassification(nivel="emergencia" if risky else "normal", justificativa="teste")

    monkeypatch.setattr(llm, "classify_risk", classify)


def test_released_emergency_is_not_triggered_again_by_a_greeting(db, client, professional, monkeypatch):
    # Caso real (14/11/2026): a profissional resolveu o alerta e liberou a
    # SelenIA; um "oi" um minuto depois era lido junto com a mensagem de
    # risco e disparava a emergência de novo.
    _model_reads_context(monkeypatch)
    first = _send(client, "to pensando em me matar")
    assert first["state"] == ConversationState.EMERGENCY_HOLD

    _review_and_release(client, db, first["conversation_id"])
    second = _send(client, "oi", first["session_id"])

    assert second["triage_level"] == "normal"
    assert second["state"] == ConversationState.ACTIVE
    assert second["reply"] == "resposta do bot"
    db.expire_all()
    assert len(db.get(models.Conversation, first["conversation_id"]).alerts) == 1


def test_message_during_emergency_hold_repeats_the_text_without_a_new_alert(db, client, professional, monkeypatch):
    # Caso real (19/11/2026): na espera, o modelo via o risco no histórico e
    # cada "pode me ajudar?" abria outro alerta e outro e-mail.
    _model_reads_context(monkeypatch)
    first = _send(client, "to pensando em me matar")
    assert first["state"] == ConversationState.EMERGENCY_HOLD

    again = _send(client, "pode me ajudar?", first["session_id"])

    assert again["reply"] == triage.EMERGENCY_MESSAGE
    assert again["state"] == ConversationState.EMERGENCY_HOLD
    assert again["alert_created"] is False
    db.expire_all()
    assert len(db.get(models.Conversation, first["conversation_id"]).alerts) == 1


def test_new_broken_signal_after_release_still_triggers(db, client, professional):
    first = _send(client, "quero me matar")
    assert first["state"] == ConversationState.EMERGENCY_HOLD
    _review_and_release(client, db, first["conversation_id"])

    assert _send(client, "eu to pensando", first["session_id"])["triage_level"] == "normal"
    again = _send(client, "em me matar", first["session_id"])

    assert again["triage_level"] == AlertLevel.EMERGENCY
    assert again["state"] == ConversationState.EMERGENCY_HOLD
    db.expire_all()
    alerts = db.get(models.Conversation, first["conversation_id"]).alerts
    assert sorted(a.trigger for a in alerts) == ["camada1:suicidio", "camada1:suicidio:juntas"]


def test_release_keeps_the_rest_of_the_context_for_triage(db, client, professional, monkeypatch):
    # Só a mensagem de risco e o texto fixo de emergência saem do contexto
    # depois da liberação; o que a pessoa disse antes continua.
    seen = []

    def classify(history, audience=None):
        seen.append([m["content"] for m in history])
        return llm.RiskClassification(nivel="normal", justificativa="teste")

    monkeypatch.setattr(llm, "classify_risk", classify)
    first = _send(client, "meu nome é Ana")
    risky = _send(client, "to pensando em me matar", first["session_id"])
    assert risky["state"] == ConversationState.EMERGENCY_HOLD

    _review_and_release(client, db, first["conversation_id"])
    _send(client, "oi", first["session_id"])

    context = seen[-1]
    assert "meu nome é Ana" in context
    assert context[-1] == "oi"
    assert "to pensando em me matar" not in context
    assert triage.EMERGENCY_MESSAGE not in context
