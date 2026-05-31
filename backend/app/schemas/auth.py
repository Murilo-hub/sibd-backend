from __future__ import annotations
"""
app/schemas/auth.py
Schemas Pydantic para autenticação (request/response).
"""
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


class RegisterRequest(BaseModel):
    name:     str   = Field(..., min_length=2,  max_length=120)
    email:    EmailStr
    password: str   = Field(..., min_length=8,  max_length=128)


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"


class UserResponse(BaseModel):
    id:         int
    name:       str
    email:      str
    is_active:  bool
    created_at: datetime

    model_config = {"from_attributes": True}

class RefreshRequest(BaseModel):
    refresh_token: str