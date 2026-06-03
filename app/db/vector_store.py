from __future__ import annotations
"""
app/db/vector_store.py
──────────────────────────────────────────────────────────────────────────────
Operações de armazenamento e busca vetorial usando pgvector no PostgreSQL.

Tabela: document_chunks
  id          → identificador único do chunk (document_id + índice)
  document_id → FK para a tabela documents
  content     → texto do chunk
  embedding   → vetor de 1024 dimensões (Cohere embed-multilingual-v3.0)
  metadata    → JSON com informações extras (empresa, categoria, página...)
──────────────────────────────────────────────────────────────────────────────
"""

import json
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def ensure_vector_table(session: AsyncSession) -> None:
    """
    Cria a extensão pgvector e a tabela document_chunks se não existirem.
    Chamada uma vez na inicialização da aplicação (init_db).
    """
    # habilita a extensão pgvector — deve estar disponível no Supabase por padrão
    await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    # cria a tabela com o tipo vector(1024) — dimensão do Cohere multilingual v3
    await session.execute(text(f"""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id          TEXT PRIMARY KEY,
            document_id INTEGER NOT NULL,
            content     TEXT NOT NULL,
            embedding   vector({settings.cohere_embedding_dim}),
            metadata    JSONB DEFAULT '{{}}'::jsonb,
            created_at  TIMESTAMPTZ DEFAULT NOW()
        )
    """))

    # índice HNSW para busca aproximada rápida (muito mais eficiente que busca exata)
    # cosine distance é o operador recomendado para embeddings normalizados
    await session.execute(text("""
        CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx
        ON document_chunks
        USING hnsw (embedding vector_cosine_ops)
    """))

    await session.commit()
    logger.info("vector_table_ready")


async def add_chunks(
    session:    AsyncSession,
    document_id: int,
    texts:       list[str],
    embeddings:  list[list[float]],
    metadatas:   list[dict],
) -> None:
    """
    Insere ou atualiza os chunks de um documento no pgvector.

    Usa ON CONFLICT DO UPDATE para que re-indexar um documento
    sobrescreva os chunks anteriores sem duplicar dados.

    Args:
        session:     sessão assíncrona do SQLAlchemy
        document_id: ID do documento na tabela documents
        texts:       lista de textos dos chunks
        embeddings:  lista de vetores (mesma ordem que texts)
        metadatas:   lista de dicts com metadados de cada chunk
    """
    for i, (text_chunk, embedding, metadata) in enumerate(
        zip(texts, embeddings, metadatas)
    ):
        # ID único por chunk: "documentId_chunkIndex"
        chunk_id = f"{document_id}_{i}"

        # converte o vetor para o formato string que o pgvector aceita: [0.1,0.2,...]
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

        await session.execute(text("""
            INSERT INTO document_chunks (id, document_id, content, embedding, metadata)
            VALUES (:id, :document_id, :content, :embedding, :metadata)
            ON CONFLICT (id) DO UPDATE
                SET content   = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    metadata  = EXCLUDED.metadata
        """), {
            "id":          chunk_id,
            "document_id": int(document_id),   # garante int — asyncpg rejeita string
            "content":     text_chunk,
            "embedding":   embedding_str,
            "metadata":    json.dumps(metadata, ensure_ascii=False),
        })

    await session.commit()
    logger.info("vector_chunks_saved", document_id=document_id, count=len(texts))


async def search_similar_chunks(
    session:         AsyncSession,
    query_embedding: list[float],
    top_k:           int = 5,
    document_ids:    Optional[list[int]] = None,
) -> list[dict]:
    """
    Busca os chunks mais similares à query usando distância de cosseno.

    Args:
        session:         sessão assíncrona
        query_embedding: vetor da query (gerado pelo embedder)
        top_k:           número de chunks a retornar (padrão: 5 do config)
        document_ids:    filtrar por documentos específicos (None = todos)

    Returns:
        Lista de dicts com id, document_id, content, metadata e similarity score.
    """
    embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

    # monta filtro opcional por document_id
    if document_ids:
        where_clause = f"WHERE document_id = ANY(:doc_ids)"
        params = {
            "embedding": embedding_str,
            "top_k":     top_k,
            "doc_ids":   document_ids,
        }
    else:
        where_clause = ""
        params = {
            "embedding": embedding_str,
            "top_k":     top_k,
        }

    # <=> é o operador de distância de cosseno do pgvector
    # 1 - distância = similaridade (quanto maior, mais similar)
    result = await session.execute(text(f"""
        SELECT
            id,
            document_id,
            content,
            metadata,
            1 - (embedding <=> :embedding::vector) AS similarity
        FROM document_chunks
        {where_clause}
        ORDER BY embedding <=> :embedding::vector
        LIMIT :top_k
    """), params)

    rows = result.fetchall()
    logger.info("vector_search_done", results=len(rows))

    return [
        {
            "id":          row.id,
            "document_id": row.document_id,
            "content":     row.content,
            "metadata":    row.metadata or {},
            "similarity":  float(row.similarity),
        }
        for row in rows
    ]


async def delete_document_chunks(
    session:     AsyncSession,
    document_id: int,
) -> None:
    """
    Remove todos os chunks de um documento do pgvector.
    Chamada quando o documento é deletado via API.
    """
    await session.execute(
        text("DELETE FROM document_chunks WHERE document_id = :id"),
        {"id": int(document_id)},   # garante int — asyncpg rejeita string
    )
    await session.commit()
    logger.info("vector_chunks_deleted", document_id=document_id)
