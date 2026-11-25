import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.restaurant import Restaurant
from app.models.user import User
from app.repositories.restaurant_repository import RestaurantRepository
from app.schemas.restaurant import RestaurantCreate


class RestaurantService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.restaurants = RestaurantRepository(session)

    async def create(self, owner: User, data: RestaurantCreate) -> Restaurant:
        restaurant = Restaurant(owner_id=owner.id, **data.model_dump())
        await self.restaurants.add(restaurant)
        await self.session.commit()
        await self.session.refresh(restaurant)  # load server-side defaults (created_at)
        return restaurant

    async def get(self, restaurant_id: uuid.UUID) -> Restaurant:
        restaurant = await self.restaurants.get_by_id(restaurant_id)
        if restaurant is None:
            raise AppError(404, "restaurant_not_found", "Restaurant not found")
        return restaurant

    async def update(
        self, owner: User, restaurant_id: uuid.UUID, changes: dict[str, Any]
    ) -> Restaurant:
        restaurant = await self._get_owned(owner, restaurant_id)
        for field, value in changes.items():
            setattr(restaurant, field, value)
        await self.session.commit()
        return restaurant

    async def set_open(self, owner: User, restaurant_id: uuid.UUID, is_open: bool) -> Restaurant:
        return await self.update(owner, restaurant_id, {"is_open": is_open})

    async def _get_owned(self, owner: User, restaurant_id: uuid.UUID) -> Restaurant:
        """Load a restaurant and make sure the caller owns it (404 missing, 403 not theirs)."""
        restaurant = await self.get(restaurant_id)
        if restaurant.owner_id != owner.id:
            raise AppError(403, "forbidden", "You do not own this restaurant")
        return restaurant
