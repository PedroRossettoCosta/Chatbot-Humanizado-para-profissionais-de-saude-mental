"""perfil de voz da profissional

Campos que a profissional preenche no painel para calibrar a MarIA:
atendimento e valores, respostas boas e ruins às três perguntas fixas
e itens extras de "nunca dizer".

Revision ID: 7a1d2e9c4b10
Revises: 2956ea379ba3
Create Date: 2026-09-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a1d2e9c4b10'
down_revision: Union[str, Sequence[str], None] = '2956ea379ba3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('professionals', sa.Column('service_info', sa.Text(), nullable=True))
    op.add_column('professionals', sa.Column('voice_examples', sa.JSON(), nullable=True))
    op.add_column('professionals', sa.Column('extra_never_say', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('professionals', 'extra_never_say')
    op.drop_column('professionals', 'voice_examples')
    op.drop_column('professionals', 'service_info')
