"""regra que disparou o alerta

Guarda em cada alerta qual camada e regra da triagem o disparou
(ex.: "camada1:suicidio"), para auditoria e para medir falsos
positivos com a Marília.

Revision ID: 4c6bc60528ba
Revises: b9cf8e4c8d38
Create Date: 2026-09-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4c6bc60528ba'
down_revision: Union[str, Sequence[str], None] = 'b9cf8e4c8d38'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('safety_alerts', sa.Column('trigger', sa.String(length=64), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('safety_alerts', 'trigger')
