from __future__ import annotations
"""
app/main.py
──────────────────────────────────────────────────────────────────────────────
Ponto de entrada da aplicação FastAPI.
Configura middlewares, rotas e lifecycle (startup/shutdown).
──────────────────────────────────────────────────────────────────────────────
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.db.init_db import init_db

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Executado na inicialização (antes do yield) e no shutdown (após o yield)."""
    setup_logging()
    logger.info("sibd_starting", env=settings.app_env)

    # Cria tabelas e extensão pgvector se ainda não existirem
    await init_db()

    logger.info("sibd_ready")
    yield
    logger.info("sibd_shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="SIBD — Sistema Inteligente de Busca de Documentos",
        description="API REST para busca semântica de documentos corporativos com RAG.",
        version="0.1.0",
        # Swagger/ReDoc só ficam ativos em desenvolvimento
        docs_url="/docs"  if settings.app_debug else None,
        redoc_url="/redoc" if settings.app_debug else None,
        lifespan=lifespan,
    )

    # ── CORS ─────────────────────────────────────────────────────────────────
    # Em produção, cors_origins_list deve conter apenas o domínio do Netlify
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Rotas da API ──────────────────────────────────────────────────────────
    app.include_router(api_router)   # prefixo /api (auth, documents, chat)

    # ── Rota raiz — exigida pelo Render para health check ─────────────────────
    # O Render faz GET / periodicamente; sem essa rota retorna 404
    # e o serviço é marcado como unhealthy e reiniciado.
    @app.get("/", tags=["health"], include_in_schema=False)
    async def root():
        return {"status": "ok"}

    # ── Rota de health detalhada — útil para monitoramento externo ────────────
    @app.get("/health", tags=["health"])
    async def health():
        return {
            "status": "ok",
            "env":    settings.app_env,
        }

    return app


# Instância usada pelo uvicorn: uvicorn app.main:app
app = create_app()
