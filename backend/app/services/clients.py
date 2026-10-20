"""Clientes ativos e a permissão de horário especial (tela Clientes).

Pedido do Pedro em 19/10/2026, a partir do teste de 18/10 em que o
contato disse ser "um paciente especial que precisa de mais atenção" e
pediu sessão às 21h, fora do expediente. A SelenIA não tem como saber se
isso é verdade, então quem decide é a profissional, no painel:

1. **Cliente ativo** (`Contact.active_since`): a pessoa vira ativa
   sozinha quando a profissional confirma uma sessão pedida na conversa
   (`appointments.approve` chama `activate`). A profissional também pode
   marcar ou tirar alguém da lista na mão.
2. **Condição especial** (`Contact.allow_special_hours`): para quem
   está na lista, a profissional liga a permissão e escolhe os dias
   especiais daquela pessoa (`Contact.special_days`). Nesses dias a
   SelenIA oferece a ela qualquer horário livre do dia, e o limite de
   sessões por dia não vale para ela em nenhum dia. Quem
   não tem a permissão continua vendo só o expediente, diga o que disser
   na conversa.

Tirar alguém da lista desliga a permissão junto: uma pessoa que deixou
de ser atendida não continua com acesso a horário fora do expediente.
"""

from sqlalchemy.orm import Session

from app import models
from app.models import AppointmentStatus
from app.services import calendar, conversations


def activate(db: Session, contact: models.Contact) -> None:
    """Marca como cliente ativo, se ainda não era. Não grava: quem chama faz o commit."""
    if contact.active_since is None:
        contact.active_since = models._now()


def update(
    db: Session,
    contact: models.Contact,
    active: bool | None,
    allow_special_hours: bool | None,
    special_days: list[str] | None = None,
) -> None:
    """Muda o que a profissional mexeu na tela. Tirar da lista ganha de
    qualquer outra coisa; ligar a permissão põe na lista."""
    if active is False:
        contact.active_since = None
        contact.allow_special_hours = False
        contact.special_days = None
    else:
        if active or allow_special_hours:
            activate(db, contact)
        if allow_special_hours is not None:
            contact.allow_special_hours = allow_special_hours
        if special_days is not None:
            contact.special_days = special_days or None
    db.commit()


def _next_session(contact: models.Contact, now) -> str | None:
    upcoming = [
        a.starts_at
        for conversation in contact.conversations
        for a in conversation.appointments
        if a.status == AppointmentStatus.CONFIRMED and a.cancel_requested_at is None and a.starts_at > now
    ]
    return calendar.format_slot(min(upcoming)) if upcoming else None


def summary(contact: models.Contact, now=None) -> dict:
    """Linha da tela Clientes. O número vai mascarado, como nas listas."""
    now = now or models._now()
    name, phone = conversations.contact_label(contact, full_phone=False)
    latest = max(contact.conversations, key=lambda c: c.last_message_at or c.created_at, default=None)
    return {
        "id": contact.id,
        "channel": contact.channel,
        "contact_name": name,
        "contact_phone": phone,
        "active_since": contact.active_since,
        "allow_special_hours": bool(contact.allow_special_hours) and contact.active_since is not None,
        "special_days": contact.special_days or [],
        "conversation_id": latest.id if latest else None,
        "last_message_at": latest.last_message_at if latest else None,
        "next_session": _next_session(contact, now),
    }
