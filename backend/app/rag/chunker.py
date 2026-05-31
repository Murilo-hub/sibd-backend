from __future__ import annotations
"""
app/rag/chunker.py
──────────────────────────────────────────────────────────────────────────────
Divide texto extraído em chunks menores com overlap.

Por que overlap?
  Garante que frases no limite entre dois chunks não percam contexto.
  Ex: chunk_size=800, overlap=100 → os últimos 100 chars do chunk N
  são os primeiros 100 chars do chunk N+1.
──────────────────────────────────────────────────────────────────────────────
"""

from dataclasses import dataclass
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Chunk:
    """Representa um pedaço de texto com sua posição no documento original."""
    index:      int   # posição do chunk dentro do documento (0, 1, 2...)
    text:       str   # conteúdo do chunk
    char_start: int   # posição de início no texto original
    char_end:   int   # posição de fim no texto original


def split_text(text: str, document_id: int) -> list[Chunk]:
    """
    Divide o texto em chunks de tamanho fixo com overlap.

    Usa os valores de chunk_size e chunk_overlap definidos no config.py,
    que podem ser ajustados via variáveis de ambiente sem mudar o código.

    Args:
        text:        texto completo extraído do documento
        document_id: ID do documento no banco (usado apenas para logging)

    Returns:
        Lista de Chunk ordenada por posição no texto.
    """
    chunk_size    = settings.chunk_size      # padrão: 800 caracteres
    chunk_overlap = settings.chunk_overlap   # padrão: 100 caracteres
    step          = chunk_size - chunk_overlap   # avanço entre chunks consecutivos

    if not text.strip():
        logger.warning("chunker_empty_text", document_id=document_id)
        return []

    chunks: list[Chunk] = []
    start = 0
    index = 0

    while start < len(text):
        end        = min(start + chunk_size, len(text))   # não ultrapassa o fim
        chunk_text = text[start:end].strip()

        if chunk_text:   # ignora chunks vazios após strip
            chunks.append(Chunk(
                index=index,
                text=chunk_text,
                char_start=start,
                char_end=end,
            ))
            index += 1

        if end == len(text):
            break        # chegou ao fim do texto

        start += step    # avança respeitando o overlap

    logger.info(
        "chunker_done",
        document_id=document_id,
        total_chars=len(text),
        total_chunks=len(chunks),
        chunk_size=chunk_size,
        overlap=chunk_overlap,
    )
    return chunks