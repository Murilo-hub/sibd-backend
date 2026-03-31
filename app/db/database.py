from __future__ import annotations
"""
app/db/database.py
Engine assíncrono do SQLAlchemy + fábrica de sessões.
"""
from __future__ import annotations
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Adiciona SSL se a variável POSTGRES_SSL estiver habilitada ou se for production
def _build_db_url() -> str:
    url = settings.async_database_url
    if "ssl" not in url:
        url += "?ssl=require"
    return url

engine = create_async_engine(
    _build_db_url(),
    echo=settings.app_debug,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

class Base(DeclarativeBase):
    pass

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
