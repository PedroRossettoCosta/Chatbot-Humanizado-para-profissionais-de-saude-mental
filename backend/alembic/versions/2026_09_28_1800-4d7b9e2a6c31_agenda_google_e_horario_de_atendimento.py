"""agenda do Google e horário de atendimento

O acesso ao Google Agenda de cada profissional (só livre/ocupado, com o
código de acesso cifrado) e os dias e horários em que ela atende.

Revision ID: 4d7b9e2a6c31
Revises: 9d2f7a3c5e18
Create Date: 2026-09-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '4d7b9e2a6c31'
down_revision: Union[str, Sequence[str], None] = '9d2f7a3c5e18'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('professionals', sa.Column('working_hours', sa.JSON(), nullable=True))
    op.create_table(
        'calendar_connections',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('professional_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('google_email', sa.String(length=255), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=False),
        sa.Column('scopes', sa.Text(), nullable=False),
        sa.Column('connected_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['professional_id'], ['professionals.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('professional_id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('calendar_connections')
    op.drop_column('professionals', 'working_hours')
