from __future__ import annotations
"""
app/core/config.py
──────────────────────────────────────────────────────────────────────────────
Configurações centrais da aplicação via pydantic-settings.
Lê variáveis de ambiente do arquivo .env (ou do ambiente do sistema).
 
Uso:
    from app.core.config import settings
    print(settings.database_url)
──────────────────────────────────────────────────────────────────────────────
"""
 
from functools import lru_cache
from typing import Literal
 
from pydantic_settings import BaseSettings, SettingsConfigDict
 
 
class Settings(BaseSettings):
    # pydantic-settings lê automaticamente o .env e as variáveis de ambiente
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,   # DATABASE_URL == database_url
        extra="ignore",         # ignora variáveis desconhecidas no .env
    )
 
    # ── Aplicação ─────────────────────────────────────────────────────────────
    app_env:        Literal["development", "production"] = "production"
    app_debug:      bool = False          # True → SQL no terminal + docs Swagger
    app_secret_key: str  = ""            # chave geral da app (cookies, etc.)
 
    # ── JWT ───────────────────────────────────────────────────────────────────
    jwt_secret_key:                    str = ""       # DEVE ser definida em produção
    jwt_algorithm:                     str = "HS256"
    jwt_access_token_expire_minutes:   int = 60       # 1 hora
    jwt_refresh_token_expire_days:     int = 7        # 7 dias
 
    # ── PostgreSQL (fallback sem DATABASE_URL) ────────────────────────────────
    postgres_host:     str = "localhost"
    postgres_port:     int = 5432
    postgres_db:       str = "sibd"
    postgres_user:     str = "sibd_user"
    postgres_password: str = "sibd_pass"
 
    # ── DATABASE_URL completa (Render/Railway/Supabase injetam automaticamente)─
    database_url: str = ""
 
    @property
    def async_database_url(self) -> str:
        """
        Retorna a URL no formato postgresql+asyncpg://... exigido pelo asyncpg.
        Supabase exige SSL; adiciona ?ssl=true se não estiver presente.
        """
        if self.database_url:
            url = self.database_url
            # normaliza prefixo para o driver asyncpg
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            # Supabase exige SSL obrigatoriamente
            if "sslmode" not in url and "ssl=" not in url:
                url += "?ssl=true"
            return url
        # fallback: monta a URL a partir das variáveis individuais (dev local)
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
 
    # ── Supabase Storage ──────────────────────────────────────────────────────
    supabase_url:         str = ""   # ex: https://xyzxyz.supabase.co
    supabase_service_key: str = ""   # service_role key (nunca expor no frontend)
 
    # ── LLM ───────────────────────────────────────────────────────────────────
    llm_provider: Literal["openai", "ollama"] = "openai"
 
    # OpenAI
    openai_api_key:         str = ""
    openai_model:           str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"
 
    # Ollama (alternativa local, sem custo)
    ollama_base_url:         str = "http://localhost:11434"
    ollama_model:            str = "llama3.2"
    ollama_embedding_model:  str = "nomic-embed-text"
 
    # ── Upload de arquivos ────────────────────────────────────────────────────
    upload_dir:           str = "./data/uploads"
    processed_dir:        str = "./data/processed"
    max_upload_size_mb:   int = 50
    allowed_extensions:   str = "pdf,doc,docx,txt"
 
    @property
    def allowed_extensions_list(self) -> list[str]:
        """Retorna a lista de extensões permitidas sem espaços e em minúsculo."""
        return [e.strip().lower() for e in self.allowed_extensions.split(",")]
 
    # ── RAG ───────────────────────────────────────────────────────────────────
    chunk_size:    int = 800    # tamanho de cada chunk em caracteres
    chunk_overlap: int = 100    # sobreposição entre chunks consecutivos
    rag_top_k:     int = 5      # quantos chunks recuperar por query
 
    # ── CORS ──────────────────────────────────────────────────────────────────
    # Em produção: "https://seu-app.netlify.app"
    # Múltiplas origens separadas por vírgula
    cors_origins: str = "http://localhost:5173"
 
    @property
    def cors_origins_list(self) -> list[str]:
        """Retorna a lista de origens CORS permitidas."""
        return [o.strip() for o in self.cors_origins.split(",")]
 
 
@lru_cache   # instancia Settings uma única vez durante o ciclo de vida da app
def get_settings() -> Settings:
    return Settings()
 
 
# Instância global — importe apenas `settings` nos outros módulos
settings = get_settings()
 