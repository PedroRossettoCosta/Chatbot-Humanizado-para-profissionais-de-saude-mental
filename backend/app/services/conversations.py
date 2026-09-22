"""Operações de contato, conversa e mensagem, independentes do canal.

Este módulo é a fronteira entre o núcleo do sistema e os canais: tanto o
simulador do painel quanto o webhook do WhatsApp chamam estas funções,
passando apenas `channel` e `external_id`. Nada aqui sabe o formato de
payload da Meta, e nada aqui precisa mudar quando entrar um canal novo.
"""

from sqlalchemy.orm import Session

from app import models
from app.models import Channel, ConversationState, MessageRole, SentBy
from app.services import crypto


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
    conversation.last_message_at = models._now()
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
