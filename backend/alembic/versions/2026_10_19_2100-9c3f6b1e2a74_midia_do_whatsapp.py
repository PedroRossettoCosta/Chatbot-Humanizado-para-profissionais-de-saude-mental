"""foto, áudio e documento do WhatsApp no painel

Pedido do Pedro em 19/10/2026 (opção 1): o painel mostra o que a pessoa
mandou buscando o arquivo na Meta na hora. A mensagem guarda só a
referência, nunca o arquivo.

- `messages.media_type`: image, audio ou document.
- `messages.media_id`: identificador do arquivo na Meta.
- `messages.media_mime`: tipo do arquivo informado pela Meta.
- `messages.media_filename`: nome do documento, cifrado.

Revision ID: 9c3f6b1e2a74
Revises: 4e1a7c2d9b85
Create Date: 2026-10-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c3f6b1e2a74'
down_revision: Union[str, Sequence[str], None] = '4e1a7c2d9b85'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('messages', sa.Column('media_type', sa.String(16), nullable=True))
    op.add_column('messages', sa.Column('media_id', sa.String(64), nullable=True))
    op.add_column('messages', sa.Column('media_mime', sa.String(100), nullable=True))
    # Cifrado pela aplicação (`EncryptedText`), guardado como texto.
    op.add_column('messages', sa.Column('media_filename', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('messages', 'media_filename')
    op.drop_column('messages', 'media_mime')
    op.drop_column('messages', 'media_id')
    op.drop_column('messages', 'media_type')
