"""Login com Google, lista de convidados, sessões e checagem de dono.

A verificação do token do Google é substituída por um dicionário de
claims; o resto (conta, sessão, cookie, proteção das rotas) é o real.
"""

import pytest

from app import models
from app.config import settings
from app.services import auth, llm

CONVIDADA = "convidada@teste.local"
OUTRA = "outra-convidada@teste.local"
SUB_PREFIX = "test-sub-"


def _claims(email, sub, verified=True):
    return {
        "iss": "https://accounts.google.com",
        "sub": sub,
        "email": email,
        "email_verified": verified,
        "name": "Dra. Teste Login",
        "picture": "https://example.com/foto.png",
    }


@pytest.fixture(autouse=True)
def google_fake(monkeypatch, db):
    """Tokens de mentira: o `credential` é "email|sub|verificado"."""

    def verify(credential, request, audience):
        if credential == "invalido":
            raise ValueError("assinatura inválida")
        email, sub, verified = credential.split("|")
        return _claims(email, sub, verified == "sim")

    monkeypatch.setattr(auth.id_token, "verify_oauth2_token", verify)
    monkeypatch.setattr(settings, "google_client_id", "client-id-de-teste")
    monkeypatch.setattr(settings, "allowed_emails", f"{CONVIDADA}, {OUTRA.upper()}")
    _cleanup(db)
    yield
    _cleanup(db)


def _cleanup(db):
    users = db.query(models.User).filter(models.User.google_sub.like(f"{SUB_PREFIX}%")).all()
    professional_ids = [u.professional_id for u in users if u.professional_id]
    for user in users:
        db.delete(user)
    db.commit()
    for pid in professional_ids:
        professional = db.get(models.Professional, pid)
        if professional:
            db.delete(professional)
    db.commit()


def _login(client, email=CONVIDADA, sub="1", verified="sim"):
    return client.post("/auth/google", json={"credential": f"{email}|{SUB_PREFIX}{sub}|{verified}"})


def test_management_routes_require_login(anon_client):
    assert anon_client.get("/auth/me").status_code == 401
    assert anon_client.get("/professionals/qualquer").status_code == 401
    assert anon_client.post("/professionals", json={"name": "X"}).status_code == 401
    assert anon_client.get("/documents/qualquer").status_code == 401
    assert anon_client.post("/chat/simulate", json={"professional_slug": "x", "message": "oi"}).status_code == 401
    assert anon_client.get("/conversations/qualquer").status_code == 401
    assert anon_client.get("/conversations", params={"professional_slug": "x"}).status_code == 401
    assert anon_client.get("/alerts", params={"professional_slug": "x"}).status_code == 401
    assert anon_client.post("/alerts/qualquer/review", json={}).status_code == 401


def test_public_routes_stay_open(anon_client):
    assert anon_client.get("/health").status_code == 200
    assert anon_client.get("/assistant/guidelines").status_code == 200
    assert anon_client.get("/auth/config").json() == {"google_client_id": "client-id-de-teste"}


def test_first_login_then_signup_then_logout(anon_client, db):
    response = _login(anon_client)
    assert response.status_code == 200
    assert response.json()["professional"] is None
    cookie = response.cookies.get(auth.SESSION_COOKIE)
    assert cookie

    # O banco guarda só o hash do código da sessão.
    assert db.query(models.UserSession).filter_by(token_hash=cookie).first() is None

    response = anon_client.post("/professionals", json={"name": "Dra. Márcia Teste Login"})
    assert response.status_code == 201
    assert response.json()["slug"].startswith("dra-marcia-teste-login")

    me = anon_client.get("/auth/me").json()
    assert me["email"] == CONVIDADA
    assert me["professional"]["name"] == "Dra. Márcia Teste Login"

    # Uma profissional por conta.
    assert anon_client.post("/professionals", json={"name": "De novo"}).status_code == 409

    assert anon_client.post("/auth/logout").status_code == 204
    assert anon_client.get("/auth/me").status_code == 401


def test_uninvited_email_is_refused_without_session(anon_client):
    response = _login(anon_client, email="intrusa@teste.local")
    assert response.status_code == 403
    assert auth.SESSION_COOKIE not in response.cookies


def test_invalid_token_and_unverified_email_are_refused(anon_client):
    assert anon_client.post("/auth/google", json={"credential": "invalido"}).status_code == 401
    assert _login(anon_client, verified="nao").status_code == 401


def test_invite_list_ignores_case(anon_client):
    assert _login(anon_client, email=OUTRA, sub="2").status_code == 200


def test_removed_from_invite_list_loses_access(anon_client, monkeypatch):
    _login(anon_client)
    assert anon_client.get("/auth/me").status_code == 200
    monkeypatch.setattr(settings, "allowed_emails", OUTRA)
    assert anon_client.get("/auth/me").status_code == 401


def test_professional_cannot_see_another_ones_data(anon_client, db, monkeypatch):
    monkeypatch.setattr(llm, "generate_reply", lambda system_prompt, history: "resposta de teste")
    _login(anon_client)
    slug_a = anon_client.post("/professionals", json={"name": "Dra. Teste A"}).json()["slug"]
    conversation_id = anon_client.post(
        "/chat/simulate", json={"professional_slug": slug_a, "message": "oi"}
    ).json()["conversation_id"]

    anon_client.cookies.clear()
    _login(anon_client, email=OUTRA, sub="2")
    anon_client.post("/professionals", json={"name": "Dra. Teste B"})

    assert anon_client.get(f"/professionals/{slug_a}").status_code == 404
    assert anon_client.patch(f"/professionals/{slug_a}", json={"voice_tone": "x"}).status_code == 404
    assert anon_client.get(f"/documents/{slug_a}").status_code == 404
    assert anon_client.post("/chat/simulate", json={"professional_slug": slug_a, "message": "oi"}).status_code == 404
    assert anon_client.get(f"/conversations/{conversation_id}").status_code == 404
    assert anon_client.get("/conversations", params={"professional_slug": slug_a}).status_code == 404
    assert anon_client.get("/alerts", params={"professional_slug": slug_a}).status_code == 404
    assert anon_client.post(f"/conversations/{conversation_id}/take-over").status_code == 404


def test_login_attempts_are_limited(anon_client):
    for _ in range(10):
        anon_client.post("/auth/google", json={"credential": "invalido"})
    assert _login(anon_client).status_code == 429
