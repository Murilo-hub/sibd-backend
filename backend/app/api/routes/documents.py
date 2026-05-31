from __future__ import annotations
"""
app/api/routes/documents.py
──────────────────────────────────────────────────────────────────────────────
Rotas REST para upload e gerenciamento de documentos.

POST   /documents          → upload de arquivo + metadados
GET    /documents          → lista paginada dos documentos do usuário
GET    /documents/{id}     → detalhes de um documento
DELETE /documents/{id}     → remove documento, arquivo e chunks vetoriais
──────────────────────────────────────────────────────────────────────────────
"""

from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile, status

from app.core.deps import CurrentUserDep, SessionDep
from app.schemas.document import DocumentListResponse, DocumentMetadata, DocumentResponse
from app.services.document_service import (
    delete_document,
    get_document,
    list_documents,
    upload_document,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload de documento",
    description="Envia um arquivo e seus metadados. A indexação RAG ocorre em background.",
)
async def upload(
    background_tasks: BackgroundTasks,          # injeta pelo FastAPI automaticamente
    file:             UploadFile = File(...),   # arquivo binário
    empresa:          str        = Form(...),   # metadados via multipart/form-data
    categoria:        str        = Form(...),
    data_documento:   str | None = Form(None),
    descricao:        str | None = Form(None),
    db:               SessionDep = ...,
    user_id:          CurrentUserDep = ...,
):
    metadata = DocumentMetadata(
        empresa=empresa,
        categoria=categoria,
        data_documento=data_documento,
        descricao=descricao,
    )
    return await upload_document(db, file, metadata, user_id, background_tasks)


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="Listar documentos",
)
async def list_docs(
    page:    int          = 1,
    limit:   int          = 20,
    db:      SessionDep   = ...,
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
    db:          SessionDep   = ...,
    user_id:     CurrentUserDep = ...,
):
    return await get_document(db, document_id, user_id)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deletar documento",
    description="Remove o documento, o arquivo no storage e todos os chunks vetoriais.",
)
async def delete_doc(
    document_id: int,
    db:          SessionDep   = ...,
    user_id:     CurrentUserDep = ...,
):
    await delete_document(db, document_id, user_id)