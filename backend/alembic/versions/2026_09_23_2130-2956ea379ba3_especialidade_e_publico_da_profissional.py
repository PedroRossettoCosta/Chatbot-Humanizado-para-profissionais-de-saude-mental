"""especialidade e publico da profissional

Texto livre em que cada profissional descreve a própria especialidade
e o público que atende. A triagem usa isto para separar sofrimento
comum daquele consultório de sofrimento intenso.

Revision ID: 2956ea379ba3
Revises: 4c6bc60528ba
Create Date: 2026-09-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2956ea379ba3'
down_revision: Union[str, Sequence[str], None] = '4c6bc60528ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('professionals', sa.Column('audience_description', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('professionals', 'audience_description')
