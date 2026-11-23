from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.auth import (
    AccessToken,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
)
from app.schemas.user import UserOut
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
async def register(body: RegisterRequest, session: AsyncSession = Depends(get_session)) -> UserOut:
    user = await AuthService(session).register(body.email, body.password, body.role)
    return UserOut.model_validate(user)


@router.post("/login", response_model=TokenPair)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)) -> TokenPair:
    return await AuthService(session).login(body.email, body.password)


@router.post("/refresh", response_model=AccessToken)
async def refresh(
    body: RefreshRequest, session: AsyncSession = Depends(get_session)
) -> AccessToken:
    return await AuthService(session).refresh(body.refresh_token)
