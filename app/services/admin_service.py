import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.user import User
from app.repositories.user_repository import UserRepository


class AdminService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    async def list_pending(self) -> list[User]:
        return await self.users.list_pending()

    async def approve(self, user_id: uuid.UUID) -> User:
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise AppError(404, "user_not_found", "User not found")
        if user.is_approved:
            raise AppError(409, "already_approved", "User is already approved")
        user.is_approved = True
        await self.session.commit()
        return user
