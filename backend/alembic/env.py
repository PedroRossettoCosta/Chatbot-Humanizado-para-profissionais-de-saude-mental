"""Configuração do Alembic para o MarIA.

Duas adaptações em relação ao arquivo padrão gerado pelo `alembic init`:

1. A URL do banco vem do `.env` (via `app.config.settings`), e não do
   `alembic.ini`. Assim existe uma única fonte de verdade e nenhuma
   senha fica versionada.
2. `target_metadata` aponta para o `Base` da aplicação, que é o que
   permite ao `alembic revision --autogenerate` comparar os modelos em
   Python com o estado real do banco.
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# Permite importar `app...` quando o Alembic roda a partir de backend/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import models  # noqa: E402,F401  (o import registra as tabelas no Base)
from app.config import settings  # noqa: E402
from app.database import Base  # noqa: E402

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Gera o SQL das migrações sem se conectar ao banco."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Aplica as migrações conectando no banco."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Detecta também mudanças de tipo de coluna, não só colunas
            # adicionadas ou removidas.
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
