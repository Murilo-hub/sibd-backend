"""
app/db/vector_store.py
Operações de embedding usando pgvector no PostgreSQL (Supabase).
"""
from __future__ import annotations
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


async def add_documents(
    session: AsyncSession,
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict],
) -> None:
    for i, doc_id in enumerate(ids):
        await session.execute(text("""
            INSERT INTO document_chunks (id, document_id, content, embedding, metadata)
            VALUES (:id, :document_id, :content, :embedding, :metadata)
            ON CONFLICT (id) DO UPDATE
            SET content = EXCLUDED.content,
                embedding = EXCLUDED.embedding,
                metadata = EXCLUDED.metadata
        """), {
            "id": doc_id,
            "document_id": metadatas[i].get("document_id", ""),
            "content": documents[i],
            "embedding": str(embeddings[i]),
            "metadata": metadatas[i],
        })
    await session.commit()
    logger.info("pgvector_docs_added", count=len(ids))


async def query_collection(
    session: AsyncSession,
    query_embedding: list[float],
    n_results: int = 5,
    document_id: Optional[str] = None,
) -> list[dict]:
    where = "WHERE document_id = :document_id" if document_id else ""
    result = await session.execute(text(f"""
        SELECT id, document_id, content, metadata,
               1 - (embedding <=> :embedding) AS similarity
        FROM document_chunks
        {where}
        ORDER BY embedding <=> :embedding
        LIMIT :n
    """), {
        "embedding": str(query_embedding),
        "document_id": document_id,
        "n": n_results,
    })
    rows = result.fetchall()
    logger.info("pgvector_query_done", results=len(rows))
    return [
        {"id": r.id, "document_id": r.document_id,
         "content": r.content, "metadata": r.metadata,
         "similarity": r.similarity}
        for r in rows
    ]


async def delete_document_chunks(
    session: AsyncSession,
    document_id: str,
) -> None:
    await session.execute(
        text("DELETE FROM document_chunks WHERE document_id = :id"),
        {"id": document_id},
    )
    await session.commit()
    logger.info("pgvector_chunks_deleted", document_id=document_id)