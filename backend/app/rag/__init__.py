# app/rag/__init__.py
# Expõe as funções principais do pipeline RAG para uso nas rotas.
 
from app.rag.indexer   import index_document
from app.rag.retriever import retrieve, format_context
from app.rag.llm       import stream_answer
 
__all__ = ["index_document", "retrieve", "format_context", "stream_answer"]
 