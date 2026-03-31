from __future__ import annotations
"""
app/core/config.py
Configurações centrais da aplicação via pydantic-settings.
Lê automaticamente do arquivo .env.
"""
from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────
    app_env: Literal["development", "production"] = "development"
    app_debug: bool = True
    app_secret_key: str = "changeme"

    # ── JWT ───────────────────────────────────────────────────────────────
    jwt_secret_key: str = "changeme-jwt"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7

    # ── PostgreSQL ────────────────────────────────────────────────────────
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "sibd"
    postgres_user: str = "sibd_user"
    postgres_password: str = "sibd_pass"

    @property
    def database_url(self) -> str:
        """URL síncrona (usada pelo Alembic)."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def async_database_url(self) -> str:
        """URL assíncrona (usada pelo SQLAlchemy + asyncpg)."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ── ChromaDB ─────────────────────────────────────────────────────────
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_collection_name: str = "sibd_documents"

    # ── LLM toggle ───────────────────────────────────────────────────────
    llm_provider: Literal["openai", "ollama"] = "openai"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_embedding_model: str = "nomic-embed-text"

    # ── Upload ────────────────────────────────────────────────────────────
    upload_dir: str = "./data/uploads"
    processed_dir: str = "./data/processed"
    max_upload_size_mb: int = 50
    allowed_extensions: str = "pdf,doc,docx,txt"

    @property
    def allowed_extensions_list(self) -> list[str]:
        return [ext.strip().lower() for ext in self.allowed_extensions.split(",")]

    # ── RAG ──────────────────────────────────────────────────────────────
    chunk_size: int = 800
    chunk_overlap: int = 100
    rag_top_k: int = 5

    # ── CORS ─────────────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Retorna instância cacheada das configurações."""
    return Settings()


settings = get_settings()
