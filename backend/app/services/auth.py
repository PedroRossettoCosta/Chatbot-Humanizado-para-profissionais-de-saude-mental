"""Login no painel com o Google e sessões.

Como funciona:

1. O botão do Google, no navegador, devolve um token assinado pelo
   Google dizendo quem é a pessoa (`credential`).
2. `verify_google_credential` confere a assinatura, se o token foi
   emitido para o nosso Client ID e se o e-mail foi verificado.
3. Só entra quem está em `settings.allowed_emails` (MVP por convite).
4. A sessão é um código aleatório num cookie `httpOnly`; o banco guarda
   só o hash dele (`UserSession`).

Toda rota de gestão depende de `current_user`, e toda ação sobre dados
de uma profissional passa por `ensure_owner`.
"""

import hashlib
import secrets
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import timedelta

from fastapi import Depends, HTTPException, Request
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.database import get_db

SESSION_COOKIE = "maria_session"

_GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


class AuthError(Exception):
    """Login recusado. A mensagem pode ir para a tela."""


class NotInvited(AuthError):
    """A conta Google é válida, mas o e-mail não está na lista de convidados."""


@dataclass
class GoogleIdentity:
    sub: str
    email: str
    name: str | None
    picture_url: str | None


def verify_google_credential(credential: str) -> GoogleIdentity:
    if not settings.google_client_id:
        raise AuthError("Login com Google não configurado (GOOGLE_CLIENT_ID).")
    try:
        claims = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            settings.google_client_id,
            # Relógio desta máquina alguns segundos atrás do Google.
            clock_skew_in_seconds=30,
        )
    except ValueError:
        # Assinatura inválida, token vencido ou emitido para outro app.
        raise AuthError("Não foi possível confirmar o login com o Google.")
    if claims.get("iss") not in _GOOGLE_ISSUERS:
        raise AuthError("Não foi possível confirmar o login com o Google.")
    if not claims.get("email") or not claims.get("email_verified"):
        raise AuthError("A conta Google precisa ter um e-mail verificado.")
    return GoogleIdentity(
        sub=claims["sub"],
        email=claims["email"].lower(),
        name=claims.get("name"),
        picture_url=claims.get("picture"),
    )


def allowed_emails() -> set[str]:
    return {e.strip().lower() for e in settings.allowed_emails.split(",") if e.strip()}


def is_allowed(email: str) -> bool:
    return email.lower() in allowed_emails()


def login(db: Session, identity: GoogleIdentity) -> tuple[models.User, str]:
    """Cria ou atualiza a conta e abre uma sessão. Devolve o código do cookie."""
    if not is_allowed(identity.email):
        raise NotInvited("Acesso ainda não liberado para este e-mail.")

    user = db.query(models.User).filter_by(google_sub=identity.sub).first()
    if user is None:
        user = models.User(google_sub=identity.sub, email=identity.email)
        db.add(user)
    user.email = identity.email
    user.name = identity.name
    user.picture_url = identity.picture_url
    user.last_login_at = models._now()

    token = secrets.token_urlsafe(32)
    db.add(
        models.UserSession(
            user=user,
            token_hash=_hash(token),
            expires_at=models._now() + timedelta(days=settings.session_days),
        )
    )
    db.commit()
    db.refresh(user)
    return user, token


def user_for_token(db: Session, token: str | None) -> models.User | None:
    if not token:
        return None
    session = db.query(models.UserSession).filter_by(token_hash=_hash(token)).first()
    if session is None:
        return None
    if session.expires_at <= models._now():
        db.delete(session)
        db.commit()
        return None
    # Quem foi tirado da lista de convidados perde o acesso na hora,
    # mesmo com uma sessão ainda válida.
    if not is_allowed(session.user.email):
        return None
    return session.user


def logout(db: Session, token: str | None) -> None:
    if not token:
        return
    db.query(models.UserSession).filter_by(token_hash=_hash(token)).delete()
    db.commit()


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Dependências das rotas
# ---------------------------------------------------------------------------


def current_user(request: Request, db: Session = Depends(get_db)) -> models.User:
    user = user_for_token(db, request.cookies.get(SESSION_COOKIE))
    if user is None:
        raise HTTPException(status_code=401, detail="Faça login para continuar.")
    return user


def ensure_owner(user: models.User, professional_id: str) -> None:
    """Dados de outra profissional respondem como inexistentes (404).

    Um 403 confirmaria que o recurso existe.
    """
    if not user.owns(professional_id):
        raise HTTPException(status_code=404, detail="Não encontrado")


# ---------------------------------------------------------------------------
# Limite de tentativas de login
# ---------------------------------------------------------------------------


class RateLimiter:
    """Janela deslizante em memória, por IP.

    Suficiente para um processo só (o MVP). Com mais de um processo, a
    contagem precisa ir para um lugar compartilhado.
    """

    def __init__(self, max_attempts: int, window_seconds: int):
        self.max_attempts = max_attempts
        self.window = window_seconds
        self._attempts: dict[str, deque] = defaultdict(deque)

    def hit(self, key: str) -> bool:
        """Registra uma tentativa. Falso = passou do limite."""
        now = time.monotonic()
        attempts = self._attempts[key]
        while attempts and attempts[0] <= now - self.window:
            attempts.popleft()
        if len(attempts) >= self.max_attempts:
            return False
        attempts.append(now)
        return True

    def reset(self) -> None:
        self._attempts.clear()


login_limiter = RateLimiter(max_attempts=10, window_seconds=300)
