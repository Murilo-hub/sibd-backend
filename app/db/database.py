from __future__ import annotations
"""
app/db/database.py
Engine assíncrono para PostgreSQL via asyncpg.

IMPORTANTE — Supabase Transaction Pooler (porta 6543):
  O pooler não suporta prepared statements. É necessário desabilitar
  via statement_cache_size=0 nos connect_args, caso contrário o asyncpg
  lança ProgrammingError nas primeiras conexões.
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(
    settings.async_database_url,
    pool_pre_ping=True,
    echo=settings.app_debug,
    # Desabilita prepared statements — obrigatório para o Supabase pooler
    connect_args={"statement_cache_size": 0},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass

async def get_session() -> AsyncSession:  # type: ignore[return]
    async with AsyncSessionLocal() as session:
        yield session
