import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_session
from app.schemas.user import UserOut
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_role("admin"))])


@router.get("/pending", response_model=list[UserOut])
async def pending(session: AsyncSession = Depends(get_session)) -> list[UserOut]:
    users = await AdminService(session).list_pending()
    return [UserOut.model_validate(u) for u in users]


@router.post("/approve/{user_id}", response_model=UserOut)
async def approve(user_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> UserOut:
    user = await AdminService(session).approve(user_id)
    return UserOut.model_validate(user)
