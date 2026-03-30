from __future__ import annotations
"""
app/schemas/chat.py
Schemas Pydantic para chat e histórico.
"""
from datetime import datetime
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message:    str = Field(..., min_length=1, max_length=4000)
    session_id: int | None = None   # None = nova sessão


class SourceReference(BaseModel):
    document_id:   int
    document_name: str
    page:          int | None
    excerpt:       str


class ChatMessageResponse(BaseModel):
    id:         int
    role:       str
    content:    str
    sources:    list[SourceReference] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionResponse(BaseModel):
    id:         int
    title:      str
    created_at: datetime
    updated_at: datetime
    messages:   list[ChatMessageResponse] = []

    model_config = {"from_attributes": True}


class ChatHistoryResponse(BaseModel):
    sessions: list[ChatSessionResponse]
