"""
app/api/routes/documents.py
Rotas de documentos — implementadas na etapa de upload/indexação.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/documents", tags=["documents"])
