"""cadastro em etapas

Duração da sessão, etapa do cadastro, aceite das regras e conclusão.

Revision ID: 8e1c4a7f2d93
Revises: 5b2e8f0d4a61
Create Date: 2026-09-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8e1c4a7f2d93'
down_revision: Union[str, Sequence[str], None] = '5b2e8f0d4a61'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('professionals', sa.Column('session_minutes', sa.Integer(), nullable=True))
    op.add_column('professionals', sa.Column('onboarding_step', sa.Integer(), nullable=True))
    op.add_column('professionals', sa.Column('rules_accepted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        'professionals', sa.Column('onboarding_completed_at', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('professionals', 'onboarding_completed_at')
    op.drop_column('professionals', 'rules_accepted_at')
    op.drop_column('professionals', 'onboarding_step')
    op.drop_column('professionals', 'session_minutes')
