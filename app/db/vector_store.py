"""
app/db/vector_store.py
Cliente ChromaDB: conexão, coleção e operações base de embedding.
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from functools import lru_cache

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@lru_cache
def get_chroma_client() -> chromadb.HttpClient:
    """
    Retorna cliente ChromaDB cacheado.
    Conecta ao servidor ChromaDB em modo HTTP (Docker).
    """
    client = chromadb.HttpClient(
        host=settings.chroma_host,
        port=settings.chroma_port,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    logger.info("chroma_connected", host=settings.chroma_host, port=settings.chroma_port)
    return client


def get_or_create_collection(client: chromadb.HttpClient | None = None):
    """
    Retorna (ou cria) a coleção principal de documentos.
    A coleção usa distância cosseno para similaridade semântica.
    """
    if client is None:
        client = get_chroma_client()

    collection = client.get_or_create_collection(
        name=settings.chroma_collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    logger.info("chroma_collection_ready", name=settings.chroma_collection_name)
    return collection


# ── Operações base ────────────────────────────────────────────────────────────

def add_documents(
    collection,
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict],
) -> None:
    """Adiciona chunks com embeddings à coleção."""
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )
    logger.info("chroma_docs_added", count=len(ids))


def query_collection(
    collection,
    query_embedding: list[float],
    n_results: int = 5,
    where: dict | None = None,
) -> dict:
    """
    Realiza busca semântica pelo embedding da consulta.
    `where` permite filtrar por metadados (ex: {"document_id": "123"}).
    """
    kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where

    return collection.query(**kwargs)


def delete_document_chunks(collection, document_id: str) -> None:
    """Remove todos os chunks de um documento pelo document_id nos metadados."""
    collection.delete(where={"document_id": document_id})
    logger.info("chroma_chunks_deleted", document_id=document_id)
