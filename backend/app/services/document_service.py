from __future__ import annotations
"""
app/services/document_service.py
──────────────────────────────────────────────────────────────────────────────
Regras de negócio para upload e gerenciamento de documentos.

Após o upload bem-sucedido, dispara a indexação RAG como background task
para não bloquear a resposta ao usuário — o processo de extração,
chunking e embedding pode levar alguns segundos.
──────────────────────────────────────────────────────────────────────────────
"""

from fastapi import BackgroundTasks, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.vector_store import delete_document_chunks
from app.models.document import Document
from app.rag.indexer import index_document
from app.schemas.document import DocumentListResponse, DocumentMetadata, DocumentResponse
from app.utils.file_utils import delete_file, save_upload

logger = get_logger(__name__)


async def upload_document(
    db:               AsyncSession,
    file:             UploadFile,
    metadata:         DocumentMetadata,
    owner_id:         int,
    background_tasks: BackgroundTasks,     # injeta tarefas em background do FastAPI
) -> DocumentResponse:
    """
    Salva o arquivo no Supabase Storage, cria o registro no banco
    e dispara a indexação RAG em background.

    O documento é criado com status='pending' e atualizado para
    'processing' → 'indexed' (ou 'error') pelo indexer em background.
    """
    # ── Salva no Supabase Storage ─────────────────────────────────────────────
    filename, file_url, file_size = await save_upload(file)
    ext = filename.rsplit(".", 1)[-1]   # extrai a extensão do nome gerado

    # ── Cria registro no banco relacional ─────────────────────────────────────
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
        status="pending",    # será atualizado pelo indexer
    )
    db.add(document)
    await db.flush()        # gera o ID sem fazer commit ainda
    await db.refresh(document)   # carrega o ID gerado pelo banco

    # commit aqui para garantir que o documento existe antes do background task
    await db.commit()
    await db.refresh(document)

    logger.info("document_uploaded", document_id=document.id, owner_id=owner_id)

    # ── Dispara indexação RAG em background ───────────────────────────────────
    # background_tasks.add_task executa a função após a resposta ser enviada
    # o usuário recebe o DocumentResponse imediatamente, sem esperar o RAG
    background_tasks.add_task(
        index_document,
        db=db,
        document_id=document.id,
        file_url=file_url,
        file_type=ext,
        metadata={
            "original_name": document.original_name,
            "empresa":       metadata.empresa,
            "categoria":     metadata.categoria,
            "descricao":     metadata.descricao or "",
        },
    )

    return DocumentResponse.model_validate(document)


async def list_documents(
    db:       AsyncSession,
    owner_id: int,
    page:     int = 1,
    limit:    int = 20,
) -> DocumentListResponse:
    """Retorna os documentos do usuário paginados, ordenados do mais recente."""
    offset = (page - 1) * limit

    # busca a página atual
    result = await db.execute(
        select(Document)
        .where(Document.owner_id == owner_id)
        .order_by(Document.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    documents = result.scalars().all()

    # conta o total para o frontend calcular o número de páginas
    count_result = await db.execute(
        select(Document).where(Document.owner_id == owner_id)
    )
    total = len(count_result.scalars().all())

    return DocumentListResponse(
        items=[DocumentResponse.model_validate(d) for d in documents],
        total=total,
        page=page,
        limit=limit,
    )


async def get_document(
    db:          AsyncSession,
    document_id: int,
    owner_id:    int,
) -> DocumentResponse:
    """Retorna um documento específico, validando que pertence ao usuário."""
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.owner_id == owner_id,   # garante isolamento entre usuários
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado.",
        )
    return DocumentResponse.model_validate(document)


async def delete_document(
    db:          AsyncSession,
    document_id: int,
    owner_id:    int,
) -> None:
    """
    Remove o documento do banco relacional, do Supabase Storage
    e todos os seus chunks do pgvector.
    """
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.owner_id == owner_id,
        )
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado.",
        )

    # remove os chunks vetoriais antes de deletar o documento
    await delete_document_chunks(db, document_id)

    # remove o arquivo do Supabase Storage
    await delete_file(document.file_path)

    # remove o registro do banco relacional
    await db.delete(document)
    await db.commit()

    logger.info("document_deleted", document_id=document_id, owner_id=owner_id)