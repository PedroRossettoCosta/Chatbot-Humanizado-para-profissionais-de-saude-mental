"""falha de envio pela Meta

- `messages.delivery_failed`: a Meta recusou o envio de uma mensagem de
  saída pelo WhatsApp. Antes, o erro ficava só no terminal e o painel
  mostrava a mensagem como se tivesse saído.

Revision ID: 5c2d8e1f7a40
Revises: 1e7a4c9b3d62
Create Date: 2026-10-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c2d8e1f7a40'
down_revision: Union[str, Sequence[str], None] = '1e7a4c9b3d62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'messages', sa.Column('delivery_failed', sa.Boolean(), nullable=False, server_default=sa.false())
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('messages', 'delivery_failed')
