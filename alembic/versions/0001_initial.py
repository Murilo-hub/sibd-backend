"""initial

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-31

Cria todas as tabelas do sistema:
  - users
  - documents
  - chat_sessions
  - chat_messages
  - document_chunks (pgvector)
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Extensão pgvector ────────────────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── users ────────────────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id',              sa.Integer(),     nullable=False),
        sa.Column('name',            sa.String(120),   nullable=False),
        sa.Column('email',           sa.String(255),   nullable=False),
        sa.Column('hashed_password', sa.String(255),   nullable=False),
        sa.Column('is_active',       sa.Boolean(),     nullable=False, server_default=sa.text('true')),
        sa.Column('created_at',      sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at',      sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_id',    'users', ['id'],    unique=False)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # ── documents ────────────────────────────────────────────────────────────
    op.create_table(
        'documents',
        sa.Column('id',            sa.Integer(),     nullable=False),
        sa.Column('owner_id',      sa.Integer(),     nullable=False),
        sa.Column('filename',      sa.String(255),   nullable=False),
        sa.Column('original_name', sa.String(255),   nullable=False),
        sa.Column('file_path',     sa.String(512),   nullable=False),
        sa.Column('file_size',     sa.Integer(),     nullable=False),
        sa.Column('file_type',     sa.String(10),    nullable=False),
        sa.Column('empresa',       sa.String(200),   nullable=False),
        sa.Column('categoria',     sa.String(100),   nullable=False),
        sa.Column('data_documento',sa.String(20),    nullable=True),
        sa.Column('descricao',     sa.Text(),        nullable=True),
        sa.Column('status',        sa.String(20),    nullable=False, server_default=sa.text("'pending'")),
        sa.Column('chunks_count',  sa.Integer(),     nullable=False, server_default=sa.text('0')),
        sa.Column('error_message', sa.Text(),        nullable=True),
        sa.Column('created_at',    sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('indexed_at',    sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_documents_id',       'documents', ['id'],       unique=False)
    op.create_index('ix_documents_owner_id', 'documents', ['owner_id'], unique=False)
    op.create_index('ix_documents_empresa',  'documents', ['empresa'],  unique=False)
    op.create_index('ix_documents_categoria','documents', ['categoria'],unique=False)

    # ── chat_sessions ────────────────────────────────────────────────────────
    op.create_table(
        'chat_sessions',
        sa.Column('id',         sa.Integer(),   nullable=False),
        sa.Column('user_id',    sa.Integer(),   nullable=False),
        sa.Column('title',      sa.String(200), nullable=False, server_default=sa.text("'Nova consulta'")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_chat_sessions_id',      'chat_sessions', ['id'],      unique=False)
    op.create_index('ix_chat_sessions_user_id', 'chat_sessions', ['user_id'], unique=False)

    # ── chat_messages ────────────────────────────────────────────────────────
    op.create_table(
        'chat_messages',
        sa.Column('id',           sa.Integer(),  nullable=False),
        sa.Column('session_id',   sa.Integer(),  nullable=False),
        sa.Column('role',         sa.String(20), nullable=False),
        sa.Column('content',      sa.Text(),     nullable=False),
        sa.Column('sources_json', sa.JSON(),     nullable=True),
        sa.Column('created_at',   sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_chat_messages_id',         'chat_messages', ['id'],         unique=False)
    op.create_index('ix_chat_messages_session_id', 'chat_messages', ['session_id'], unique=False)

    # ── document_chunks (pgvector) ───────────────────────────────────────────
    # Criado via SQL raw pois o tipo vector não é nativo do SQLAlchemy
    op.execute("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id          TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            content     TEXT NOT NULL,
            embedding   vector(1536),
            metadata    JSONB
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_document_chunks_document_id ON document_chunks (document_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS document_chunks")
    op.drop_table('chat_messages')
    op.drop_table('chat_sessions')
    op.drop_table('documents')
    op.drop_table('users')
    op.execute("DROP EXTENSION IF EXISTS vector")