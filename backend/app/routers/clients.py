"""Tela Clientes: quem já conversou, quem é cliente ativo e quem pode
marcar em horário especial. Regras em `services/clients.py`.

Todas exigem login, e só a dona dos contatos enxerga ou muda.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app import models, schemas
from app.database import get_db
from app.services import auth, clients

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[schemas.ClientOut])
def list_clients(
    professional_slug: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.current_user),
):
    """Ativos primeiro (o mais antigo no topo), depois os outros contatos,
    do que escreveu por último para o mais antigo."""
    professional = db.query(models.Professional).filter_by(slug=professional_slug).first()
    if not professional or not user.owns(professional.id):
        raise HTTPException(status_code=404, detail="Profissional não encontrado")
    contacts = (
        db.query(models.Contact)
        .options(selectinload(models.Contact.conversations).selectinload(models.Conversation.appointments))
        .filter_by(professional_id=professional.id)
        .all()
    )
    rows = [clients.summary(c) for c in contacts]
    rows.sort(key=lambda r: r["last_message_at"].timestamp() if r["last_message_at"] else 0, reverse=True)
    rows.sort(key=lambda r: (r["active_since"] is None, r["active_since"].timestamp() if r["active_since"] else 0))
    return rows


@router.patch("/{contact_id}", response_model=schemas.ClientOut)
def update_client(
    contact_id: str,
    payload: schemas.ClientUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.current_user),
):
    contact = db.get(models.Contact, contact_id)
    if not contact or not user.owns(contact.professional_id):
        raise HTTPException(status_code=404, detail="Contato não encontrado")
    clients.update(db, contact, payload.active, payload.allow_special_hours, payload.special_days)
    db.refresh(contact)
    return clients.summary(contact)
