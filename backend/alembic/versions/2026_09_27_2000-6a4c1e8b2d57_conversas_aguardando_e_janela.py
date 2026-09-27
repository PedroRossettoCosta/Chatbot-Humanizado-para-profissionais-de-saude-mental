"""conversas: aguardando você e janela de 24h

`awaiting_reply_since`: a pessoa pediu para falar com a profissional e
ainda não teve resposta. `last_contact_message_at`: última mensagem do
contato, para a janela de 24h do WhatsApp. As conversas que já existem
recebem a hora da última mensagem do contato.

Revision ID: 6a4c1e8b2d57
Revises: 3f9d2b6a1c47
Create Date: 2026-09-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6a4c1e8b2d57'
down_revision: Union[str, Sequence[str], None] = '3f9d2b6a1c47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('conversations', sa.Column('awaiting_reply_since', sa.DateTime(timezone=True), nullable=True))
    op.add_column('conversations', sa.Column('last_contact_message_at', sa.DateTime(timezone=True), nullable=True))
    op.execute(
        """
        UPDATE conversations c
        SET last_contact_message_at = (
            SELECT max(m.created_at) FROM messages m
            WHERE m.conversation_id = c.id AND m.role = 'user'
        )
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('conversations', 'last_contact_message_at')
    op.drop_column('conversations', 'awaiting_reply_since')
