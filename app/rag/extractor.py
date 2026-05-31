from __future__ import annotations
"""
app/rag/extractor.py
──────────────────────────────────────────────────────────────────────────────
Extrai texto puro de arquivos PDF, DOCX e TXT.

Cada função recebe o conteúdo bruto do arquivo (bytes) e retorna uma string
com o texto extraído, pronto para ser dividido em chunks.
──────────────────────────────────────────────────────────────────────────────
"""

import io
from app.core.logging import get_logger

logger = get_logger(__name__)


def extract_text(content: bytes, file_type: str) -> str:
    """
    Ponto de entrada único: detecta o tipo e chama o extrator correto.

    Args:
        content:   bytes do arquivo lido do storage
        file_type: extensão sem ponto em minúsculo — 'pdf', 'docx', 'doc', 'txt'

    Returns:
        Texto extraído como string; vazio se nada foi encontrado.
    """
    extractors = {
        "pdf":  _extract_pdf,
        "docx": _extract_docx,
        "doc":  _extract_docx,   # python-docx lê .doc moderno também
        "txt":  _extract_txt,
    }

    extractor = extractors.get(file_type.lower())
    if not extractor:
        # tipo não suportado — loga e retorna vazio para não quebrar o pipeline
        logger.warning("extractor_unsupported_type", file_type=file_type)
        return ""

    try:
        text = extractor(content)
        logger.info("extractor_success", file_type=file_type, chars=len(text))
        return text
    except Exception as exc:
        # falha na extração não deve derrubar o servidor
        logger.error("extractor_failed", file_type=file_type, error=str(exc))
        return ""


# ── Extratores individuais ────────────────────────────────────────────────────

def _extract_pdf(content: bytes) -> str:
    """
    Extrai texto de todas as páginas de um PDF usando pypdf.
    Páginas sem texto (ex: scaneadas sem OCR) contribuem com string vazia.
    """
    from pypdf import PdfReader   # importação local evita custo se tipo não for PDF

    reader = PdfReader(io.BytesIO(content))   # lê o PDF a partir dos bytes em memória

    pages_text = []
    for page_num, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""     # extract_text retorna None se vazia
        if page_text.strip():                     # ignora páginas completamente em branco
            pages_text.append(page_text)

    return "\n\n".join(pages_text)   # separa páginas com linha em branco dupla


def _extract_docx(content: bytes) -> str:
    """
    Extrai texto de arquivos DOCX/DOC usando python-docx.
    Cada parágrafo não vazio é incluído separado por quebra de linha.
    """
    from docx import Document   # importação local — python-docx

    doc = Document(io.BytesIO(content))   # abre o documento a partir dos bytes

    paragraphs = []
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if text:                   # ignora parágrafos vazios
            paragraphs.append(text)

    return "\n".join(paragraphs)


def _extract_txt(content: bytes) -> str:
    """
    Decodifica arquivo TXT tentando UTF-8 primeiro; fallback para latin-1.
    latin-1 aceita qualquer byte, então nunca vai falhar.
    """
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("latin-1")   # fallback seguro para arquivos legados