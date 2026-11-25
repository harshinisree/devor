import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_approved, require_role
from app.db.session import get_session
from app.models.user import User
from app.schemas.restaurant import (
    RestaurantCreate,
    RestaurantOpen,
    RestaurantOut,
    RestaurantUpdate,
)
from app.services.restaurant_service import RestaurantService

router = APIRouter(prefix="/restaurants", tags=["restaurants"])

# Owner-only: right role first, then approved.
owner_only = [Depends(require_role("owner")), Depends(require_approved)]


@router.post("", response_model=RestaurantOut, status_code=201, dependencies=owner_only)
async def create_restaurant(
    body: RestaurantCreate,
    user: User = Depends(require_approved),
    session: AsyncSession = Depends(get_session),
) -> RestaurantOut:
    restaurant = await RestaurantService(session).create(user, body)
    return RestaurantOut.model_validate(restaurant)


@router.patch("/{restaurant_id}", response_model=RestaurantOut, dependencies=owner_only)
async def update_restaurant(
    restaurant_id: uuid.UUID,
    body: RestaurantUpdate,
    user: User = Depends(require_approved),
    session: AsyncSession = Depends(get_session),
) -> RestaurantOut:
    restaurant = await RestaurantService(session).update(user, restaurant_id, body.changes())
    return RestaurantOut.model_validate(restaurant)


@router.patch("/{restaurant_id}/open", response_model=RestaurantOut, dependencies=owner_only)
async def set_restaurant_open(
    restaurant_id: uuid.UUID,
    body: RestaurantOpen,
    user: User = Depends(require_approved),
    session: AsyncSession = Depends(get_session),
) -> RestaurantOut:
    restaurant = await RestaurantService(session).set_open(user, restaurant_id, body.is_open)
    return RestaurantOut.model_validate(restaurant)


@router.get("/{restaurant_id}", response_model=RestaurantOut)
async def get_restaurant(
    restaurant_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> RestaurantOut:
    return RestaurantOut.model_validate(await RestaurantService(session).get(restaurant_id))
