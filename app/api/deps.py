from collections.abc import Awaitable, Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import decode_token
from app.db.session import get_session
from app.models.user import User
from app.repositories.user_repository import UserRepository

# auto_error=False so a missing header goes through our own error shape.
_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    if credentials is None:
        raise AppError(401, "unauthorized", "Not authenticated")
    user_id = decode_token(credentials.credentials, expected_type="access")
    user = await UserRepository(session).get_by_id(user_id)
    if user is None or not user.is_active:
        raise AppError(401, "invalid_token", "Invalid token")
    return user


def require_role(*roles: str) -> Callable[..., Awaitable[User]]:
    async def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise AppError(403, "forbidden", "You do not have permission to do this")
        return user

    return checker
