"""pronomes da profissional

Como a MarIA fala da profissional com o paciente (feminino, masculino
ou neutro).

Revision ID: 3f9d2b6a1c47
Revises: 8e1c4a7f2d93
Create Date: 2026-09-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3f9d2b6a1c47'
down_revision: Union[str, Sequence[str], None] = '8e1c4a7f2d93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('professionals', sa.Column('pronouns', sa.String(length=20), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('professionals', 'pronouns')
