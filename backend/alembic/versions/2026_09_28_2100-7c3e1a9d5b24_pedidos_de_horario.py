"""pedidos de horário

A MarIA passa a reservar horário provisório: nome dado pela pessoa
(cifrado), validade do pedido, quando a profissional decidiu e se a
pessoa foi avisada. O índice único parcial impede dois pedidos ativos
no mesmo horário da mesma profissional.

Revision ID: 7c3e1a9d5b24
Revises: 4d7b9e2a6c31
Create Date: 2026-09-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c3e1a9d5b24'
down_revision: Union[str, Sequence[str], None] = '4d7b9e2a6c31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('appointments', sa.Column('patient_name', sa.Text(), nullable=True))
    op.add_column('appointments', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('appointments', sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('appointments', sa.Column('contact_notified', sa.Boolean(), nullable=True))
    op.create_index(
        'uq_appointment_active_slot',
        'appointments',
        ['professional_id', 'starts_at'],
        unique=True,
        postgresql_where=sa.text("status IN ('tentative', 'confirmed')"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('uq_appointment_active_slot', table_name='appointments')
    op.drop_column('appointments', 'contact_notified')
    op.drop_column('appointments', 'decided_at')
    op.drop_column('appointments', 'expires_at')
    op.drop_column('appointments', 'patient_name')
