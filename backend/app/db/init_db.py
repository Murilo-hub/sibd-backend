from __future__ import annotations
"""
app/db/init_db.py
Inicializa as tabelas em background — nunca derruba o servidor.
"""
import asyncio
from app.db.database import Base, engine
from app.core.logging import get_logger

logger = get_logger(__name__)


async def _create_tables() -> None:
    from app.models import user, document, chat  # noqa: F401
    for attempt in range(20):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("database_tables_created")
            return
        except Exception as e:
            logger.info("db_retry", attempt=attempt + 1, error=str(e)[:60])
            await asyncio.sleep(3)
    logger.info("db_gave_up")


async def init_db_background() -> None:
    asyncio.create_task(_create_tables())
