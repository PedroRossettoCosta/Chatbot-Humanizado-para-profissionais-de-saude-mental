"""estado inicial: profissionais, documentos, conversas e mensagens

Esta migração descreve o banco como ele existia antes do Alembic entrar
no projeto. Ela é o ponto de partida do histórico: um banco vazio roda
esta primeira e fica igual ao que já havia em desenvolvimento.

O banco de desenvolvimento, que já tinha essas tabelas, foi marcado
nesta revisão com `alembic stamp` — ou seja, o Alembic passou a
considerá-la aplicada sem executá-la de novo.

Revision ID: 51c0d73348c0
Create Date: 2026-09-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "51c0d73348c0"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "professionals",
        sa.Column("id", UUID(as_uuid=False), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("voice_tone", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_professionals_slug", "professionals", ["slug"], unique=True)

    op.create_table(
        "documents",
        sa.Column("id", UUID(as_uuid=False), nullable=False),
        sa.Column("professional_id", UUID(as_uuid=False), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["professional_id"], ["professionals.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "conversations",
        sa.Column("id", UUID(as_uuid=False), nullable=False),
        sa.Column("professional_id", UUID(as_uuid=False), nullable=False),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["professional_id"], ["professionals.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversations_session_id", "conversations", ["session_id"])

    op.create_table(
        "messages",
        sa.Column("id", UUID(as_uuid=False), nullable=False),
        sa.Column("conversation_id", UUID(as_uuid=False), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("messages")
    op.drop_index("ix_conversations_session_id", table_name="conversations")
    op.drop_table("conversations")
    op.drop_table("documents")
    op.drop_index("ix_professionals_slug", table_name="professionals")
    op.drop_table("professionals")
