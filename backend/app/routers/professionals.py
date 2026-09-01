from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/professionals", tags=["professionals"])


@router.post("", response_model=schemas.ProfessionalOut, status_code=201)
def create_professional(payload: schemas.ProfessionalCreate, db: Session = Depends(get_db)):
    professional = models.Professional(**payload.model_dump())
    db.add(professional)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Slug já está em uso")
    db.refresh(professional)
    return professional


@router.get("", response_model=list[schemas.ProfessionalOut])
def list_professionals(db: Session = Depends(get_db)):
    return db.query(models.Professional).all()


@router.get("/{slug}", response_model=schemas.ProfessionalOut)
def get_professional(slug: str, db: Session = Depends(get_db)):
    professional = db.query(models.Professional).filter_by(slug=slug).first()
    if not professional:
        raise HTTPException(status_code=404, detail="Profissional não encontrado")
    return professional


@router.patch("/{slug}", response_model=schemas.ProfessionalOut)
def update_professional(slug: str, payload: schemas.ProfessionalUpdate, db: Session = Depends(get_db)):
    professional = db.query(models.Professional).filter_by(slug=slug).first()
    if not professional:
        raise HTTPException(status_code=404, detail="Profissional não encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(professional, field, value)
    db.commit()
    db.refresh(professional)
    return professional
