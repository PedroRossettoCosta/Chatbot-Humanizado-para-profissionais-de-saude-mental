"""mensagens não lidas no painel

Decisão do Pedro em 15/11/2026: o menu Conversas mostra quantas
mensagens do contato a profissional ainda não viu, como o menu Alertas
mostra os alertas sem revisar.

- `conversations.read_at`: até quando ela já viu a conversa no painel.
  As conversas que já existem começam como lidas, para o número não
  aparecer cheio com o histórico antigo.

Revision ID: e6b1f3a9c824
Revises: d4a8c2e7f513
Create Date: 2026-11-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6b1f3a9c824'
down_revision: Union[str, Sequence[str], None] = 'd4a8c2e7f513'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('conversations', sa.Column('read_at', sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE conversations SET read_at = now()")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('conversations', 'read_at')
