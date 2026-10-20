"""dias especiais por cliente

Pedido do Pedro em 19/10/2026: em vez de todos os clientes com a
permissão terem os mesmos dias especiais, a profissional escolhe os dias
de cada pessoa ao ligar a permissão dela.

- `contacts.special_days`: dias da semana desta pessoa.
- `professionals.special_days` sai. Quem já tinha a permissão herda os
  dias que a profissional tinha marcado.

Revision ID: 4e1a7c2d9b85
Revises: b7d2e9a41c63
Create Date: 2026-10-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e1a7c2d9b85'
down_revision: Union[str, Sequence[str], None] = 'b7d2e9a41c63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

professionals = sa.table('professionals', sa.column('id', sa.Uuid(as_uuid=False)), sa.column('special_days', sa.JSON))
contacts = sa.table(
    'contacts',
    sa.column('professional_id', sa.Uuid(as_uuid=False)),
    sa.column('allow_special_hours', sa.Boolean),
    sa.column('special_days', sa.JSON),
)


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('contacts', sa.Column('special_days', sa.JSON(), nullable=True))
    conn = op.get_bind()
    for prof_id, days in conn.execute(sa.select(professionals.c.id, professionals.c.special_days)).fetchall():
        if days:
            conn.execute(
                contacts.update()
                .where(contacts.c.professional_id == prof_id, contacts.c.allow_special_hours.is_(True))
                .values(special_days=days)
            )
    op.drop_column('professionals', 'special_days')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('professionals', sa.Column('special_days', sa.JSON(), nullable=True))
    op.drop_column('contacts', 'special_days')
