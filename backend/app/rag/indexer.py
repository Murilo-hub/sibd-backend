from __future__ import annotations
"""
app/rag/indexer.py
──────────────────────────────────────────────────────────────────────────────
Orquestra o pipeline completo de indexação de um documento:

  1. Baixa o arquivo do Supabase Storage
  2. Extrai texto (PDF / DOCX / TXT)
  3. Divide em chunks com overlap
  4. Gera embeddings via Cohere (em lotes para respeitar limites da API)
  5. Salva chunks + vetores no pgvector
  6. Atualiza o status e chunks_count do documento no banco relacional

Este módulo é chamado como background task após o upload bem-sucedido.
──────────────────────────────────────────────────────────────────────────────
"""

import httpx
from datetime import datetime, timezone
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.vector_store import add_chunks, delete_document_chunks
from app.models.document import Document
from app.rag.chunker import split_text
from app.rag.embedder import embed_documents
from app.rag.extractor import extract_text

logger = get_logger(__name__)

# Cohere aceita até 96 textos por request no plano gratuito
# usamos 50 para folga e evitar timeout
EMBED_BATCH_SIZE = 50


async def index_document(
    db:          AsyncSession,
    document_id: int,
    file_url:    str,
    file_type:   str,
    metadata:    dict,
) -> None:
    """
    Executa o pipeline completo de indexação de um documento.

    Atualiza o status do documento em cada etapa:
      pending → processing → indexed (sucesso) ou error (falha)

    Args:
        db:          sessão assíncrona do banco
        document_id: ID do documento na tabela documents
        file_url:    URL do arquivo no Supabase Storage
        file_type:   extensão do arquivo (pdf, docx, txt)
        metadata:    dict com empresa, categoria, etc. para enriquecer os chunks
    """
    try:
        # ── Etapa 1: marca como "processing" ─────────────────────────────────
        await _update_status(db, document_id, "processing")
        logger.info("indexer_started", document_id=document_id, file_type=file_type)

        # ── Etapa 2: baixa o arquivo do Supabase Storage ──────────────────────
        content = await _download_file(file_url)
        if not content:
            raise ValueError("Arquivo vazio ou inacessível no storage")

        # ── Etapa 3: extrai texto conforme o tipo do arquivo ──────────────────
        text = extract_text(content, file_type)
        if not text.strip():
            raise ValueError(f"Nenhum texto extraído do arquivo {file_type}")

        # ── Etapa 4: divide em chunks com overlap ─────────────────────────────
        chunks = split_text(text, document_id)
        if not chunks:
            raise ValueError("Nenhum chunk gerado após divisão do texto")

        # ── Etapa 5: gera embeddings em lotes ────────────────────────────────
        texts      = [c.text for c in chunks]
        embeddings = await _embed_in_batches(texts)

        # ── Etapa 6: monta metadados por chunk e salva no pgvector ───────────
        # remove chunks antigos antes de re-indexar (evita duplicatas)
        await delete_document_chunks(db, document_id)

        chunk_metadatas = [
            {
                "document_id":  document_id,
                "chunk_index":  chunk.index,
                "char_start":   chunk.char_start,
                "char_end":     chunk.char_end,
                **metadata,    # empresa, categoria, original_name, etc.
            }
            for chunk in chunks
        ]

        await add_chunks(
            session=db,
            document_id=document_id,
            texts=texts,
            embeddings=embeddings,
            metadatas=chunk_metadatas,
        )

        # ── Etapa 7: atualiza status para "indexed" com contagem de chunks ────
        await _update_status(
            db, document_id, "indexed",
            chunks_count=len(chunks),
            indexed_at=datetime.now(timezone.utc),
        )

        logger.info(
            "indexer_success",
            document_id=document_id,
            chunks=len(chunks),
            chars=len(text),
        )

    except Exception as exc:
        # qualquer falha → marca como erro e registra a mensagem
        logger.error("indexer_failed", document_id=document_id, error=str(exc))
        await _update_status(db, document_id, "error", error_message=str(exc))


# ── Helpers privados ──────────────────────────────────────────────────────────

async def _download_file(file_url: str) -> bytes:
    """
    Baixa o arquivo do Supabase Storage usando o service key para autenticação.
    Timeout de 30s para evitar que arquivos grandes travem o processo.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            file_url,
            headers={"Authorization": f"Bearer {settings.supabase_service_key}"},
        )
        response.raise_for_status()   # lança exceção para status >= 400
        return response.content


async def _embed_in_batches(texts: list[str]) -> list[list[float]]:
    """
    Divide a lista de textos em lotes e chama o Cohere para cada lote.
    Necessário porque a API tem limite de textos por request.
    """
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[i : i + EMBED_BATCH_SIZE]   # fatia o lote atual
        batch_embeddings = await embed_documents(batch)
        all_embeddings.extend(batch_embeddings)
        logger.info(
            "indexer_embed_batch",
            batch=i // EMBED_BATCH_SIZE + 1,
            size=len(batch),
        )

    return all_embeddings


async def _update_status(
    db:             AsyncSession,
    document_id:    int,
    status:         str,
    chunks_count:   int = 0,
    indexed_at:     datetime | None = None,
    error_message:  str | None = None,
) -> None:
    """Atualiza os campos de status do documento no banco relacional."""
    values: dict = {"status": status}

    if chunks_count:
        values["chunks_count"] = chunks_count
    if indexed_at:
        values["indexed_at"] = indexed_at
    if error_message:
        values["error_message"] = error_message

    await db.execute(
        update(Document)
        .where(Document.id == document_id)
        .values(**values)
    )
    await db.commit()