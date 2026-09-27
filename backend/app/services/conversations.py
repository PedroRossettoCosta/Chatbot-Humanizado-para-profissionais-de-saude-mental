"""Operações de contato, conversa e mensagem, independentes do canal.

Este módulo é a fronteira entre o núcleo do sistema e os canais: tanto o
simulador do painel quanto o webhook do WhatsApp chamam estas funções,
passando apenas `channel` e `external_id`. Nada aqui sabe o formato de
payload da Meta, e nada aqui precisa mudar quando entrar um canal novo.
"""

import re
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app import models
from app.models import AlertLevel, Channel, ConversationState, MessageRole, SentBy
from app.services import crypto

# Regra da Meta: fora das 24h depois da última mensagem do contato, só
# modelo de mensagem aprovado (pago), que o MVP não usa. O simulador
# segue a mesma regra, para o teste mostrar o que acontece no WhatsApp.
REPLY_WINDOW = timedelta(hours=24)


def reply_window_closes_at(conversation: models.Conversation) -> datetime | None:
    if conversation.last_contact_message_at is None:
        return None
    return conversation.last_contact_message_at + REPLY_WINDOW


def reply_window_open(conversation: models.Conversation) -> bool:
    closes_at = reply_window_closes_at(conversation)
    return closes_at is not None and closes_at > models._now()


def contact_phone(contact: models.Contact) -> str | None:
    """Número completo, formatado (+55 21 95555-4444). Só no WhatsApp."""
    if contact.channel != Channel.WHATSAPP:
        return None
    # Quem usa nome de usuário no WhatsApp chega com um id da Meta
    # (BSUID), não com o número: aí não há telefone para mostrar.
    if not re.fullmatch(r"\+?\d{8,15}", contact.external_id):
        return None
    digits = re.sub(r"\D", "", contact.external_id)
    if digits.startswith("55") and len(digits) in (12, 13):
        return f"+55 {digits[2:4]} {digits[4:-4]}-{digits[-4:]}"
    return f"+{digits}"


def masked_phone(contact: models.Contact) -> str | None:
    """Número para a lista (+55 21 •••••-4444): quem olha por cima do
    ombro da profissional não lê o número inteiro."""
    phone = contact_phone(contact)
    if phone is None:
        return None
    digits = re.sub(r"\D", "", phone)
    if phone.startswith("+55 "):
        return f"+55 {digits[2:4]} •••••-{digits[-4:]}"
    return f"•••••-{digits[-4:]}"


def contact_label(contact: models.Contact, full_phone: bool) -> tuple[str, str | None]:
    """Nome e número para mostrar no painel.

    Nome: o do perfil do WhatsApp; sem ele, o número; no simulador,
    "Conversa de teste". Número mascarado nas listas, completo quando a
    conversa ou o alerta está aberto.
    """
    phone = contact_phone(contact) if full_phone else masked_phone(contact)
    if contact.channel == Channel.SIMULATOR:
        return "Conversa de teste", phone
    return contact.display_name or phone or "Contato do WhatsApp", phone


