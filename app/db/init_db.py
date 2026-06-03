from __future__ import annotations
"""
app/db/init_db.py
Verifica conexão com o banco no startup.
"""
import asyncio
from sqlalchemy import text
from app.db.database import AsyncSessionLocal
from app.core.logging import get_logger

logger = get_logger(__name__)

async def init_db() -> None:
    for attempt in range(10):
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            logger.info("database_connected")
            return
        except Exception as e:
            # Log completo do erro para diagnóstico
            logger.warning("database_retry", attempt=attempt + 1, error=str(e)[:300])
            await asyncio.sleep(4)

    logger.error("database_connection_failed")
