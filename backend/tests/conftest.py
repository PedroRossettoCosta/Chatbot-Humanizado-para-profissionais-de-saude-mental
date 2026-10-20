import pytest
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.main import app
from app.services import auth, llm, notifications, whatsapp


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


@pytest.fixture(autouse=True)
def no_real_whatsapp(monkeypatch):
    """Nenhum teste chama a API da Meta.

    Cada chamada fica em `whatsapp.calls_in_tests` como (número, corpo),
    e o envio devolve um `wamid` falso.
    """
    calls = []

    def fake_post(phone_number_id, body):
        calls.append((phone_number_id, body))
        return {"messages": [{"id": f"wamid.teste.saida.{len(calls)}"}]}

    def no_graph(method, path, body=None, params=None):
        raise AssertionError(f"teste chamou a Graph API de verdade: {method} {path}")

    monkeypatch.setattr(whatsapp, "_post", fake_post)
    monkeypatch.setattr(whatsapp, "_graph", no_graph)
    monkeypatch.setattr(whatsapp, "calls_in_tests", calls, raising=False)
    return calls


class _OwnerOfEverything:
    """Conta de teste que é dona de qualquer profissional.

    Os testes das funcionalidades (chat, triagem, handoff...) não são
    sobre login; com ela, cada um continua criando a profissional de que
    precisa. O login e a checagem de dono de verdade são testados em
    `test_auth.py`, com o cliente `anon_client`.
    """

    email = "dona-de-tudo@teste.local"
    name = "Teste"
    picture_url = None
    professional_id = None
    professional = None

    def owns(self, professional_id):
        return True


@pytest.fixture
def client():
    app.dependency_overrides[auth.current_user] = lambda: _OwnerOfEverything()
    yield TestClient(app)
    app.dependency_overrides.pop(auth.current_user, None)


@pytest.fixture
def anon_client():
    """Cliente sem login: passa pela autenticação de verdade."""
    auth.login_limiter.reset()
    return TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
