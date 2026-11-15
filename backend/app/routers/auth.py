"""Login no painel (Google, ou senha da conta de demonstração). Regras em `services/auth.py`."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings
from app.database import get_db
from app.services import auth

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/config", response_model=schemas.AuthConfig)
def get_config():
    """Client ID do Google para o botão de login (não é segredo)."""
    return schemas.AuthConfig(
        google_client_id=settings.google_client_id,
        password_login=auth.password_login_enabled(),
    )


@router.post("/google", response_model=schemas.MeOut)
def login_with_google(payload: schemas.GoogleLogin, request: Request, response: Response, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "desconhecido"
    if not auth.login_limiter.hit(client_ip):
        raise HTTPException(status_code=429, detail="Muitas tentativas. Aguarde alguns minutos.")
    try:
        identity = auth.verify_google_credential(payload.credential)
        user, token = auth.login(db, identity)
    except auth.NotInvited as err:
        raise HTTPException(status_code=403, detail=str(err))
    except auth.AuthError as err:
        raise HTTPException(status_code=401, detail=str(err))
    _set_session_cookie(response, token)
    return _me(user)


@router.post("/password", response_model=schemas.MeOut)
def login_with_password(
    payload: schemas.PasswordLogin, request: Request, response: Response, db: Session = Depends(get_db)
):
    """Só a conta de demonstração da banca (`DEMO_LOGIN_*`)."""
    client_ip = request.client.host if request.client else "desconhecido"
    if not auth.login_limiter.hit(client_ip):
        raise HTTPException(status_code=429, detail="Muitas tentativas. Aguarde alguns minutos.")
    try:
        user, token = auth.login_with_password(db, payload.email, payload.password)
    except auth.NotInvited as err:
        raise HTTPException(status_code=403, detail=str(err))
    except auth.AuthError as err:
        raise HTTPException(status_code=401, detail=str(err))
    _set_session_cookie(response, token)
    return _me(user)


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        auth.SESSION_COOKIE,
        token,
        max_age=settings.session_days * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
        path="/",
    )


@router.get("/me", response_model=schemas.MeOut)
def me(user: models.User = Depends(auth.current_user)):
    return _me(user)


@router.post("/logout", status_code=204)
def logout(request: Request, db: Session = Depends(get_db)):
    auth.logout(db, request.cookies.get(auth.SESSION_COOKIE))
    response = Response(status_code=204)
    response.delete_cookie(auth.SESSION_COOKIE, path="/")
    return response


def _me(user: models.User) -> schemas.MeOut:
    return schemas.MeOut(
        email=user.email,
        name=user.name,
        picture_url=user.picture_url,
        professional=user.professional,
    )
