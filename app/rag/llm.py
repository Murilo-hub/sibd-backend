from __future__ import annotations
"""
app/rag/llm.py
──────────────────────────────────────────────────────────────────────────────
Interface com o Groq para geração de respostas com streaming.

Modelo: llama-3.3-70b-versatile
  - Excelente em português
  - Suporta contexto de 128k tokens
  - Streaming nativo via AsyncGroq

O prompt do sistema instrui o modelo a:
  - Responder sempre em português
  - Basear a resposta apenas nos documentos fornecidos
  - Citar as fontes pelo número [FONTE N]
  - Admitir quando não encontrar a informação
──────────────────────────────────────────────────────────────────────────────
"""

from collections.abc import AsyncGenerator

from groq import AsyncGroq

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Prompt do sistema fixo — define o comportamento do assistente
SYSTEM_PROMPT = """Você é um assistente especializado em análise de documentos corporativos.

Seu trabalho é responder perguntas com base exclusivamente nos documentos fornecidos abaixo como contexto.

Regras que você DEVE seguir:
1. Responda SEMPRE em português brasileiro
2. Use APENAS as informações dos documentos fornecidos
3. Ao citar uma informação, referencie a fonte usando [FONTE N] onde N é o número da fonte
4. Se a informação não estiver nos documentos, diga claramente: "Não encontrei essa informação nos documentos disponíveis"
5. Seja objetivo e preciso — evite especulações
6. Se houver informações conflitantes entre documentos, mencione as duas versões e suas fontes

Contexto dos documentos:
{context}"""


# Cliente Groq instanciado uma vez (lazy init)
_client: AsyncGroq | None = None


def get_groq_client() -> AsyncGroq:
    """Retorna o cliente Groq, criando-o na primeira chamada."""
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=settings.groq_api_key)
    return _client


async def stream_answer(
    query:    str,
    context:  str,
    history:  list[dict] | None = None,
) -> AsyncGenerator[str, None]:
    """
    Gera a resposta do LLM token a token (streaming).

    Args:
        query:   pergunta atual do usuário
        context: texto formatado com os chunks recuperados pelo retriever
        history: mensagens anteriores da conversa [{"role": ..., "content": ...}]

    Yields:
        Fragmentos de texto conforme chegam do Groq (streaming SSE).
    """
    client = get_groq_client()

    # monta o system prompt com o contexto dos documentos
    system_message = SYSTEM_PROMPT.format(context=context)

    # constrói o histórico de mensagens para contexto de conversa
    messages: list[dict] = [{"role": "system", "content": system_message}]

    if history:
        # inclui apenas as últimas 10 mensagens para não estourar o contexto
        messages.extend(history[-10:])

    # adiciona a pergunta atual
    messages.append({"role": "user", "content": query})

    logger.info(
        "llm_request",
        model=settings.groq_model,
        messages=len(messages),
        context_len=len(context),
    )

    # stream=True → o Groq envia tokens conforme gera, sem esperar terminar
    stream = await client.chat.completions.create(
        model=settings.groq_model,
        messages=messages,        # type: ignore[arg-type]
        max_tokens=settings.groq_max_tokens,
        temperature=0.1,          # baixo → respostas mais factuais, menos criativas
        stream=True,
    )

    # itera sobre os chunks do stream e yield cada fragmento de texto
    async for chunk in stream:
        delta = chunk.choices[0].delta.content   # texto do fragmento atual
        if delta:                                 # pode ser None no último chunk
            yield delta

    logger.info("llm_stream_done")