from __future__ import annotations
"""
app/api/routes/chat.py
──────────────────────────────────────────────────────────────────────────────
Rotas de chat com streaming SSE (Server-Sent Events).

POST /chat/stream   → envia mensagem e recebe resposta em streaming
GET  /chat/history  → lista sessões de chat do usuário
GET  /chat/{id}     → mensagens de uma sessão específica
──────────────────────────────────────────────────────────────────────────────
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUserDep, SessionDep
from app.core.logging import get_logger
from app.models.chat import ChatMessage, ChatSession
from app.rag import format_context, retrieve, stream_answer
from app.schemas.chat import ChatRequest, ChatHistoryResponse, ChatSessionSummary

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "/stream",
    summary="Enviar mensagem com resposta em streaming",
    description="Retorna a resposta do LLM token a token via Server-Sent Events.",
)
async def chat_stream(
    body:    ChatRequest,
    db:      SessionDep,
    user_id: CurrentUserDep,
):
    """
    Pipeline completo do chat RAG:
      1. Recupera ou cria a sessão de chat
      2. Busca chunks relevantes no pgvector (retrieve)
      3. Formata o contexto para o LLM
      4. Faz streaming da resposta do Groq
      5. Salva a mensagem e resposta no histórico
    """
    # ── 1. Sessão de chat ─────────────────────────────────────────────────────
    if body.session_id:
        # valida que a sessão pertence ao usuário
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == body.session_id,
                ChatSession.user_id == user_id,
            )
        )
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sessão não encontrada.",
            )
    else:
        # cria nova sessão com título gerado a partir da primeira mensagem
        title = body.message[:60] + ("..." if len(body.message) > 60 else "")
        session = ChatSession(user_id=user_id, title=title)
        db.add(session)
        await db.flush()   # gera o ID da sessão
        await db.commit()
        await db.refresh(session)

    # ── 2. Carrega histórico da sessão para contexto ──────────────────────────
    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
        .limit(10)   # últimas 10 mensagens para não estourar o contexto do LLM
    )
    history_messages = history_result.scalars().all()

    # converte para o formato de mensagens do Groq
    history = [
        {"role": msg.role, "content": msg.content}
        for msg in history_messages
    ]

    # ── 3. Recupera chunks relevantes do pgvector ─────────────────────────────
    chunks = await retrieve(
        db=db,
        query=body.message,
        owner_id=user_id,
    )
    context = format_context(chunks)   # formata para inserir no prompt

    # ── 4. Salva a mensagem do usuário no histórico ───────────────────────────
    user_message = ChatMessage(
        session_id=session.id,
        role="user",
        content=body.message,
    )
    db.add(user_message)
    await db.commit()

    # ── 5. Streaming da resposta ──────────────────────────────────────────────
    async def generate():
        """
        Gerador assíncrono que faz streaming da resposta e salva no banco.
        Usa o formato SSE: cada chunk é enviado como 'data: <texto>\n\n'
        """
        full_response = ""   # acumula a resposta completa para salvar no banco

        try:
            async for token in stream_answer(
                query=body.message,
                context=context,
                history=history,
            ):
                full_response += token
                # SSE: envia cada token como evento
                yield f"data: {token}\n\n"

        except Exception as exc:
            logger.error("chat_stream_error", error=str(exc), session_id=session.id)
            yield f"data: [ERRO: Falha ao gerar resposta]\n\n"
            full_response = "Erro ao gerar resposta."

        finally:
            # salva a resposta completa do assistente no histórico
            # (mesmo em caso de erro parcial)
            if full_response:
                assistant_message = ChatMessage(
                    session_id=session.id,
                    role="assistant",
                    content=full_response,
                    sources_json={
                        "chunks": [
                            {
                                "document_id": c["document_id"],
                                "similarity":  round(c["similarity"], 3),
                                "excerpt":     c["content"][:200],   # primeiros 200 chars
                                "metadata":    c["metadata"],
                            }
                            for c in chunks
                        ]
                    },
                )
                db.add(assistant_message)
                await db.commit()

                # sinaliza ao frontend que o streaming terminou
                yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",   # content-type obrigatório para SSE
        headers={
            "Cache-Control":  "no-cache",
            "X-Accel-Buffering": "no",    # desativa buffer do Nginx (importante no Render)
            "X-Session-Id":   str(session.id),   # envia o ID da sessão para o frontend
        },
    )


@router.get(
    "/history",
    response_model=ChatHistoryResponse,
    summary="Listar sessões de chat",
)
async def get_history(
    db:      SessionDep,
    user_id: CurrentUserDep,
):
    """Retorna todas as sessões de chat do usuário, ordenadas da mais recente."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .order_by(ChatSession.updated_at.desc())
        .limit(50)   # máximo de 50 sessões no histórico
    )
    sessions = result.scalars().all()

    return ChatHistoryResponse(
        sessions=[
            ChatSessionSummary(
                id=s.id,
                title=s.title,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in sessions
        ]
    )


@router.get(
    "/{session_id}",
    summary="Mensagens de uma sessão",
)
async def get_session_messages(
    session_id: int,
    db:         SessionDep,
    user_id:    CurrentUserDep,
):
    """Retorna todas as mensagens de uma sessão específica."""
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages))   # carrega mensagens em um único query
        .where(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessão não encontrada.",
        )

    return {
        "session_id": session.id,
        "title":      session.title,
        "messages": [
            {
                "id":         msg.id,
                "role":       msg.role,
                "content":    msg.content,
                "sources":    msg.sources_json or {},
                "created_at": msg.created_at,
            }
            for msg in session.messages
        ],
    }