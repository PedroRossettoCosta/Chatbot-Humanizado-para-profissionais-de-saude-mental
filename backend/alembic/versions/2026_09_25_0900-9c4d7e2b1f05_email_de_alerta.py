"""e-mail de alerta

Endereço onde cada profissional recebe os alertas por e-mail.

Revision ID: 9c4d7e2b1f05
Revises: 3e8b5f1c2a77
Create Date: 2026-09-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c4d7e2b1f05'
down_revision: Union[str, Sequence[str], None] = '3e8b5f1c2a77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('professionals', sa.Column('alert_email', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('professionals', 'alert_email')
