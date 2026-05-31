"""
app/api/__init__.py
Router principal — agrega todas as rotas da API.
"""
from fastapi import APIRouter

from app.api.routes import auth, documents, chat

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(documents.router)
api_router.include_router(chat.router)
