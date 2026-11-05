"""avisos por e-mail guardados durante a consulta

Decisão do Pedro em 03/11/2026: com a profissional em consulta (botão
"Em consulta" ou compromisso no Google Agenda), os e-mails de pedidos
comuns ficam guardados e, quando a consulta acaba, sai um e-mail só com
o resumo. Alertas de segurança continuam saindo na hora.

- `professionals.held_notices_since`: quando o primeiro aviso foi
  guardado; nulo = nada guardado.

Revision ID: b7d2e4f19a36
Revises: 9c3f6b1e2a74
Create Date: 2026-11-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7d2e4f19a36'
down_revision: Union[str, Sequence[str], None] = '9c3f6b1e2a74'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('professionals', sa.Column('held_notices_since', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('professionals', 'held_notices_since')
