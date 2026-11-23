import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def list_pending(self) -> list[User]:
        """Owners and partners still waiting for approval, oldest first."""
        result = await self.session.execute(
            select(User)
            .where(User.role.in_(("owner", "partner")), User.is_approved.is_(False))
            .order_by(User.created_at, User.id)
        )
        return list(result.scalars().all())

    async def add(self, user: User) -> User:
        """Stage the user and flush; raises IntegrityError on a duplicate email."""
        self.session.add(user)
        await self.session.flush()
        return user
