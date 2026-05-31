from __future__ import annotations
"""
app/schemas/chat.py
Schemas Pydantic para chat e histórico.
"""
from datetime import datetime
from pydantic import field_validator, BaseModel, Field
from datetime import datetime

import json

class ChatRequest(BaseModel):
    message:    str = Field(..., min_length=1, max_length=4000)
    session_id: int | None = None   # None = nova sessão


class SourceReference(BaseModel):
    document_id:   int
    document_name: str
    page:          int | None
    excerpt:       str


class ChatMessageResponse(BaseModel):
    ...
    sources: list[SourceReference] = []

    @field_validator("sources", mode="before")
    @classmethod
    def parse_sources(cls, v):
        if isinstance(v, str):
            return json.loads(v) if v else []
        return v or []


class ChatSessionSummary(BaseModel):
    id:         int
    title:      str
    created_at: datetime
    updated_at: datetime
    # Sem messages aqui

class ChatHistoryResponse(BaseModel):
    sessions: list[ChatSessionSummary]  # Mensagens só ao abrir a sessão
