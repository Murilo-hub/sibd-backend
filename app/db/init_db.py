from __future__ import annotations
"""
app/db/init_db.py
──────────────────────────────────────────────────────────────────────────────
Verifica a conexão com o banco no startup da aplicação.

As tabelas NÃO são criadas aqui — são criadas pelo Alembic (migrate.py)
antes do servidor subir. Isso é mais seguro e previsível em produção.

No Render, o Start Command deve ser:
  python migrate.py && uvicorn app.main:app --host 0.0.0.0 --port $PORT
──────────────────────────────────────────────────────────────────────────────
"""

import asyncio
from sqlalchemy import text
from app.db.database import AsyncSessionLocal
from app.core.logging import get_logger

logger = get_logger(__name__)


async def init_db() -> None:
    """
    Testa a conexão com o banco no startup.
    Tenta 10 vezes com intervalo de 3s — útil quando o banco demora para acordar
    (ex: Supabase free tier que hiberna após inatividade).
    """
    for attempt in range(10):
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))   # query mínima para testar conexão
            logger.info("database_connected")
            return
        except Exception as e:
            logger.warning("database_retry", attempt=attempt + 1, error=str(e)[:80])
            await asyncio.sleep(3)

    # Se chegou aqui, não conseguiu conectar — loga mas não derruba o servidor
    # O Render vai reiniciar automaticamente se o health check falhar
    logger.error("database_connection_failed")
