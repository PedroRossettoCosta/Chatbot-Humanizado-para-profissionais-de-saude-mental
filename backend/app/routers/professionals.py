import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services import auth, handoff, onboarding

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
