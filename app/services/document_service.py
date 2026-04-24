from __future__ import annotations
"""
app/services/document_service.py
Regras de negócio para upload e gerenciamento de documentos.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status, UploadFile

from app.models.document import Document
from app.schemas.document import DocumentMetadata, DocumentResponse, DocumentListResponse
from app.utils.file_utils import save_upload, delete_file
from app.core.logging import get_logger

logger = get_logger(__name__)


async def upload_document(
    db: AsyncSession,
    file: UploadFile,
    metadata: DocumentMetadata,
    owner_id: int,
) -> DocumentResponse:
    # Salva no Supabase Storage
    filename, file_url, file_size = await save_upload(file)
    ext = filename.rsplit(".", 1)[-1]

    # Cria registro no banco
    document = Document(
        owner_id=owner_id,
        filename=filename,
        original_name=file.filename or filename,
        file_path=file_url,
        file_size=file_size,
        file_type=ext,
        empresa=metadata.empresa,
        categoria=metadata.categoria,
        data_documento=metadata.data_documento,
        descricao=metadata.descricao,
        status="pending",
    )
    db.add(document)
    await db.flush()
    await db.refresh(document)

    logger.info("document_uploaded", document_id=document.id, owner_id=owner_id)
    return DocumentResponse.model_validate(document)


async def list_documents(
    db: AsyncSession,
    owner_id: int,
    page: int = 1,
    limit: int = 20,
) -> DocumentListResponse:
    offset = (page - 1) * limit
    result = await db.execute(
        select(Document)
        .where(Document.owner_id == owner_id)
        .order_by(Document.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    documents = result.scalars().all()

    total_result = await db.execute(
        select(Document).where(Document.owner_id == owner_id)
    )
    total = len(total_result.scalars().all())

    return DocumentListResponse(
        items=[DocumentResponse.model_validate(d) for d in documents],
        total=total,
        page=page,
        limit=limit,
    )


async def get_document(
    db: AsyncSession,
    document_id: int,
    owner_id: int,
) -> DocumentResponse:
    result = await db.execute(
        select(Document)
        .where(Document.id == document_id, Document.owner_id == owner_id)
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado.",
        )
    return DocumentResponse.model_validate(document)


async def delete_document(
    db: AsyncSession,
    document_id: int,
    owner_id: int,
) -> None:
    result = await db.execute(
        select(Document)
        .where(Document.id == document_id, Document.owner_id == owner_id)
    )
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado.",
        )
    await delete_file(document.file_path)
    await db.delete(document)
    await db.commit()
    logger.info("document_deleted", document_id=document_id)