def get_or_create_contact(
    db: Session,
    professional: models.Professional,
    channel: Channel,
    external_id: str,
    display_name: str | None = None,
) -> models.Contact:
    """Encontra o contato pelo identificador do canal, ou cria um novo.

    A busca é feita pelo índice cego, já que `external_id` fica cifrado
    no banco e cifras iguais não se repetem.
    """
    index = crypto.blind_index(external_id)
    contact = (
        db.query(models.Contact)
        .filter_by(professional_id=professional.id, channel=channel, external_id_index=index)
        .first()
    )
    if contact:
        # O nome do perfil pode mudar com o tempo no canal de origem.
        if display_name and contact.display_name != display_name:
            contact.display_name = display_name
            db.commit()
        return contact

    contact = models.Contact(
        professional_id=professional.id,
        channel=channel,
        external_id=external_id,
        external_id_index=index,
        display_name=display_name,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def get_or_create_conversation(
    db: Session, contact: models.Contact
) -> tuple[models.Conversation, bool]:
    """Devolve a conversa em andamento do contato, criando se não houver.

    O segundo valor indica se a conversa acabou de ser criada — é o que
    diz ao chamador que o aviso de IA precisa ser enviado.
    """
    conversation = (
        db.query(models.Conversation)
        .filter_by(contact_id=contact.id)
        .order_by(models.Conversation.created_at.desc())
        .first()
    )
    if conversation:
        return conversation, False

    conversation = models.Conversation(
        professional_id=contact.professional_id,
        contact_id=contact.id,
        state=ConversationState.ACTIVE,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation, True


def record_message(
    db: Session,
    conversation: models.Conversation,
    role: MessageRole,
    content: str,
    sent_by: SentBy | None = None,
    external_id: str | None = None,
) -> models.Message:
    """Grava uma mensagem e atualiza o horário da última atividade."""
    message = models.Message(
        conversation_id=conversation.id,
        role=role,
        content=content,
        sent_by=sent_by,
        external_id=external_id,
    )
    db.add(message)
    now = models._now()
    conversation.last_message_at = now
    if role == MessageRole.USER:
        conversation.last_contact_message_at = now
    db.commit()
    db.refresh(message)
    return message


def recent_history(db: Session, conversation: models.Conversation, limit: int) -> list[dict]:
    """Últimas mensagens no formato que a API da Claude espera.

    A ordenação usa `seq` (ordem de inserção garantida pelo banco), e não
    o horário: duas mensagens no mesmo milissegundo receberiam o mesmo
    `created_at` e o histórico chegaria embaralhado ao modelo.
    """
    messages = (
        db.query(models.Message)
        .filter_by(conversation_id=conversation.id)
        .order_by(models.Message.seq.desc())
        .limit(limit)
        .all()
    )
    return [{"role": m.role, "content": m.content} for m in reversed(messages)]


def recent_contact_texts(
    db: Session, conversation: models.Conversation, limit: int, within: timedelta
) -> list[str]:
    """Últimas mensagens do contato, da mais antiga para a mais nova.

    Só as que chegaram dentro de `within` antes da mais nova: a triagem
    junta mensagens seguidas ("eu to pensando" / "em me matar"), não uma
    frase de hoje com outra de ontem.
    """
    messages = (
        db.query(models.Message)
        .filter_by(conversation_id=conversation.id, role=MessageRole.USER)
        .order_by(models.Message.seq.desc())
        .limit(limit)
        .all()
    )
    if not messages:
        return []
    newest = messages[0].created_at
    return [m.content for m in reversed(messages) if newest - m.created_at <= within]


def raise_safety_alert(
    db: Session,
    conversation: models.Conversation,
    message: models.Message,
    level: AlertLevel,
    trigger: str,
    excerpt: str,
) -> models.SafetyAlert:
    """Grava o alerta e coloca a conversa em espera de emergência.

    O alerta e a mudança de estado vão no mesmo commit: não pode existir
    alerta com o bot ainda respondendo normalmente, nem o contrário.
    """
    alert = models.SafetyAlert(
        professional_id=conversation.professional_id,
        conversation_id=conversation.id,
        message_id=message.id,
        level=level,
        trigger=trigger,
        excerpt=excerpt,
    )
    db.add(alert)
    if level == AlertLevel.EMERGENCY:
        conversation.state = ConversationState.EMERGENCY_HOLD
    else:
        conversation.needs_attention = True
    db.commit()
    db.refresh(alert)
    return alert


def mark_needs_attention(db: Session, conversation: models.Conversation) -> None:
    """Sofrimento intenso: sinaliza para a profissional, sem abrir alerta.

    A Marília pediu que sofrimento sem referência a risco não vire alerta
    de segurança, só a marcação "necessita atenção" no inbox.
    """
    if not conversation.needs_attention:
        conversation.needs_attention = True
        db.commit()
