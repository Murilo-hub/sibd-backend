"""
app/db/vector_store.py
Cliente ChromaDB: conexão, coleção e operações base de embedding.
"""
from __future__ import annotations
from typing import Optional
from functools import lru_cache

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@lru_cache
def get_chroma_client():
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        logger.info("chroma_connected", host=settings.chroma_host, port=settings.chroma_port)
        return client
    except Exception as e:
        logger.warning("chroma_unavailable", error=str(e))
        return None


def get_or_create_collection(client: Optional[object] = None):
    if client is None:
        client = get_chroma_client()
    if client is None:
        logger.warning("chroma_collection_skipped")
        return None
    try:
        collection = client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("chroma_collection_ready", name=settings.chroma_collection_name)
        return collection
    except Exception as e:
        logger.warning("chroma_collection_error", error=str(e))
        return None


def add_documents(collection, ids, embeddings, documents, metadatas) -> None:
    if collection is None:
        return
    collection.add(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
    logger.info("chroma_docs_added", count=len(ids))


def query_collection(collection, query_embedding, n_results: int = 5, where: Optional[dict] = None) -> Optional[dict]:
    if collection is None:
        return None
    kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where
    return collection.query(**kwargs)


def delete_document_chunks(collection, document_id: str) -> None:
    if collection is None:
        return
    collection.delete(where={"document_id": document_id})
    logger.info("chroma_chunks_deleted", document_id=document_id)
