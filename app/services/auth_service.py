import asyncio

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AccessToken, TokenPair


def normalize_email(email: str) -> str:
    return email.strip().lower()


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)

    async def register(self, email: str, password: str, role: str) -> User:
        # Customers are auto-approved; owners and partners wait for an admin.
        return await self._create_user(email, password, role, is_approved=role == "customer")

    async def create_admin(self, email: str, password: str) -> User:
        """Only reachable from the CLI, never from an API route."""
        return await self._create_user(email, password, "admin", is_approved=True)

    async def _create_user(self, email: str, password: str, role: str, is_approved: bool) -> User:
        # bcrypt is CPU-bound; keep it off the event loop.
        password_hash = await asyncio.to_thread(hash_password, password)
        user = User(
            email=normalize_email(email),
            password_hash=password_hash,
            role=role,
            is_approved=is_approved,
        )
        try:
            await self.users.add(user)
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise AppError(
                409, "email_taken", "An account with this email already exists"
            ) from None
        await self.session.refresh(user)
        return user

    async def login(self, email: str, password: str) -> TokenPair:
        user = await self.users.get_by_email(normalize_email(email))
        # Always run a bcrypt check (against a dummy hash if no user) so timing is uniform.
        ok = await asyncio.to_thread(
            verify_password, password, user.password_hash if user else None
        )
        if user is None or not ok or not user.is_active:
            raise AppError(401, "invalid_credentials", "Invalid email or password")
        return TokenPair(
            access_token=create_token(user.id, "access"),
            refresh_token=create_token(user.id, "refresh"),
        )

    async def refresh(self, refresh_token: str) -> AccessToken:
        user_id = decode_token(refresh_token, expected_type="refresh")
        user = await self.users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise AppError(401, "invalid_token", "Invalid token")
        return AccessToken(access_token=create_token(user.id, "access"))
