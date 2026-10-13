"""uso de tokens por chamada ao modelo

- `llm_usage`: uma linha por chamada (resposta ou camada 2 da triagem),
  com o modelo e os tokens de entrada, saída e cache. Sem conteúdo.
  Serve para medir o custo real (feedback de 30/09).

Revision ID: 1e7a4c9b3d62
Revises: 2b8f6d4e9a13
Create Date: 2026-10-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1e7a4c9b3d62'
down_revision: Union[str, Sequence[str], None] = '2b8f6d4e9a13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'llm_usage',
        sa.Column('id', sa.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            'professional_id',
            sa.UUID(as_uuid=False),
            sa.ForeignKey('professionals.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'conversation_id',
            sa.UUID(as_uuid=False),
            sa.ForeignKey('conversations.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column('purpose', sa.String(length=20), nullable=False),
        sa.Column('model', sa.String(length=64), nullable=False),
        sa.Column('input_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('output_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cache_read_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cache_write_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_uso_profissional_data', 'llm_usage', ['professional_id', 'created_at'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_uso_profissional_data', table_name='llm_usage')
    op.drop_table('llm_usage')
