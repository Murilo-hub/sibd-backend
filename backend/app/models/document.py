from __future__ import annotations
"""
app/models/document.py
Model SQLAlchemy para documentos enviados e indexados.
"""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Document(Base):
    __tablename__ = "documents"

    id:           Mapped[int]           = mapped_column(Integer, primary_key=True, index=True)
    owner_id:     Mapped[int]           = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Arquivo
    filename:     Mapped[str]           = mapped_column(String(255), nullable=False)
    original_name: Mapped[str]          = mapped_column(String(255), nullable=False)
    file_path:    Mapped[str]           = mapped_column(String(512), nullable=False)
    file_size:    Mapped[int]           = mapped_column(Integer, nullable=False)  # bytes
    file_type:    Mapped[str]           = mapped_column(String(10), nullable=False)   # pdf, docx...

    # Metadados corporativos
    empresa:      Mapped[str]           = mapped_column(String(200), nullable=False, index=True)
    categoria:    Mapped[str]           = mapped_column(String(100), nullable=False, index=True)
    data_documento: Mapped[str | None]  = mapped_column(String(20), nullable=True)
    descricao:    Mapped[str | None]    = mapped_column(Text, nullable=True)

    # Indexação
    status:       Mapped[str]           = mapped_column(
        String(20), default="pending"   # pending | processing | indexed | error
    )
    chunks_count: Mapped[int]           = mapped_column(Integer, default=0)
    error_message: Mapped[str | None]   = mapped_column(Text, nullable=True)

    # Timestamps
    created_at:   Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())
    indexed_at:   Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relacionamentos
    owner: Mapped["User"] = relationship("User", back_populates="documents")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Document id={self.id} name={self.original_name} status={self.status}>"
