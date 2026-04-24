from __future__ import annotations
"""
app/api/routes/documents.py
Rotas de upload e gerenciamento de documentos.
"""
from fastapi import APIRouter, UploadFile, File, Form, status

from app.core.deps import SessionDep, CurrentUserDep
from app.schemas.document import DocumentMetadata, DocumentResponse, DocumentListResponse
from app.services.document_service import (
    upload_document, list_documents, get_document, delete_document
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload de documento",
)
async def upload(
    file: UploadFile = File(...),
    empresa: str = Form(...),
    categoria: str = Form(...),
    data_documento: str | None = Form(None),
    descricao: str | None = Form(None),
    db: SessionDep = ...,
    user_id: CurrentUserDep = ...,
):
    metadata = DocumentMetadata(
        empresa=empresa,
        categoria=categoria,
        data_documento=data_documento,
        descricao=descricao,
    )
    return await upload_document(db, file, metadata, user_id)


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="Listar documentos",
)
async def list_docs(
    page: int = 1,
    limit: int = 20,
    db: SessionDep = ...,
    user_id: CurrentUserDep = ...,
):
    return await list_documents(db, user_id, page, limit)


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Detalhes de um documento",
)
async def get_doc(
    document_id: int,
    db: SessionDep = ...,
    user_id: CurrentUserDep = ...,
):
    return await get_document(db, document_id, user_id)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar documento",
)
async def delete_doc(
    document_id: int,
    db: SessionDep = ...,
    user_id: CurrentUserDep = ...,
):
    await delete_document(db, document_id, user_id)