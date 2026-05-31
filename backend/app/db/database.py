from __future__ import annotations
"""
app/db/database.py
──────────────────────────────────────────────────────────────────────────────
Configura o engine SQLAlchemy assíncrono (asyncpg) e a session factory.
 
Exporta:
  - engine            → usado pelo Alembic e pelo init_db
  - AsyncSessionLocal → factory de sessões, usada internamente
  - Base              → classe base declarativa de todos os models
  - get_session       → dependência do FastAPI que abre/fecha sessão por request
──────────────────────────────────────────────────────────────────────────────
"""
 
from sqlalchemy.ext.asyncio import (
    AsyncSession,           # tipo da sessão assíncrona
    async_sessionmaker,     # factory moderna (SQLAlchemy 2.x)
    create_async_engine,    # cria o engine com driver asyncpg
)
from sqlalchemy.orm import DeclarativeBase  # base para os models ORM
 
from app.core.config import settings        # lê variáveis de ambiente
 
 
# ── Engine ────────────────────────────────────────────────────────────────────
# create_async_engine recebe a URL no formato postgresql+asyncpg://...
# pool_pre_ping=True testa a conexão antes de usá-la (evita erros após idle)
# echo=True em dev imprime o SQL gerado no terminal
engine = create_async_engine(
    settings.async_database_url,
    pool_pre_ping=True,
    echo=settings.app_debug,   # False em produção → não polui os logs
)
 
 
# ── Session factory ───────────────────────────────────────────────────────────
# expire_on_commit=False impede que os atributos sejam invalidados após commit,
# o que quebraria schemas Pydantic que leem os dados depois do commit.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
 
 
# ── Base declarativa ──────────────────────────────────────────────────────────
# Todos os models herdam de Base; o Alembic usa Base.metadata para gerar migrations.
class Base(DeclarativeBase):
    pass
 
 
# ── Dependência FastAPI ───────────────────────────────────────────────────────
async def get_session() -> AsyncSession:  # type: ignore[return]
    """
    Gerador usado via Depends() nas rotas.
    Garante que a sessão seja fechada mesmo em caso de exceção (async with).
    O commit/rollback é responsabilidade do serviço ou do middleware de transação.
    """
    async with AsyncSessionLocal() as session:
        yield session   # FastAPI injeta a sessão na rota; fecha ao sair do bloco
 