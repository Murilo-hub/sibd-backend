from __future__ import annotations
"""
alembic/env.py
Configuração do Alembic — usa driver SÍNCRONO (psycopg2) para migrations.
O driver assíncrono (asyncpg) é usado apenas pelo servidor FastAPI em runtime.
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.config import settings
from app.db.database import Base
from app.models.user     import User       # noqa: F401
from app.models.document import Document   # noqa: F401
from app.models.chat     import ChatSession, ChatMessage  # noqa: F401

config = context.config

# Converte a URL para psycopg2 (síncrono) — obrigatório para o Alembic
sync_url = (
    settings.async_database_url
    .replace("postgresql+asyncpg://", "postgresql://")
    .split("?")[0]   # remove ?ssl=true — psycopg2 usa sslmode no parâmetro
)
# Adiciona sslmode=require para o Supabase
sync_url += "?sslmode=require"

config.set_main_option("sqlalchemy.url", sync_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # engine_from_config usa psycopg2 síncrono — correto para Alembic
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
