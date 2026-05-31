from __future__ import annotations
"""
app/core/deps.py
Dependências reutilizáveis do FastAPI (injeção de dependência).
"""
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.database import get_session

from app.services.auth_service import get_user_by_id
from app.models.user import User

bearer_scheme = HTTPBearer()


# ── Sessão do banco ───────────────────────────────────────────────────────────

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# ── Usuário autenticado ───────────────────────────────────────────────────────

async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> int:
    """
    Extrai e valida o JWT do header Authorization: Bearer <token>.
    Retorna o ID do usuário ou lança 401.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido ou expirado.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(credentials.credentials)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return int(user_id)
    except (JWTError, ValueError):
        raise credentials_exception


CurrentUserDep = Annotated[int, Depends(get_current_user_id)]

async def get_current_user(
    user_id: CurrentUserDep,
    db: SessionDep,
) -> User:
    user = await get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuário não encontrado.")
    return user

CurrentUserObjDep = Annotated[User, Depends(get_current_user)]
