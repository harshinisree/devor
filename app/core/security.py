import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

import bcrypt
import jwt

from app.core.config import settings
from app.core.errors import AppError

ALGORITHM = "HS256"
TokenType = Literal["access", "refresh"]

# Verified against when the email is unknown, so login timing doesn't reveal which emails exist.
_DUMMY_HASH = bcrypt.hashpw(b"devor-dummy-password", bcrypt.gensalt()).decode()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str | None) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), (password_hash or _DUMMY_HASH).encode()) and (
            password_hash is not None
        )
    except ValueError:  # e.g. password longer than bcrypt's 72-byte limit
        return False


def create_token(
    user_id: uuid.UUID, token_type: TokenType, expires_delta: timedelta | None = None
) -> str:
    if expires_delta is None:
        expires_delta = (
            timedelta(minutes=settings.ACCESS_TOKEN_MINUTES)
            if token_type == "access"
            else timedelta(days=settings.REFRESH_TOKEN_DAYS)
        )
    now = datetime.now(UTC)
    claims = {"sub": str(user_id), "type": token_type, "iat": now, "exp": now + expires_delta}
    return jwt.encode(claims, settings.JWT_SECRET, algorithm=ALGORITHM)


def decode_token(token: str, expected_type: TokenType) -> uuid.UUID:
    """Return the user id from a valid token of the expected type, else raise a 401."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub", "type"]},
        )
        if payload["type"] != expected_type:
            raise AppError(401, "invalid_token", f"Expected a {expected_type} token")
        return uuid.UUID(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise AppError(401, "token_expired", "Token has expired") from None
    except (jwt.PyJWTError, ValueError):
        raise AppError(401, "invalid_token", "Invalid token") from None
