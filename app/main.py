"""
app/main.py
Ponto de entrada da aplicação FastAPI.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.db.init_db import init_db
from app.db.vector_store import get_chroma_client, get_or_create_collection

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Executado na inicialização e encerramento da aplicação.
    Inicializa banco relacional e coleção ChromaDB.
    """
    setup_logging()
    logger.info("sibd_starting", env=settings.app_env, llm=settings.llm_provider)

    # Banco relacional
    await init_db()

    # Banco vetorial
    chroma = get_chroma_client()
    get_or_create_collection(chroma)

    logger.info("sibd_ready")
    yield
    logger.info("sibd_shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="SIBD — Sistema Inteligente de Busca de Documentos",
        description="API REST para busca semântica de documentos corporativos com RAG + LLMs.",
        version="0.1.0",
        docs_url="/docs"     if settings.app_debug else None,
        redoc_url="/redoc"   if settings.app_debug else None,
        lifespan=lifespan,
    )

    # ── CORS ─────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Rotas ─────────────────────────────────────────────────────────────
    app.include_router(api_router)

    # ── Health check ──────────────────────────────────────────────────────
    @app.get("/health", tags=["health"])
    async def health():
        return {
            "status": "ok",
            "env": settings.app_env,
            "llm_provider": settings.llm_provider,
        }

    return app


app = create_app()
