import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, false, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Restaurant(Base):
    __tablename__ = "restaurants"
    __table_args__ = (Index("ix_restaurants_is_open_cuisine", "is_open", "cuisine"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", name="fk_restaurants_owner_id_users"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    cuisine: Mapped[str] = mapped_column(String(50), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    is_open: Mapped[bool] = mapped_column(nullable=False, server_default=false())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
