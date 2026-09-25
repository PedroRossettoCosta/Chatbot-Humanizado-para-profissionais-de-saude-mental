"""botão em consulta

Quando ligado, a MarIA avisa a quem pedir para falar com a profissional
que ela está em atendimento, e oferece ajuda enquanto isso.

Revision ID: 3e8b5f1c2a77
Revises: 7a1d2e9c4b10
Create Date: 2026-09-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3e8b5f1c2a77'
down_revision: Union[str, Sequence[str], None] = '7a1d2e9c4b10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('professionals', sa.Column('in_session_since', sa.DateTime(timezone=True), nullable=True))
    op.add_column('professionals', sa.Column('in_session_until', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('professionals', 'in_session_until')
    op.drop_column('professionals', 'in_session_since')
