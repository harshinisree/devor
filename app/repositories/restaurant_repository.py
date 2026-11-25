import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.restaurant import Restaurant


class RestaurantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, restaurant_id: uuid.UUID) -> Restaurant | None:
        return await self.session.get(Restaurant, restaurant_id)

    async def add(self, restaurant: Restaurant) -> Restaurant:
        self.session.add(restaurant)
        await self.session.flush()
        return restaurant
