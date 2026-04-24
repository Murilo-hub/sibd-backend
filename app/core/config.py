from __future__ import annotations
"""
app/core/config.py
Configurações centrais via pydantic-settings.
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

    # ── App ───────────────────────────────────────────────────────
    app_env: Literal["development", "production"] = "production"
    app_debug: bool = False
    app_secret_key: str = ""

    # ── JWT ───────────────────────────────────────────────────────
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7

    # ── PostgreSQL individual (fallback) ──────────────────────────
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "sibd"
    postgres_user: str = "sibd_user"
    postgres_password: str = "sibd_pass"

    # ── DATABASE_URL direto (Railway injeta automaticamente) ──────
    database_url: str = ""

    @property
    def async_database_url(self) -> str:
        if self.database_url:
            url = self.database_url
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            # Garante SSL para Supabase
            if "sslmode" not in url:
                url += "?ssl=true"
            return url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    )

    # ── Supabase ──────────────────────────────────────────────────────
    supabase_url: str = ""
    supabase_service_key: str = ""

    # ── LLM ───────────────────────────────────────────────────────
    llm_provider: Literal["openai", "ollama"] = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    ollama_embedding_model: str = "nomic-embed-text"

    # ── Upload ────────────────────────────────────────────────────
    upload_dir: str = "./data/uploads"
    processed_dir: str = "./data/processed"
    max_upload_size_mb: int = 50
    allowed_extensions: str = "pdf,doc,docx,txt"

    @property
    def allowed_extensions_list(self) -> list[str]:
        return [e.strip().lower() for e in self.allowed_extensions.split(",")]

    # ── RAG ───────────────────────────────────────────────────────
    chunk_size: int = 800
    chunk_overlap: int = 100
    rag_top_k: int = 5

    # ── CORS ──────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()