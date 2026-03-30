from __future__ import annotations
"""
app/db/init_db.py
Inicializa as tabelas do banco relacional na primeira execução.
Em produção, prefira usar Alembic para migrações controladas.
"""
from app.db.database import Base, engine
from app.core.logging import get_logger

logger = get_logger(__name__)


async def init_db() -> None:
    """Cria todas as tabelas mapeadas se ainda não existirem."""
    # Importa os models para que o Base os conheça
    from app.models import user, document, chat  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_tables_created")
