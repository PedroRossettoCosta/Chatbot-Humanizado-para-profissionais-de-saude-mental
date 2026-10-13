"""remarcar e cancelar como pedido

- `appointments.replaces_id`: no pedido de troca, a sessão que ele
  substitui quando a profissional confirmar.
- `appointments.cancel_requested_at`: a pessoa pediu para cancelar esta
  sessão confirmada; a profissional ainda não decidiu.

Revision ID: 8b3f6a2d9c15
Revises: 5c2d8e1f7a40
Create Date: 2026-10-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b3f6a2d9c15'
down_revision: Union[str, Sequence[str], None] = '5c2d8e1f7a40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'appointments',
        sa.Column(
            'replaces_id',
            sa.UUID(as_uuid=False),
            sa.ForeignKey('appointments.id', ondelete='SET NULL'),
            nullable=True,
        ),
    )
    op.add_column('appointments', sa.Column('cancel_requested_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('appointments', 'cancel_requested_at')
    op.drop_column('appointments', 'replaces_id')
