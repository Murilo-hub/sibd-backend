from __future__ import annotations
"""
app/rag/embedder.py
──────────────────────────────────────────────────────────────────────────────
Gera embeddings vetoriais usando a API do Cohere.

Modelo: embed-multilingual-v3.0
  - 1024 dimensões
  - Suporte nativo a português e outros 100+ idiomas
  - input_type diferencia documentos (indexação) de queries (busca)
    → melhora a qualidade da recuperação semântica

Limites do plano gratuito Cohere:
  - 1.000 requests/minuto
  - Sem limite diário de tokens no trial
──────────────────────────────────────────────────────────────────────────────
"""

import cohere
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Cliente Cohere instanciado uma vez (evita criar novo cliente a cada chamada)
_client: cohere.AsyncClient | None = None


def get_cohere_client() -> cohere.AsyncClient:
    """Retorna o cliente Cohere, criando-o na primeira chamada (lazy init)."""
    global _client
    if _client is None:
        _client = cohere.AsyncClient(api_key=settings.cohere_api_key)
    return _client


async def embed_documents(texts: list[str]) -> list[list[float]]:
    """
    Gera embeddings para uma lista de chunks de documento.

    Usa input_type='search_document' — indicado para textos que serão
    armazenados e recuperados posteriormente (indexação).

    Args:
        texts: lista de strings (chunks de texto)

    Returns:
        Lista de vetores float com 1024 dimensões cada.
    """
    if not texts:
        return []

    client = get_cohere_client()

    response = await client.embed(
        texts=texts,
        model=settings.cohere_embedding_model,   # embed-multilingual-v3.0
        input_type="search_document",             # para indexação de chunks
        embedding_types=["float"],                # retorna floats (não int8)
    )

    # response.embeddings.float é a lista de vetores
    embeddings = response.embeddings.float_
    logger.info("embedder_documents_done", count=len(texts))
    return embeddings   # type: ignore[return-value]


async def embed_query(query: str) -> list[float]:
    """
    Gera embedding para uma query de busca do usuário.

    Usa input_type='search_query' — otimizado para recuperação semântica
    (par query/documento treinado conjuntamente pelo Cohere).

    Args:
        query: pergunta do usuário em linguagem natural

    Returns:
        Vetor float com 1024 dimensões.
    """
    client = get_cohere_client()

    response = await client.embed(
        texts=[query],                            # sempre lista, mesmo com 1 item
        model=settings.cohere_embedding_model,
        input_type="search_query",                # para queries de busca
        embedding_types=["float"],
    )

    embedding = response.embeddings.float_[0]    # pega o primeiro (e único) vetor
    logger.info("embedder_query_done", query_len=len(query))
    return embedding   # type: ignore[return-value]