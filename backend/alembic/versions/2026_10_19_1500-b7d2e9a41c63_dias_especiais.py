"""dias especiais no lugar dos horários especiais

Pedido do Pedro em 19/10/2026: em vez de a profissional montar
intervalos fora do expediente, ela marca dias da semana, e nesses dias
os clientes com a permissão podem marcar em qualquer horário livre.

- `professionals.special_days`: lista de dias da semana (ex.:
  ["tue", "sat"]).
- `professionals.special_hours` sai. Quem tinha algum intervalo num dia
  passa a ter esse dia como dia especial.

Revision ID: b7d2e9a41c63
Revises: f84405bc419e
Create Date: 2026-10-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7d2e9a41c63'
down_revision: Union[str, Sequence[str], None] = 'f84405bc419e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

professionals = sa.table(
    'professionals',
    sa.column('id', sa.Uuid(as_uuid=False)),
    sa.column('special_hours', sa.JSON),
    sa.column('special_days', sa.JSON),
)


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('professionals', sa.Column('special_days', sa.JSON(), nullable=True))
    conn = op.get_bind()
    rows = conn.execute(sa.select(professionals.c.id, professionals.c.special_hours)).fetchall()
    for row_id, hours in rows:
        days = [day for day in WEEKDAYS if (hours or {}).get(day)]
        if days:
            conn.execute(professionals.update().where(professionals.c.id == row_id).values(special_days=days))
    op.drop_column('professionals', 'special_hours')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('professionals', sa.Column('special_hours', sa.JSON(), nullable=True))
    conn = op.get_bind()
    rows = conn.execute(sa.select(professionals.c.id, professionals.c.special_days)).fetchall()
    for row_id, days in rows:
        if days:
            hours = {day: [{"start": "00:00", "end": "23:59"}] for day in days}
            conn.execute(professionals.update().where(professionals.c.id == row_id).values(special_hours=hours))
    op.drop_column('professionals', 'special_days')
