from typing import Literal

from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    # "admin" is deliberately not allowed: admins are never self-registered.
    role: Literal["customer", "owner", "partner"]

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("must be at least 8 characters")
        if len(v.encode()) > 72:  # bcrypt limit
            raise ValueError("must be at most 72 bytes")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"


class AccessToken(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
