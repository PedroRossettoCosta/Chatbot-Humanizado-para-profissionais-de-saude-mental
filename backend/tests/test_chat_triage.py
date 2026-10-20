from datetime import timedelta

from app import models
from app.models import AlertLevel, ConversationState
from app.services import llm, triage

TEST_SLUG = "test-pytest-triagem"


def _cleanup(db):
    professional = db.query(models.Professional).filter_by(slug=TEST_SLUG).first()
    if professional:
        db.delete(professional)
        db.commit()


def _send(client, text, session_id=None):
    payload = {"professional_slug": TEST_SLUG, "message": text}
    if session_id:
        payload["session_id"] = session_id
    response = client.post("/chat/simulate", json=payload)
    assert response.status_code == 200
    return response.json()


def test_risk_message_sends_fixed_text_raises_alert_and_silences_bot(client, db, monkeypatch):
    _cleanup(db)
    llm_calls = []
    monkeypatch.setattr(
        llm, "generate_reply", lambda system_prompt, history, **_: llm_calls.append(1) or "resposta do bot"
    )
    db.add(models.Professional(slug=TEST_SLUG, name="Teste Triagem"))
    db.commit()

    first = _send(client, "oi, queria saber como funciona")
    assert first["reply"] == "resposta do bot"
    assert first["triage_level"] == "normal"
    assert first["alert_created"] is False

    risk = _send(client, "na verdade to pensando em me matar", first["session_id"])
    assert risk["reply"] == triage.EMERGENCY_MESSAGE
    # O simulador mostra o que aconteceu por trás da resposta.
    assert risk["triage_level"] == "emergency"
    assert risk["alert_created"] is True
    assert len(llm_calls) == 1  # a mensagem de risco não passou pelo modelo

    after = _send(client, "quanto custa a sessão?", first["session_id"])
    assert after["reply"] is None  # bot em silêncio depois do alerta
    assert len(llm_calls) == 1

    db.expire_all()
    professional = db.query(models.Professional).filter_by(slug=TEST_SLUG).one()
    conversation = professional.conversations[0]
    assert conversation.state == ConversationState.EMERGENCY_HOLD
    [alert] = conversation.alerts
    assert alert.level == AlertLevel.EMERGENCY
    assert alert.trigger == "camada1:suicidio"
    assert alert.excerpt == "na verdade to pensando em me matar"
    assert alert.message_id is not None

    _cleanup(db)


def test_possible_risk_alerts_professional_and_bot_keeps_talking(client, db, monkeypatch):
    _cleanup(db)
    monkeypatch.setattr(llm, "generate_reply", lambda system_prompt, history, **_: "resposta do bot")
    db.add(models.Professional(slug=TEST_SLUG, name="Teste Triagem"))
    db.commit()

    body = _send(client, "quero morrer")
    assert body["reply"] == "resposta do bot"

    db.expire_all()
    professional = db.query(models.Professional).filter_by(slug=TEST_SLUG).one()
    conversation = professional.conversations[0]
    assert conversation.state == ConversationState.ACTIVE
    assert conversation.needs_attention is True
    [alert] = conversation.alerts
    assert alert.level == AlertLevel.POSSIBLE_RISK

    _cleanup(db)


def test_intense_suffering_marks_attention_without_alert(client, db, monkeypatch):
    _cleanup(db)
    monkeypatch.setattr(llm, "generate_reply", lambda system_prompt, history, **_: "acolhimento")
    monkeypatch.setattr(
        llm,
        "classify_risk",
        lambda history, audience=None: llm.RiskClassification(nivel="sofrimento_intenso", justificativa="teste"),
    )
    db.add(models.Professional(slug=TEST_SLUG, name="Teste Triagem"))
    db.commit()

    body = _send(client, "não consigo parar de chorar desde o término")
    assert body["reply"] == "acolhimento"

    db.expire_all()
    professional = db.query(models.Professional).filter_by(slug=TEST_SLUG).one()
    conversation = professional.conversations[0]
    assert conversation.needs_attention is True
    assert conversation.alerts == []

    _cleanup(db)


def _capture_layer2(monkeypatch):
    seen = []

    def fake(history, audience=None):
        seen.append([m["content"] for m in history])
        return llm.RiskClassification(nivel="normal", justificativa="teste")

    monkeypatch.setattr(llm, "classify_risk", fake)
    return seen


