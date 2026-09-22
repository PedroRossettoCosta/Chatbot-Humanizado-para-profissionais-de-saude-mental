"""contatos, alertas de seguranca, agendamentos e estado da conversa

Reestrutura o modelo para suportar múltiplos canais, a triagem de
segurança e o pré-agendamento:

- `contacts`: quem fala com o bot, identificado por canal
- `safety_alerts` + `safety_alert_events`: alertas imutáveis com
  trilha de auditoria
- `appointments`: pré-agendamentos espelhados no Google Calendar
- `conversations` ganha contato, estado e marcação de atenção, e perde
  o `session_id` (que virou o identificador do contato no simulador)
- datas passam a ter fuso horário explícito (UTC)

Este arquivo foi gerado por `--autogenerate` e depois ajustado à mão em
quatro pontos que o autogenerate não resolve sozinho: o import de
`EncryptedText`, as colunas obrigatórias em tabelas que já têm dados, o
nome da chave estrangeira e a migração dos dados existentes.

Revision ID: b9cf8e4c8d38
Revises: 51c0d73348c0
Create Date: 2026-09-22
"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.models import EncryptedText
from app.services import crypto

revision: str = "b9cf8e4c8d38"
down_revision: Union[str, Sequence[str], None] = "51c0d73348c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FK_CONVERSA_CONTATO = "fk_conversations_contact_id"


def upgrade() -> None:
    # --- 1. Datas ganham fuso horário -------------------------------------
    # Os valores gravados até aqui eram UTC sem fuso declarado. O
    # `postgresql_using` diz isso explicitamente ao Postgres; sem ele, a
    # conversão assumiria o fuso do servidor e deslocaria os horários.
    for tabela, coluna in [
        ("professionals", "created_at"),
        ("documents", "uploaded_at"),
        ("conversations", "created_at"),
        ("messages", "created_at"),
    ]:
        op.alter_column(
            tabela,
            coluna,
            existing_type=postgresql.TIMESTAMP(),
            type_=sa.DateTime(timezone=True),
            existing_nullable=True,
            postgresql_using=f"{coluna} AT TIME ZONE 'UTC'",
        )

    # --- 2. Tabelas novas --------------------------------------------------
    op.create_table(
        "contacts",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("professional_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("external_id", EncryptedText(), nullable=False),
        sa.Column("external_id_index", sa.String(length=64), nullable=False),
        sa.Column("display_name", EncryptedText(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["professional_id"], ["professionals.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "professional_id", "channel", "external_id_index", name="uq_contact_por_canal"
        ),
    )
    op.create_index("ix_contacts_external_id_index", "contacts", ["external_id_index"])
    op.create_index("ix_contacts_professional_id", "contacts", ["professional_id"])

    op.create_table(
        "safety_alerts",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("professional_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("conversation_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("message_id", sa.UUID(as_uuid=False), nullable=True),
        sa.Column("level", sa.String(length=30), nullable=False),
        sa.Column("excerpt", EncryptedText(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["professional_id"], ["professionals.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_alerta_profissional_data", "safety_alerts", ["professional_id", "created_at"]
    )
    op.create_index("ix_safety_alerts_conversation_id", "safety_alerts", ["conversation_id"])

    op.create_table(
        "safety_alert_events",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("alert_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("event_type", sa.String(length=20), nullable=False),
        sa.Column("actor", sa.String(length=64), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["alert_id"], ["safety_alerts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_safety_alert_events_alert_id", "safety_alert_events", ["alert_id"])

    op.create_table(
        "appointments",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("professional_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("conversation_id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column("calendar_id", sa.String(length=255), nullable=True),
        sa.Column("calendar_event_id", sa.String(length=255), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["professional_id"], ["professionals.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_appointments_professional_id", "appointments", ["professional_id"])

    # --- 3. Colunas novas em conversations --------------------------------
    # As obrigatórias entram com valor padrão no banco, senão as linhas que
    # já existem ficariam com nulo e a restrição falharia. O padrão é
    # removido logo em seguida, para o banco continuar igual ao modelo.
    op.add_column("conversations", sa.Column("contact_id", sa.UUID(as_uuid=False), nullable=True))
    op.add_column(
        "conversations",
        sa.Column("state", sa.String(length=20), nullable=False, server_default="active"),
    )
    op.add_column(
        "conversations",
        sa.Column("needs_attention", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "conversations",
        sa.Column("contact_type", sa.String(length=20), nullable=False, server_default="lead"),
    )
    op.add_column(
        "conversations", sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.alter_column("conversations", "state", server_default=None)
    op.alter_column("conversations", "needs_attention", server_default=None)
    op.alter_column("conversations", "contact_type", server_default=None)

    # --- 4. Migração dos dados existentes ---------------------------------
    # Cada conversa antiga tinha um `session_id` e nenhum contato. Aqui
    # esse identificador vira um contato do canal simulador, cifrado e
    # indexado como qualquer outro.
    conn = op.get_bind()
    conversas = conn.execute(
        sa.text("SELECT id, professional_id, session_id FROM conversations")
    ).fetchall()

    for conversa in conversas:
        contato_id = str(uuid.uuid4())
        conn.execute(
            sa.text(
                "INSERT INTO contacts "
                "(id, professional_id, channel, external_id, external_id_index, created_at) "
                "VALUES (:id, :prof, 'simulator', :ext, :idx, now())"
            ),
            {
                "id": contato_id,
                "prof": conversa.professional_id,
                "ext": crypto.encrypt(conversa.session_id),
                "idx": crypto.blind_index(conversa.session_id),
            },
        )
        conn.execute(
            sa.text("UPDATE conversations SET contact_id = :contato WHERE id = :id"),
            {"contato": contato_id, "id": conversa.id},
        )

    # A política de retenção passou a usar a última atividade; sem este
    # preenchimento, as conversas antigas ficariam com nulo e nunca seriam
    # alcançadas pela limpeza.
    op.execute(
        """
        UPDATE conversations c
        SET last_message_at = COALESCE(
            (SELECT MAX(m.created_at) FROM messages m WHERE m.conversation_id = c.id),
            c.created_at,
            now()
        )
        """
    )

    # --- 5. Agora que todas as linhas têm contato, a coluna vira obrigatória
    op.alter_column("conversations", "contact_id", nullable=False)
    op.create_foreign_key(
        FK_CONVERSA_CONTATO, "conversations", "contacts", ["contact_id"], ["id"]
    )
    op.create_index("ix_conversations_contact_id", "conversations", ["contact_id"])
    op.create_index("ix_conversations_professional_id", "conversations", ["professional_id"])

    op.drop_index("ix_conversations_session_id", table_name="conversations")
    op.drop_column("conversations", "session_id")

    # --- 6. Colunas novas em messages e professionals ---------------------
    op.add_column("messages", sa.Column("sent_by", sa.String(length=20), nullable=True))
    op.add_column("messages", sa.Column("external_id", sa.String(length=128), nullable=True))
    op.create_unique_constraint("uq_message_external_id", "messages", ["external_id"])

    # Ordem de inserção garantida pelo banco. O horário não serve para
    # ordenar: o relógio do sistema tem resolução de milissegundos, então
    # mensagens seguidas podem empatar e o histórico ficaria embaralhado.
    op.add_column("messages", sa.Column("seq", sa.BigInteger(), nullable=True))
    # As mensagens que já existem recebem a sequência na ordem cronológica.
    op.execute(
        """
        UPDATE messages m
        SET seq = ordenadas.posicao
        FROM (
            SELECT id, row_number() OVER (ORDER BY created_at, id) AS posicao
            FROM messages
        ) AS ordenadas
        WHERE m.id = ordenadas.id
        """
    )
    op.alter_column("messages", "seq", nullable=False)
    op.execute("ALTER TABLE messages ALTER COLUMN seq ADD GENERATED BY DEFAULT AS IDENTITY")
    # A sequência precisa continuar de onde o preenchimento parou.
    op.execute(
        "SELECT setval(pg_get_serial_sequence('messages', 'seq'), "
        "(SELECT COALESCE(MAX(seq), 0) + 1 FROM messages), false)"
    )
    op.create_unique_constraint("uq_message_seq", "messages", ["seq"])
    op.create_index("ix_message_conversa_seq", "messages", ["conversation_id", "seq"])

    op.add_column("professionals", sa.Column("calendar_id", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("professionals", "calendar_id")

    op.drop_index("ix_message_conversa_seq", table_name="messages")
    op.drop_constraint("uq_message_seq", "messages", type_="unique")
    op.drop_column("messages", "seq")
    op.drop_constraint("uq_message_external_id", "messages", type_="unique")
    op.drop_column("messages", "external_id")
    op.drop_column("messages", "sent_by")

    # Recria o `session_id` a partir do identificador do contato, para que
    # desfazer a migração não perca a ligação das conversas antigas.
    op.add_column(
        "conversations", sa.Column("session_id", sa.VARCHAR(length=128), nullable=True)
    )
    conn = op.get_bind()
    vinculos = conn.execute(
        sa.text(
            "SELECT c.id AS conversa_id, ct.external_id AS externo "
            "FROM conversations c JOIN contacts ct ON ct.id = c.contact_id"
        )
    ).fetchall()
    for vinculo in vinculos:
        conn.execute(
            sa.text("UPDATE conversations SET session_id = :sessao WHERE id = :id"),
            {"sessao": crypto.decrypt(vinculo.externo), "id": vinculo.conversa_id},
        )
    op.execute("UPDATE conversations SET session_id = id::text WHERE session_id IS NULL")
    op.alter_column("conversations", "session_id", nullable=False)
    op.create_index("ix_conversations_session_id", "conversations", ["session_id"])

    op.drop_constraint(FK_CONVERSA_CONTATO, "conversations", type_="foreignkey")
    op.drop_index("ix_conversations_professional_id", table_name="conversations")
    op.drop_index("ix_conversations_contact_id", table_name="conversations")
    op.drop_column("conversations", "last_message_at")
    op.drop_column("conversations", "contact_type")
    op.drop_column("conversations", "needs_attention")
    op.drop_column("conversations", "state")
    op.drop_column("conversations", "contact_id")

    op.drop_index("ix_appointments_professional_id", table_name="appointments")
    op.drop_table("appointments")
    op.drop_index("ix_safety_alert_events_alert_id", table_name="safety_alert_events")
    op.drop_table("safety_alert_events")
    op.drop_index("ix_safety_alerts_conversation_id", table_name="safety_alerts")
    op.drop_index("ix_alerta_profissional_data", table_name="safety_alerts")
    op.drop_table("safety_alerts")
    op.drop_index("ix_contacts_professional_id", table_name="contacts")
    op.drop_index("ix_contacts_external_id_index", table_name="contacts")
    op.drop_table("contacts")

    for tabela, coluna in [
        ("messages", "created_at"),
        ("conversations", "created_at"),
        ("documents", "uploaded_at"),
        ("professionals", "created_at"),
    ]:
        op.alter_column(
            tabela,
            coluna,
            existing_type=sa.DateTime(timezone=True),
            type_=postgresql.TIMESTAMP(),
            existing_nullable=True,
        )
