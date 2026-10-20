"""conectar o WhatsApp pelo painel

- `professionals.whatsapp_pending_id`: número já cadastrado na conta da
  Meta, aguardando o código ou o registro. Só vira
  `whatsapp_phone_number_id` (e passa a receber mensagens) depois do
  registro.
- `professionals.whatsapp_setup_step`: em que passo a conexão parou
  (`code_sent` ou `verified`).
- `professionals.whatsapp_display_number` e `whatsapp_verified_name`: o
  número e o nome como a Meta mostra.
- `professionals.whatsapp_pin`: PIN de 6 dígitos da verificação em duas
  etapas do número, cifrado. É pedido de novo se o número for
  registrado outra vez.
- `whatsapp_register_attempts`: cada chamada de registro, para não passar
  do limite da Meta (10 por número em 72 horas; a 11ª bloqueia o número
  por mais 72 horas).

Revision ID: 3a7e5c1b9d42
Revises: 8b3f6a2d9c15
Create Date: 2026-10-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a7e5c1b9d42'
down_revision: Union[str, Sequence[str], None] = '8b3f6a2d9c15'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('professionals', sa.Column('whatsapp_pending_id', sa.String(32), nullable=True))
    op.add_column('professionals', sa.Column('whatsapp_setup_step', sa.String(20), nullable=True))
    op.add_column('professionals', sa.Column('whatsapp_display_number', sa.String(32), nullable=True))
    op.add_column('professionals', sa.Column('whatsapp_verified_name', sa.String(255), nullable=True))
    op.add_column('professionals', sa.Column('whatsapp_pin', sa.Text(), nullable=True))
    op.create_table(
        'whatsapp_register_attempts',
        sa.Column('id', sa.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            'professional_id',
            sa.UUID(as_uuid=False),
            sa.ForeignKey('professionals.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('phone_number_id', sa.String(32), nullable=False, index=True),
        sa.Column('ok', sa.Boolean(), nullable=False),
        sa.Column('error_code', sa.String(32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('whatsapp_register_attempts')
    for column in (
        'whatsapp_pin',
        'whatsapp_verified_name',
        'whatsapp_display_number',
        'whatsapp_setup_step',
        'whatsapp_pending_id',
    ):
        op.drop_column('professionals', column)
