"""Pydantic schemas for authentication requests and responses."""

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class GuestSessionResponse(BaseModel):
    role: str = "guest"
    message: str = "Guest session initialized. Results are session-only and not persisted."
