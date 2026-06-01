from __future__ import annotations
"""
app/core/security.py
──────────────────────────────────────────────────────────────────────────────
Funções de segurança: hash de senha, verificação e geração de tokens JWT.

Usa bcrypt puro (sem passlib) — o passlib é incompatível com bcrypt >= 4.0
e causa falha silenciosa na verificação de senha.
──────────────────────────────────────────────────────────────────────────────
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt                   # bcrypt puro — sem passlib
from jose import jwt            # python-jose para assinar/verificar JWT

from app.core.config import settings


def hash_password(password: str) -> str:
    """
    Gera o hash bcrypt de uma senha em texto puro.
    rounds=12 é o padrão seguro — aumentar eleva o custo de brute force.
    """
    password_bytes = password.encode("utf-8")           # converte para bytes
    salt           = bcrypt.gensalt(rounds=12)          # salt aleatório
    hashed         = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")                       # armazena como string no banco


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verifica se a senha em texto puro corresponde ao hash armazenado.
    Retorna False (nunca lança exceção) para não vazar informações.
    """
    try:
        return bcrypt.checkpw(
            plain.encode("utf-8"),    # senha digitada pelo usuário
            hashed.encode("utf-8"),   # hash salvo no banco
        )
    except Exception:
        return False   # hash malformado ou outro erro → nega acesso


def create_access_token(subject: Any) -> str:
    """
    Gera um JWT de curta duração para autenticação de requests.
    subject normalmente é o user_id (int).
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes   # padrão: 60 min
    )
    payload = {
        "sub":  str(subject),   # subject — ID do usuário
        "exp":  expire,         # expiration — python-jose aceita datetime
        "type": "access",       # distingue de refresh para validação
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: Any) -> str:
    """
    Gera um JWT de longa duração para renovar o access token sem novo login.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_token_expire_days   # padrão: 7 dias
    )
    payload = {
        "sub":  str(subject),
        "exp":  expire,
        "type": "refresh",   # obrigatório — verificado na rota /auth/refresh
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """
    Decodifica e valida a assinatura + expiração de um JWT.
    Lança JWTError se inválido ou expirado — o caller deve capturar.
    """
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
