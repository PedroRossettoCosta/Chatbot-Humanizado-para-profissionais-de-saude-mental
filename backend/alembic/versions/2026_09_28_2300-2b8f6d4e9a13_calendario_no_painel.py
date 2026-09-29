"""calendário no painel e limite de sessões por dia

- `appointments.conversation_id` passa a aceitar nulo: a profissional
  marca sessões pelo painel, sem conversa.
- `appointments.source`: "maria" ou "panel".
- `professionals.max_sessions_per_day`: limite de sessões por dia que a
  MarIA pode marcar.

Revision ID: 2b8f6d4e9a13
Revises: 7c3e1a9d5b24
Create Date: 2026-09-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2b8f6d4e9a13'
down_revision: Union[str, Sequence[str], None] = '7c3e1a9d5b24'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('appointments', 'conversation_id', existing_type=sa.UUID(as_uuid=False), nullable=True)
    op.add_column('appointments', sa.Column('source', sa.String(length=20), nullable=False, server_default='maria'))
    op.add_column('professionals', sa.Column('max_sessions_per_day', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('professionals', 'max_sessions_per_day')
    op.drop_column('appointments', 'source')
    op.execute("DELETE FROM appointments WHERE conversation_id IS NULL")
    op.alter_column('appointments', 'conversation_id', existing_type=sa.UUID(as_uuid=False), nullable=False)
