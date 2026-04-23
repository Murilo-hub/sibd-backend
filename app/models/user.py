from __future__ import annotations
"""
app/models/user.py
Model SQLAlchemy para usuários do sistema.
"""
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.chat import ChatSession, ChatMessage


class User(Base):
    __tablename__ = "users"

    id:              Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    name:            Mapped[str]      = mapped_column(String(120), nullable=False)
    email:           Mapped[str]      = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str]      = mapped_column(String(255), nullable=False)
    is_active:       Mapped[bool]     = mapped_column(Boolean, default=True)
    created_at:      Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:      Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), server_onupdate=func.now())

    documents:     Mapped[list["Document"]]    = relationship("Document",    back_populates="owner", cascade="all, delete-orphan")
    chat_sessions: Mapped[list["ChatSession"]] = relationship("ChatSession", back_populates="user",  cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"