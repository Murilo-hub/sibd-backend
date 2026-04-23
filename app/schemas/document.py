from __future__ import annotations
"""
app/schemas/document.py
Schemas Pydantic para documentos.
"""
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic import computed_field

@computed_field
def file_size_readable(self) -> str:
    if self.file_size < 1024 * 1024:
        return f"{self.file_size / 1024:.1f} KB"  # KB
    return f"{self.file_size / (1024 * 1024):.1f} MB"  # MB

class DocumentMetadata(BaseModel):
    empresa:        str  = Field(..., min_length=1, max_length=200)
    categoria:      str  = Field(..., min_length=1, max_length=100)
    data_documento: str | None = None
    descricao:      str | None = None


class DocumentResponse(BaseModel):
    id:            int
    filename:      str
    original_name: str
    file_size:     int
    file_type:     str
    empresa:       str
    categoria:     str
    data_documento: str | None
    descricao:     str | None
    status:        str
    chunks_count:  int
    created_at:    datetime
    indexed_at:    datetime | None

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    items:  list[DocumentResponse]
    total:  int
    page:   int = 1
    limit:  int = 20

    
