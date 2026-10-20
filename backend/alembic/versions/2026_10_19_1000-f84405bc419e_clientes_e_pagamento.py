"""clientes ativos, horários especiais, formas de pagamento e motivo do pedido

Feedback de teste de 18/10/2026 (conversa simulada pelo irmão do Pedro):

- `contacts.active_since`: desde quando a pessoa é cliente ativo (tela
  Clientes). Nulo = não é.
- `contacts.allow_special_hours`: a profissional deixou esta pessoa
  marcar nos horários especiais.
- `professionals.special_hours`: horários fora do expediente, no
  formato de `working_hours`, que só os clientes com a permissão veem.
- `professionals.payment_methods`: formas de pagamento aceitas (lista
  de chaves de `guidelines.PAYMENT_METHODS`).
- `conversations.awaiting_reason`: por que a conversa está "Aguardando
  você" (pediu a profissional, horário especial, pagamento...).

Revision ID: f84405bc419e
Revises: 3a7e5c1b9d42
Create Date: 2026-10-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f84405bc419e'
down_revision: Union[str, Sequence[str], None] = '3a7e5c1b9d42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('contacts', sa.Column('active_since', sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        'contacts',
        sa.Column('allow_special_hours', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )
    op.add_column('professionals', sa.Column('special_hours', sa.JSON(), nullable=True))
    op.add_column('professionals', sa.Column('payment_methods', sa.JSON(), nullable=True))
    op.add_column('conversations', sa.Column('awaiting_reason', sa.String(30), nullable=True))
    # Conversas que já estavam aguardando só podiam ter vindo de um
    # pedido para falar com a profissional ou de uma recusa do bot; a
    # recusa sempre tem alerta, então o padrão é o pedido simples.
    op.execute(
        "UPDATE conversations SET awaiting_reason = 'falar_com_profissional' "
        "WHERE awaiting_reply_since IS NOT NULL"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('conversations', 'awaiting_reason')
    op.drop_column('professionals', 'payment_methods')
    op.drop_column('professionals', 'special_hours')
    op.drop_column('contacts', 'allow_special_hours')
    op.drop_column('contacts', 'active_since')
