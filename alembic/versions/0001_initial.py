"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Extensão pgvector ─────────────────────────────────────────────────────
    # Deve estar habilitada no Supabase em:
    # Dashboard → Database → Extensions → pesquisar "vector" → Enable
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── Tabela users ──────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id",              sa.Integer(),     primary_key=True),
        sa.Column("name",            sa.String(120),   nullable=False),
        sa.Column("email",           sa.String(255),   nullable=False),
        sa.Column("hashed_password", sa.String(255),   nullable=False),
        sa.Column("is_active",       sa.Boolean(),     server_default="true", nullable=False),
        sa.Column("created_at",      sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at",      sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── Tabela documents ──────────────────────────────────────────────────────
    op.create_table(
        "documents",
        sa.Column("id",             sa.Integer(),    primary_key=True),
        sa.Column("owner_id",       sa.Integer(),    sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename",       sa.String(255),  nullable=False),
        sa.Column("original_name",  sa.String(255),  nullable=False),
        sa.Column("file_path",      sa.String(512),  nullable=False),
        sa.Column("file_size",      sa.Integer(),    nullable=False),
        sa.Column("file_type",      sa.String(10),   nullable=False),
        sa.Column("empresa",        sa.String(200),  nullable=False),
        sa.Column("categoria",      sa.String(100),  nullable=False),
        sa.Column("data_documento", sa.String(20),   nullable=True),
        sa.Column("descricao",      sa.Text(),       nullable=True),
        sa.Column("status",         sa.String(20),   server_default="pending", nullable=False),
        sa.Column("chunks_count",   sa.Integer(),    server_default="0",       nullable=False),
        sa.Column("error_message",  sa.Text(),       nullable=True),
        sa.Column("created_at",     sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("indexed_at",     sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_documents_owner_id",  "documents", ["owner_id"])
    op.create_index("ix_documents_empresa",   "documents", ["empresa"])
    op.create_index("ix_documents_categoria", "documents", ["categoria"])

    # ── Tabela chat_sessions ──────────────────────────────────────────────────
    op.create_table(
        "chat_sessions",
        sa.Column("id",         sa.Integer(),    primary_key=True),
        sa.Column("user_id",    sa.Integer(),    sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title",      sa.String(200),  server_default="Nova consulta", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"])

    # ── Tabela chat_messages ──────────────────────────────────────────────────
    op.create_table(
        "chat_messages",
        sa.Column("id",           sa.Integer(),  primary_key=True),
        sa.Column("session_id",   sa.Integer(),  sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role",         sa.String(20), nullable=False),
        sa.Column("content",      sa.Text(),     nullable=False),
        sa.Column("sources_json", sa.JSON(),     nullable=True),
        sa.Column("created_at",   sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])

    # ── Tabela document_chunks (pgvector) ─────────────────────────────────────
    # Usa tipo nativo vector(1024) do pgvector — 1024 = dimensão do Cohere multilingual v3
    op.execute("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id          TEXT PRIMARY KEY,
            document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            content     TEXT NOT NULL,
            embedding   vector(1024),
            metadata    JSONB DEFAULT '{}'::jsonb,
            created_at  TIMESTAMPTZ DEFAULT now()
        )
    """)

    # Índice HNSW para busca vetorial rápida por similaridade de cosseno
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding
        ON document_chunks
        USING hnsw (embedding vector_cosine_ops)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_document_chunks_document_id
        ON document_chunks (document_id)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS document_chunks")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("documents")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS vector")
