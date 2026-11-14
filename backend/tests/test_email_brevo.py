"""Envio de e-mail pela API HTTPS da Brevo (a Railway bloqueia SMTP)."""

from email.message import EmailMessage

import pytest

from app.config import settings
from app.services import notifications


class _Response:
    def __init__(self, status_code):
        self.status_code = status_code


def _message():
    message = EmailMessage()
    message["Subject"] = "[SelenIA] Teste"
    message["From"] = "SelenIA <remetente@exemplo.com>"
    message["To"] = "profissional@exemplo.com"
    message.set_content("Olá.\n— SelenIA")
    return message


def test_brevo_receives_sender_recipient_subject_and_text(monkeypatch):
    calls = []
    monkeypatch.setattr(settings, "brevo_api_key", "xkeysib-teste")
    monkeypatch.setattr(notifications.requests, "post", lambda url, **kw: calls.append((url, kw)) or _Response(201))

    notifications._send_brevo(_message())

    [(url, kw)] = calls
    assert url == notifications.BREVO_URL
    assert kw["headers"]["api-key"] == "xkeysib-teste"
    assert kw["json"]["sender"] == {"email": "remetente@exemplo.com", "name": "SelenIA"}
    assert kw["json"]["to"] == [{"email": "profissional@exemplo.com"}]
    assert kw["json"]["subject"] == "[SelenIA] Teste"
    assert kw["json"]["textContent"].startswith("Olá.")


def test_brevo_error_is_raised_so_the_alert_records_the_failure(monkeypatch):
    monkeypatch.setattr(settings, "brevo_api_key", "xkeysib-teste")
    monkeypatch.setattr(notifications.requests, "post", lambda url, **kw: _Response(401))
    with pytest.raises(RuntimeError, match="401"):
        notifications._send_brevo(_message())


def test_brevo_key_alone_counts_as_configured(monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "")
    monkeypatch.setattr(settings, "brevo_api_key", "")
    assert not notifications.email_configured()
    monkeypatch.setattr(settings, "brevo_api_key", "xkeysib-teste")
    assert notifications.email_configured()
