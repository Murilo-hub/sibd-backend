# app/db/__init__.py
# Expõe os símbolos principais do pacote de banco de dados.
# Outros módulos podem importar diretamente de app.db em vez de app.db.database.
 
from app.db.database import Base, engine, AsyncSessionLocal, get_session
 
__all__ = ["Base", "engine", "AsyncSessionLocal", "get_session"]