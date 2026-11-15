"""link do Google Meet na sessão confirmada

Decisão do Pedro em 15/11/2026: quando a profissional confirma uma
sessão, a SelenIA cria um link do Google Meet no evento da agenda e o
envia à pessoa junto da mensagem de confirmação.

- `appointments.meet_link`: o link; nulo se o Google não criou.

Revision ID: d4a8c2e7f513
Revises: b7d2e4f19a36
Create Date: 2026-11-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4a8c2e7f513'
down_revision: Union[str, Sequence[str], None] = 'b7d2e4f19a36'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('appointments', sa.Column('meet_link', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('appointments', 'meet_link')
