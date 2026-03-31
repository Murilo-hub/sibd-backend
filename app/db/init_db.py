from __future__ import annotations
"""
app/db/init_db.py
Inicializa as tabelas do banco relacional na primeira execução.
Tenta reconectar automaticamente se o banco ainda não estiver pronto.
"""
import asyncio
from app.db.database import Base, engine
from app.core.logging import get_logger

logger = get_logger(__name__)


async def init_db() -> None:
    """Cria todas as tabelas, com retry automático para esperar o PostgreSQL."""
    from app.models import user, document, chat  # noqa: F401

    for attempt in range(10):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("database_tables_created")
            return
        except Exception as e:
            wait = 3 * (attempt + 1)
            logger.info("database_not_ready", attempt=attempt + 1, wait=wait, error=str(e))
            await asyncio.sleep(wait)

    raise RuntimeError("Não foi possível conectar ao PostgreSQL após 10 tentativas.")