def test_layer2_ignores_messages_older_than_five_minutes(client, db, monkeypatch):
    # Caso real (30/09): uma emergência testada às 17:50 fazia o pedido de
    # horário das 18:15 virar emergência, porque o modelo lia o histórico
    # inteiro, sem horário.
    _cleanup(db)
    monkeypatch.setattr(llm, "generate_reply", lambda system_prompt, history, **_: "resposta do bot")
    seen = _capture_layer2(monkeypatch)
    db.add(models.Professional(slug=TEST_SLUG, name="Teste Triagem"))
    db.commit()

    first = _send(client, "mensagem antiga")
    professional = db.query(models.Professional).filter_by(slug=TEST_SLUG).one()
    for message in professional.conversations[0].messages:
        message.created_at -= timedelta(minutes=30)
    db.commit()

    _send(client, "quero marcar uma sessão amanhã às 15:30", first["session_id"])
    assert seen[-1] == ["quero marcar uma sessão amanhã às 15:30"]

    _cleanup(db)


def test_layer2_reads_the_last_three_messages_together(client, db, monkeypatch):
    _cleanup(db)
    monkeypatch.setattr(llm, "generate_reply", lambda system_prompt, history, **_: "ok")
    seen = _capture_layer2(monkeypatch)
    db.add(models.Professional(slug=TEST_SLUG, name="Teste Triagem"))
    db.commit()

    first = _send(client, "um")
    _send(client, "dois", first["session_id"])
    _send(client, "três", first["session_id"])
    # Três últimas da conversa, com a resposta do consultório no meio.
    assert seen[-1] == ["dois", "ok", "três"]

    _cleanup(db)


def _emergency_then_release(client, db, monkeypatch, minutes_ago):
    """Emergência, a profissional libera, e a pessoa volta a escrever."""
    from app.services import handoff

    _cleanup(db)
    histories = []
    monkeypatch.setattr(
        llm, "generate_reply", lambda system_prompt, history, **_: histories.append(history) or "resposta do bot"
    )
    _capture_layer2(monkeypatch)
    db.add(models.Professional(slug=TEST_SLUG, name="Teste Triagem"))
    db.commit()

    first = _send(client, "oi, meu nome é Ana")
    _send(client, "to pensando em me matar", first["session_id"])
    professional = db.query(models.Professional).filter_by(slug=TEST_SLUG).one()
    conversation = professional.conversations[0]
    handoff.release(db, conversation)
    for message in conversation.messages:
        message.created_at -= timedelta(minutes=minutes_ago)
    db.commit()

    _send(client, "quero marcar uma sessão", first["session_id"])
    return [m["content"] for m in histories[-1]]


def test_reply_forgets_risk_older_than_five_minutes(client, db, monkeypatch):
    # Caso real (30/09): 36 minutos depois de uma emergência de teste, a
    # resposta a um pedido de horário ainda falava em "querer se matar".
    seen = _emergency_then_release(client, db, monkeypatch, minutes_ago=30)
    assert "to pensando em me matar" not in seen
    assert triage.EMERGENCY_MESSAGE not in seen
    # O resto da conversa continua: a SelenIA não perde a memória toda.
    assert "oi, meu nome é Ana" in seen
    assert seen[-1] == "quero marcar uma sessão"
    _cleanup(db)


def test_reply_keeps_recent_risk_in_context(client, db, monkeypatch):
    seen = _emergency_then_release(client, db, monkeypatch, minutes_ago=0)
    assert "to pensando em me matar" in seen
    _cleanup(db)


def test_niche_distress_goes_to_the_model_without_alert(client, db, monkeypatch):
    _cleanup(db)
    monkeypatch.setattr(llm, "generate_reply", lambda system_prompt, history, **_: "acolhimento")
    db.add(models.Professional(slug=TEST_SLUG, name="Teste Triagem"))
    db.commit()

    body = _send(client, "terminei um relacionamento, perdi meu chão, preciso de ajuda urgente")
    assert body["reply"] == "acolhimento"

    db.expire_all()
    professional = db.query(models.Professional).filter_by(slug=TEST_SLUG).one()
    assert professional.conversations[0].alerts == []

    _cleanup(db)
