import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services import auth, handoff, onboarding, whatsapp_numbers

router = APIRouter(prefix="/professionals", tags=["professionals"])


@router.post("", response_model=schemas.ProfessionalOut, status_code=201)
def create_professional(
    payload: schemas.ProfessionalCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.current_user),
):
    """Cria a profissional da conta logada (cadastro). Uma por conta."""
    if user.professional_id:
        raise HTTPException(status_code=409, detail="Esta conta já tem um cadastro.")
    data = payload.model_dump()
    data["slug"] = data["slug"] or _unique_slug(db, payload.name)
    # Criar a profissional conclui a etapa 1 do cadastro.
    data["onboarding_step"] = 2
    professional = models.Professional(**data)
    db.add(professional)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Slug já está em uso")
    user.professional_id = professional.id
    db.commit()
    db.refresh(professional)
    return professional


@router.get("/{slug}", response_model=schemas.ProfessionalOut)
def get_professional(slug: str, db: Session = Depends(get_db), user: models.User = Depends(auth.current_user)):
    return _get_owned(db, slug, user)


@router.patch("/{slug}", response_model=schemas.ProfessionalOut)
def update_professional(
    slug: str,
    payload: schemas.ProfessionalUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.current_user),
):
    professional = _get_owned(db, slug, user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(professional, field, value)
    db.commit()
    db.refresh(professional)
    return professional


@router.post("/{slug}/accept-rules", response_model=schemas.ProfessionalOut)
def accept_rules(
    slug: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.current_user),
):
    """Registra que ela leu e aceitou as regras fixas da SelenIA (etapa 4)."""
    professional = _get_owned(db, slug, user)
    onboarding.accept_rules(professional)
    db.commit()
    db.refresh(professional)
    return professional


@router.post("/{slug}/complete-onboarding", response_model=schemas.ProfessionalOut)
def complete_onboarding(
    slug: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.current_user),
):
    """Conclui o cadastro, se tudo o que é obrigatório estiver preenchido."""
    professional = _get_owned(db, slug, user)
    missing = onboarding.complete(professional)
    if missing:
        raise HTTPException(status_code=422, detail={"message": "Cadastro incompleto", "missing": missing})
    db.commit()
    db.refresh(professional)
    return professional


@router.put("/{slug}/in-session", response_model=schemas.ProfessionalOut)
def start_session(
    slug: str,
    payload: schemas.InSessionStart,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.current_user),
):
    """Liga o botão "Em consulta" (por `minutes`, ou até desligar se nulo)."""
    professional = _get_owned(db, slug, user)
    handoff.start_session(db, professional, payload.minutes)
    return professional


@router.delete("/{slug}/in-session", response_model=schemas.ProfessionalOut)
def end_session(slug: str, db: Session = Depends(get_db), user: models.User = Depends(auth.current_user)):
    professional = _get_owned(db, slug, user)
    handoff.end_session(db, professional)
    return professional


# ---------------------------------------------------------------------------
# Conectar o WhatsApp (etapa 6 do cadastro e Perfil)
# ---------------------------------------------------------------------------


def _whatsapp_step(action, db: Session, professional: models.Professional, *args) -> dict:
    try:
        action(db, professional, *args)
    except whatsapp_numbers.NumberError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc))
    db.refresh(professional)
    return whatsapp_numbers.status(db, professional)


@router.get("/{slug}/whatsapp", response_model=schemas.WhatsAppStatus)
def whatsapp_status(slug: str, db: Session = Depends(get_db), user: models.User = Depends(auth.current_user)):
    return whatsapp_numbers.status(db, _get_owned(db, slug, user))


@router.post("/{slug}/whatsapp", response_model=schemas.WhatsAppStatus)
def whatsapp_start(
    slug: str,
    payload: schemas.WhatsAppStart,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.current_user),
):
    """Cadastra o número na conta da Meta e pede o código (SMS ou ligação)."""
    professional = _get_owned(db, slug, user)
    return _whatsapp_step(
        whatsapp_numbers.start, db, professional, payload.number, payload.display_name, payload.method
    )


@router.post("/{slug}/whatsapp/resend", response_model=schemas.WhatsAppStatus)
def whatsapp_resend(
    slug: str,
    payload: schemas.WhatsAppResend,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.current_user),
):
    return _whatsapp_step(whatsapp_numbers.resend_code, db, _get_owned(db, slug, user), payload.method)


@router.post("/{slug}/whatsapp/verify", response_model=schemas.WhatsAppStatus)
def whatsapp_verify(
    slug: str,
    payload: schemas.WhatsAppVerify,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.current_user),
):
    """Confere o código e, se der certo, registra o número."""
    return _whatsapp_step(whatsapp_numbers.verify, db, _get_owned(db, slug, user), payload.code)


@router.post("/{slug}/whatsapp/register", response_model=schemas.WhatsAppStatus)
def whatsapp_register(slug: str, db: Session = Depends(get_db), user: models.User = Depends(auth.current_user)):
    """Tenta o registro de novo (número já verificado, registro falhou)."""
    return _whatsapp_step(whatsapp_numbers.register, db, _get_owned(db, slug, user))


@router.delete("/{slug}/whatsapp/pending", response_model=schemas.WhatsAppStatus)
def whatsapp_cancel(slug: str, db: Session = Depends(get_db), user: models.User = Depends(auth.current_user)):
    return _whatsapp_step(whatsapp_numbers.cancel, db, _get_owned(db, slug, user))


@router.post("/{slug}/whatsapp/name", response_model=schemas.WhatsAppStatus)
def whatsapp_rename(
    slug: str,
    payload: schemas.WhatsAppRename,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.current_user),
):
    """Pede à Meta para trocar o nome que aparece no WhatsApp."""
    return _whatsapp_step(whatsapp_numbers.rename, db, _get_owned(db, slug, user), payload.display_name)


@router.post("/{slug}/whatsapp/name/apply", response_model=schemas.WhatsAppStatus)
def whatsapp_apply_name(slug: str, db: Session = Depends(get_db), user: models.User = Depends(auth.current_user)):
    """Nome novo aprovado: registra o número de novo para ele aparecer."""
    return _whatsapp_step(whatsapp_numbers.apply_name, db, _get_owned(db, slug, user))


@router.delete("/{slug}/whatsapp", response_model=schemas.WhatsAppStatus)
def whatsapp_disconnect(slug: str, db: Session = Depends(get_db), user: models.User = Depends(auth.current_user)):
    """Desconecta o número, para conectar outro."""
    return _whatsapp_step(whatsapp_numbers.disconnect, db, _get_owned(db, slug, user))


def _get_owned(db: Session, slug: str, user: models.User) -> models.Professional:
    professional = db.query(models.Professional).filter_by(slug=slug).first()
    if not professional or not user.owns(professional.id):
        raise HTTPException(status_code=404, detail="Profissional não encontrado")
    return professional


def _unique_slug(db: Session, name: str) -> str:
    """"Dra. Marília Rossetto" → "dra-marilia-rossetto" (com sufixo se já existir)."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")[:56] or "profissional"
    if len(base) < 3:
        base = f"{base}-maria"
    slug, n = base, 2
    while db.query(models.Professional).filter_by(slug=slug).first():
        slug, n = f"{base}-{n}", n + 1
    return slug
