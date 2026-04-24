from __future__ import annotations
"""
app/utils/file_utils.py
Upload de arquivos para o Supabase Storage.
"""
import uuid
from pathlib import Path

import httpx
from fastapi import UploadFile, HTTPException, status

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

SUPABASE_STORAGE_URL = f"{settings.supabase_url}/storage/v1/object"
BUCKET = "documents"


def validate_upload(file: UploadFile) -> str:
    ext = Path(file.filename or "").suffix.lstrip(".").lower()
    if ext not in settings.allowed_extensions_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Formato '{ext}' não suportado. Aceitos: {settings.allowed_extensions}",
        )
    return ext


async def save_upload(file: UploadFile) -> tuple[str, str, int]:
    ext = validate_upload(file)
    unique_name = f"{uuid.uuid4().hex}.{ext}"

    content = await file.read()
    size_bytes = len(content)

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Arquivo muito grande. Máximo: {settings.max_upload_size_mb}MB",
        )

    # Upload para Supabase Storage
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SUPABASE_STORAGE_URL}/{BUCKET}/{unique_name}",
            content=content,
            headers={
                "Authorization": f"Bearer {settings.supabase_service_key}",
                "Content-Type": file.content_type or "application/octet-stream",
            },
        )
        if response.status_code not in (200, 201):
            logger.error("storage_upload_failed", status=response.status_code, body=response.text)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao salvar arquivo no storage.",
            )

    file_url = f"{SUPABASE_STORAGE_URL}/{BUCKET}/{unique_name}"
    logger.info("file_uploaded", name=unique_name, size_bytes=size_bytes)
    return unique_name, file_url, size_bytes


async def delete_file(file_path: str) -> None:
    async with httpx.AsyncClient() as client:
        await client.delete(
            file_path,
            headers={"Authorization": f"Bearer {settings.supabase_service_key}"},
        )
    logger.info("file_deleted", path=file_path)