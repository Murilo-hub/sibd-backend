from __future__ import annotations
"""
app/utils/file_utils.py
Utilitários para manipulação de arquivos enviados.
"""
import os
import uuid
from pathlib import Path

from fastapi import UploadFile, HTTPException, status

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def validate_upload(file: UploadFile) -> str:
    """
    Valida extensão e tamanho do arquivo.
    Retorna a extensão (sem ponto) em lowercase.
    Lança HTTPException 400 se inválido.
    """
    ext = Path(file.filename or "").suffix.lstrip(".").lower()

    if ext not in settings.allowed_extensions_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato '{ext}' não suportado. Aceitos: {settings.allowed_extensions}",
        )
    return ext


async def save_upload(file: UploadFile) -> tuple[str, str, int]:
    """
    Salva o arquivo enviado em disco com nome único (UUID).
    Retorna: (filename_salvo, caminho_completo, tamanho_bytes)
    """
    ext = validate_upload(file)
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    upload_path = Path(settings.upload_dir)
    upload_path.mkdir(parents=True, exist_ok=True)

    file_path = upload_path / unique_name

    content = await file.read()
    size_bytes = len(content)

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Arquivo muito grande. Máximo: {settings.max_upload_size_mb}MB",
        )

    with open(file_path, "wb") as f:
        f.write(content)

    logger.info("file_saved", name=unique_name, size_bytes=size_bytes)
    return unique_name, str(file_path), size_bytes


def delete_file(file_path: str) -> None:
    """Remove um arquivo do disco se existir."""
    try:
        os.remove(file_path)
        logger.info("file_deleted", path=file_path)
    except FileNotFoundError:
        logger.warning("file_not_found_on_delete", path=file_path)
