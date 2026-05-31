"""
app/db/vector_store.py
Operações de embedding usando pgvector no PostgreSQL (Supabase).
"""
from __future__ import annotations
import json
from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger

logger = get_logger(__name__)


async def ensure_vector_table(session: AsyncSession) -> None:
    """Cria a tabela de embeddings se não existir."""
    await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS document_chunks (
            id          TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            content     TEXT NOT NULL,
            embedding   vector(1536),
            metadata    JSONB
        )
    """))
    await session.commit()
    logger.info("vector_table_ready")


async def add_chunks(
    session:     AsyncSession,
    document_id: int,
    texts:       list[str],
    embeddings:  list[list[float]],
    metadatas:   list[dict],
) -> None:
    """
    Insere ou atualiza chunks vetoriais no pgvector.
    Cada chunk recebe um ID composto: <document_id>_<índice>.
    """
    for i, (text_content, embedding, metadata) in enumerate(zip(texts, embeddings, metadatas)):
        chunk_id = f"{document_id}_{i}"
        await session.execute(text("""
            INSERT INTO document_chunks (id, document_id, content, embedding, metadata)
            VALUES (:id, :document_id, :content, :embedding, :metadata)
            ON CONFLICT (id) DO UPDATE
            SET content   = EXCLUDED.content,
                embedding = EXCLUDED.embedding,
                metadata  = EXCLUDED.metadata
        """), {
            "id":          chunk_id,
            "document_id": str(document_id),
            "content":     text_content,
            "embedding":   str(embedding),
            "metadata":    json.dumps(metadata),
        })
    await session.commit()
    logger.info("pgvector_chunks_added", document_id=document_id, count=len(texts))


# Mantém o nome antigo como alias para não quebrar outras partes do código
async def add_documents(
    session:    AsyncSession,
    ids:        list[str],
    embeddings: list[list[float]],
    documents:  list[str],
    metadatas:  list[dict],
) -> None:
    for i, doc_id in enumerate(ids):
        await session.execute(text("""
            INSERT INTO document_chunks (id, document_id, content, embedding, metadata)
            VALUES (:id, :document_id, :content, :embedding, :metadata)
            ON CONFLICT (id) DO UPDATE
            SET content   = EXCLUDED.content,
                embedding = EXCLUDED.embedding,
                metadata  = EXCLUDED.metadata
        """), {
            "id":          doc_id,
            "document_id": metadatas[i].get("document_id", ""),
            "content":     documents[i],
            "embedding":   str(embeddings[i]),
            "metadata":    json.dumps(metadatas[i]),
        })
    await session.commit()
    logger.info("pgvector_docs_added", count=len(ids))


async def query_collection(
    session:         AsyncSession,
    query_embedding: list[float],
    n_results:       int = 5,
    owner_id:        Optional[int] = None,
) -> list[dict]:
    where = "WHERE (metadata->>'owner_id')::int = :owner_id" if owner_id is not None else ""
    params: dict = {"embedding": str(query_embedding), "n": n_results}
    if owner_id is not None:
        params["owner_id"] = owner_id

    result = await session.execute(text(f"""
        SELECT id, document_id, content, metadata,
               1 - (embedding <=> :embedding) AS similarity
        FROM document_chunks
        {where}
        ORDER BY embedding <=> :embedding
        LIMIT :n
    """), params)
    rows = result.fetchall()
    logger.info("pgvector_query_done", results=len(rows))
    return [
        {
            "id":          r.id,
            "document_id": r.document_id,
            "content":     r.content,
            "metadata":    r.metadata or {},
            "similarity":  r.similarity,
        }
        for r in rows
    ]


async def delete_document_chunks(
    session:     AsyncSession,
    document_id: int,
) -> None:
    await session.execute(
        text("DELETE FROM document_chunks WHERE document_id = :id"),
        {"id": str(document_id)},
    )
    await session.commit()
    logger.info("pgvector_chunks_deleted", document_id=document_id)
