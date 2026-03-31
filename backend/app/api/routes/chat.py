"""
app/api/routes/chat.py
Rotas de chat e streaming — implementadas na etapa dos agentes.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/chat", tags=["chat"])
