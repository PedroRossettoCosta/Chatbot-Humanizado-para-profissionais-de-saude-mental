import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.services import llm, notifications


@pytest.fixture(autouse=True)
def triage_model_says_normal(monkeypatch):
    """Nenhum teste chama a API de verdade na camada 2 da triagem.

    Por padrão o modelo responde "normal"; o teste que precisar de outro
    nível sobrescreve `llm.classify_risk`.
    """
    monkeypatch.setattr(
        llm,
        "classify_risk",
        lambda history, audience=None: llm.RiskClassification(nivel="normal", justificativa="teste"),
    )


@pytest.fixture(autouse=True)
def no_real_email(monkeypatch):
    """Nenhum teste envia e-mail de verdade, mesmo com SMTP no `.env`.

    Os e-mails "enviados" ficam em `notifications.sent_in_tests`.
    """
    sent = []
    monkeypatch.setattr(notifications, "_send", sent.append)
    monkeypatch.setattr(notifications, "sent_in_tests", sent, raising=False)
    return sent


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
