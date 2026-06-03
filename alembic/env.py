from __future__ import annotations
"""
alembic/env.py
──────────────────────────────────────────────────────────────────────────────
Configuração do Alembic para migrações assíncronas com asyncpg.

Para gerar uma nova migration:
  alembic revision --autogenerate -m "descricao"

Para aplicar no banco:
  alembic upgrade head
──────────────────────────────────────────────────────────────────────────────
"""

import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Garante que o pacote app está no path mesmo rodando de fora do diretório
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.config import settings
from app.db.database import Base

# Importa todos os models para que o Base.metadata os conheça
# sem isso o autogenerate não detecta as tabelas
from app.models.user     import User       # noqa: F401
from app.models.document import Document   # noqa: F401
from app.models.chat     import ChatSession, ChatMessage  # noqa: F401

config = context.config

# Sobrescreve a URL com a do settings — ignora o placeholder do alembic.ini
# Usa a URL síncrona (psycopg2) que o Alembic exige internamente
sync_url = settings.async_database_url.replace(
    "postgresql+asyncpg://", "postgresql+psycopg2://"
)
config.set_main_option("sqlalchemy.url", sync_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata   # aponta para os models importados acima


def run_migrations_offline() -> None:
    """Gera SQL sem conectar ao banco — útil para revisar antes de aplicar."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Roda as migrations com conexão assíncrona (asyncpg)."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,   # sem pool — cada migration abre e fecha conexão
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
