from __future__ import annotations
"""
app/rag/retriever.py
──────────────────────────────────────────────────────────────────────────────
Recupera os chunks mais relevantes do pgvector para uma query do usuário.

Fluxo:
  1. Recebe a pergunta em texto
  2. Gera o embedding da query via Cohere (input_type='search_query')
  3. Busca os top_k chunks mais similares no pgvector
  4. Retorna os chunks com seus metadados para o LLM usar como contexto
──────────────────────────────────────────────────────────────────────────────
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.vector_store import search_similar_chunks
from app.rag.embedder import embed_query

logger = get_logger(__name__)


async def retrieve(
    db:           AsyncSession,
    query:        str,
    owner_id:     int,
    top_k:        int | None = None,
    document_ids: list[int] | None = None,
) -> list[dict]:
    """
    Recupera os chunks mais relevantes para a query do usuário.

    Args:
        db:           sessão assíncrona do banco
        query:        pergunta do usuário em linguagem natural
        owner_id:     ID do usuário — garante que só vê seus próprios documentos
        top_k:        número de chunks a retornar (padrão: settings.rag_top_k = 5)
        document_ids: lista de IDs para filtrar (None = todos os documentos do usuário)

    Returns:
        Lista de dicts com content, similarity e metadata de cada chunk.
    """
    k = top_k or settings.rag_top_k   # usa o padrão do config se não informado

    # gera o embedding da query (input_type='search_query' é diferente do documento)
    query_embedding = await embed_query(query)

    # busca no pgvector — filtro por document_ids se fornecido
    chunks = await search_similar_chunks(
        session=db,
        query_embedding=query_embedding,
        top_k=k,
        document_ids=document_ids,
    )

    # filtra chunks com similaridade muito baixa (< 0.3) — provavelmente irrelevantes
    # esse threshold pode ser ajustado via config se necessário
    relevant = [c for c in chunks if c["similarity"] >= 0.30]

    logger.info(
        "retriever_done",
        query_len=len(query),
        total_found=len(chunks),
        relevant=len(relevant),
        owner_id=owner_id,
    )

    return relevant


def format_context(chunks: list[dict]) -> str:
    """
    Formata os chunks recuperados em um bloco de contexto para o LLM.

    Cada chunk é precedido por seu número e metadados básicos,
    facilitando que o LLM cite a fonte corretamente na resposta.

    Args:
        chunks: lista retornada pelo retrieve()

    Returns:
        String formatada para ser inserida no prompt do sistema.
    """
    if not chunks:
        return "Nenhum documento relevante encontrado para esta consulta."

    parts = []
    for i, chunk in enumerate(chunks, start=1):
        meta     = chunk.get("metadata", {})
        doc_name = meta.get("original_name", "Documento desconhecido")
        empresa  = meta.get("empresa", "")
        categoria = meta.get("categoria", "")

        # cabeçalho do chunk com identificação da fonte
        header = f"[FONTE {i}] {doc_name}"
        if empresa:
            header += f" | {empresa}"
        if categoria:
            header += f" | {categoria}"

        parts.append(f"{header}\n{chunk['content']}")

    # separa as fontes com linha divisória
    return "\n\n---\n\n".join(parts)