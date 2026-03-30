from __future__ import annotations
"""
app/models/chat.py
Models SQLAlchemy para sessões e mensagens de chat (RF09 — histórico).
"""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id:         Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    user_id:    Mapped[int]      = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title:      Mapped[str]      = mapped_column(String(200), default="Nova consulta")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relacionamentos
    user:     Mapped["User"]           = relationship("User", back_populates="chat_sessions")  # noqa: F821
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at"
    )

    def __repr__(self) -> str:
        return f"<ChatSession id={self.id} title={self.title}>"


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id:           Mapped[int]          = mapped_column(Integer, primary_key=True, index=True)
    session_id:   Mapped[int]          = mapped_column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role:         Mapped[str]          = mapped_column(String(20), nullable=False)  # user | assistant
    content:      Mapped[str]          = mapped_column(Text, nullable=False)
    sources_json: Mapped[str | None]   = mapped_column(Text, nullable=True)  # JSON com referências documentais
    created_at:   Mapped[datetime]     = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relacionamento
    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")

    def __repr__(self) -> str:
        return f"<ChatMessage id={self.id} role={self.role}>"
