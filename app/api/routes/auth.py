"""
app/api/routes/auth.py
Endpoints de autenticação: registro, login, perfil e refresh de token.
"""
from fastapi import APIRouter, HTTPException, status
from jose import JWTError

from app.core.deps import SessionDep, CurrentUserDep
from app.core.security import decode_token, create_access_token, create_refresh_token
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from app.services.auth_service import register_user, login_user, get_user_by_id

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar novo usuário",
)
async def register(data: RegisterRequest, db: SessionDep):
    """
    Cria uma nova conta de usuário.
    Retorna os dados do usuário criado (sem senha).
    """
    return await register_user(db, data)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login — obtém tokens JWT",
)
async def login(data: LoginRequest, db: SessionDep):
    """
    Autentica o usuário com e-mail e senha.
    Retorna access_token (curto prazo) e refresh_token (longo prazo).
    """
    return await login_user(db, data)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Perfil do usuário autenticado",
)
async def get_me(user_id: CurrentUserDep, db: SessionDep):
    """
    Retorna os dados do usuário dono do token JWT enviado.
    Requer header: Authorization: Bearer <access_token>
    """
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")
    return UserResponse.model_validate(user)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Renova o access token via refresh token",
)
async def refresh_token(body: dict, db: SessionDep):
    """
    Recebe { "refresh_token": "..." } e retorna um novo par de tokens.
    """
    token = body.get("refresh_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="refresh_token é obrigatório.")

    try:
        payload = decode_token(token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")
        user_id = int(payload["sub"])
    except (JWTError, ValueError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido ou expirado.")

    user = await get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado.")

    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )
