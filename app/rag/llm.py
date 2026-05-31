from __future__ import annotations
"""
app/rag/llm.py
Interface com o Groq para geração de respostas com streaming.
"""

from collections.abc import AsyncGenerator

from groq import AsyncGroq

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """Você é um assistente especializado em análise de documentos corporativos.

Responda perguntas com base exclusivamente nos documentos fornecidos abaixo como contexto.

Regras:
1. Responda SEMPRE em português brasileiro
2. Use APENAS as informações dos documentos fornecidos
3. Seja objetivo e preciso
4. Se a informação não estiver nos documentos, diga claramente que não encontrou
5. Se houver informações conflitantes entre documentos, mencione as duas versões

Contexto dos documentos:
{context}"""

_client: AsyncGroq | None = None


def get_groq_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=settings.groq_api_key)
    return _client


async def stream_answer(
    query:   str,
    context: str,
    history: list[dict] | None = None,
) -> AsyncGenerator[str, None]:
    client = get_groq_client()

    system_message = SYSTEM_PROMPT.format(context=context)

    messages: list[dict] = [{"role": "system", "content": system_message}]
    if history:
        messages.extend(history[-10:])
    messages.append({"role": "user", "content": query})

    logger.info("llm_request", model=settings.groq_model, messages=len(messages))

    stream = await client.chat.completions.create(
        model=settings.groq_model,
        messages=messages,        # type: ignore[arg-type]
        max_tokens=settings.groq_max_tokens,
        temperature=0.1,
        stream=True,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta

    logger.info("llm_stream_done")
