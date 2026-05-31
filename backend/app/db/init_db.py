from __future__ import annotations
"""
app/db/init_db.py
Inicializa as tabelas em background — nunca derruba o servidor.
"""
import asyncio
from app.db.database import Base, engine, AsyncSessionLocal
from app.db.vector_store import ensure_vector_table
from app.core.logging import get_logger

logger = get_logger(__name__)


async def _create_tables() -> None:
    from app.models import user, document, chat  # noqa: F401
    for attempt in range(20):
        try:
            # Tabelas relacionais
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("database_tables_created")

            # Tabela de embeddings (pgvector)
            async with AsyncSessionLocal() as session:
                await ensure_vector_table(session)
            logger.info("vector_table_created")

            return
        except Exception as e:
            logger.info("db_retry", attempt=attempt + 1, error=str(e)[:60])
            await asyncio.sleep(3)
    logger.info("db_gave_up")


async def init_db() -> None:
    asyncio.create_task(_create_tables())