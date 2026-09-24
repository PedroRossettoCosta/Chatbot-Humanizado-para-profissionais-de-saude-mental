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
        llm, "generate_reply", lambda system_prompt, history: llm_calls.append(1) or "resposta do bot"
    )
    db.add(models.Professional(slug=TEST_SLUG, name="Teste Triagem"))
    db.commit()

    first = _send(client, "oi, queria saber como funciona")
    assert first["reply"] == "resposta do bot"

    risk = _send(client, "na verdade to pensando em me matar", first["session_id"])
    assert risk["reply"] == triage.EMERGENCY_MESSAGE
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
    monkeypatch.setattr(llm, "generate_reply", lambda system_prompt, history: "resposta do bot")
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
    monkeypatch.setattr(llm, "generate_reply", lambda system_prompt, history: "acolhimento")
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


def test_niche_distress_goes_to_the_model_without_alert(client, db, monkeypatch):
    _cleanup(db)
    monkeypatch.setattr(llm, "generate_reply", lambda system_prompt, history: "acolhimento")
    db.add(models.Professional(slug=TEST_SLUG, name="Teste Triagem"))
    db.commit()

    body = _send(client, "terminei um relacionamento, perdi meu chão, preciso de ajuda urgente")
    assert body["reply"] == "acolhimento"

    db.expire_all()
    professional = db.query(models.Professional).filter_by(slug=TEST_SLUG).one()
    assert professional.conversations[0].alerts == []

    _cleanup(db)
