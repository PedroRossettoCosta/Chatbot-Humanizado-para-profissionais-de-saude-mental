import pytest

from app import models
from app.config import settings
from app.models import AlertEventType, AlertLevel
from app.services import llm

TEST_SLUG = "test-pytest-notificacao"


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
    response = client.post("/chat/simulate", json=payload)
    assert response.status_code == 200
    return response.json()


def _events(db, conversation_id):
    db.expire_all()
    [alert] = db.get(models.Conversation, conversation_id).alerts
    return alert, [(e.event_type, e.note) for e in alert.events]


def test_emergency_emails_professional_without_conversation_content(db, client, professional, no_real_email):
    first = _send(client, "to pensando em me matar")

    [email] = no_real_email
    assert email["To"] == "marilia@exemplo.com"
    assert "EMERGÊNCIA" in email["Subject"]
    body = email.get_content()
    assert "me matar" not in body  # nada da conversa sai por e-mail
    assert "simulador do painel" in body

    alert, events = _events(db, first["conversation_id"])
    assert alert.level == AlertLevel.EMERGENCY
    assert events == [(AlertEventType.NOTIFIED, "e-mail para marilia@exemplo.com")]


def test_bot_refusal_also_emails(db, client, professional, no_real_email):
    first = _send(client, "oi")
    _send(client, "não quero falar com robô", first["session_id"])

    [email] = no_real_email
    assert "quer falar com você" in email["Subject"]


def test_intense_suffering_does_not_email(client, professional, no_real_email, monkeypatch):
    monkeypatch.setattr(
        llm,
        "classify_risk",
        lambda history, audience=None: llm.RiskClassification(nivel="sofrimento_intenso", justificativa="t"),
    )
    _send(client, "to muito mal, chorando o dia todo")
    assert no_real_email == []


def test_missing_address_is_recorded_as_failure(db, client, professional, no_real_email):
    client.patch(f"/professionals/{TEST_SLUG}", json={"alert_email": ""})
    first = _send(client, "to pensando em me matar")

    assert no_real_email == []
    _, events = _events(db, first["conversation_id"])
    assert events == [(AlertEventType.NOTIFY_FAILED, "sem e-mail de alerta configurado")]


def test_smtp_error_is_recorded_and_does_not_break_the_reply(db, client, professional, monkeypatch):
    from app.services import notifications, triage

    def fail(message):
        raise ConnectionRefusedError()

    monkeypatch.setattr(notifications, "_send", fail)
    first = _send(client, "to pensando em me matar")
    assert first["reply"] == triage.EMERGENCY_MESSAGE

    _, events = _events(db, first["conversation_id"])
    assert events == [(AlertEventType.NOTIFY_FAILED, "erro no envio: ConnectionRefusedError")]


def test_invalid_alert_email_is_rejected(client, professional):
    response = client.patch(f"/professionals/{TEST_SLUG}", json={"alert_email": "marilia.exemplo.com"})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Pedido levado pela SelenIA (`avisar_profissional`)
# ---------------------------------------------------------------------------


def _assistant_asks(monkeypatch, motivo):
    """O modelo chama `avisar_profissional` e responde."""

    def fake_reply(system_prompt, history, tools=None, run_tool=None):
        assert llm.ASK_PROFESSIONAL_TOOL in tools
        run_tool("avisar_profissional", {"motivo": motivo})
        return "Perguntei e a resposta vem por aqui."

    monkeypatch.setattr(llm, "generate_reply", fake_reply)


def test_assistant_request_emails_once_and_keeps_the_bot_answering(db, client, professional, no_real_email, monkeypatch):
    """Caso real de 18/10/2026: "vou perguntar ao Pedro" sem nada chegar a ele."""
    _assistant_asks(monkeypatch, "horario_especial")
    body = _send(client, "só posso às 21h, pergunta pra ele se topa")
    conversation = db.get(models.Conversation, body["conversation_id"])
    assert conversation.awaiting_reply_since is not None
    assert conversation.awaiting_reason == "horario_especial"
    assert conversation.state == "active"  # a SelenIA continua respondendo

    [email] = no_real_email
    assert email["Subject"] == "[SelenIA] Uma pessoa aguarda uma resposta sua"
    content = email.get_content()
    assert "fora do seu horário de atendimento" in content
    assert "21h" not in content  # nada do que a pessoa escreveu

    # O segundo pedido, antes de ela responder, não manda outro e-mail.
    _assistant_asks(monkeypatch, "pagamento")
    _send(client, "e como pago?", body["session_id"])
    assert len(no_real_email) == 1
    db.expire_all()
    assert db.get(models.Conversation, body["conversation_id"]).awaiting_reason == "horario_especial"

    # A conversa aparece no painel com o motivo, e responder limpa.
    listed = client.get(f"/conversations?professional_slug={TEST_SLUG}").json()[0]
    assert listed["awaiting_reason"] == "horario_especial"
    client.post(f"/conversations/{body['conversation_id']}/messages", json={"content": "Oi, aqui é a Marília."})
    db.expire_all()
    conversation = db.get(models.Conversation, body["conversation_id"])
    assert conversation.awaiting_reply_since is None and conversation.awaiting_reason is None


def test_unknown_reason_becomes_other(db, client, professional, no_real_email, monkeypatch):
    _assistant_asks(monkeypatch, "qualquer coisa")
    body = _send(client, "uma dúvida que só ela sabe")
    assert db.get(models.Conversation, body["conversation_id"]).awaiting_reason == "outro"
    assert "só você pode responder" in no_real_email[0].get_content()


def test_human_request_keeps_its_own_email_and_reason(db, client, professional, no_real_email):
    body = _send(client, "queria falar com a Marília")
    assert db.get(models.Conversation, body["conversation_id"]).awaiting_reason == "falar_com_profissional"
    assert no_real_email[0]["Subject"] == "[SelenIA] Uma pessoa pediu para falar com você"
