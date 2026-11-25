import uuid
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]
Cuisine = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]
Address = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
Lat = Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False)]
Lng = Annotated[float, Field(ge=-180, le=180, allow_inf_nan=False)]


class RestaurantCreate(BaseModel):
    name: Name
    cuisine: Cuisine
    address: Address
    lat: Lat
    lng: Lng


class RestaurantUpdate(BaseModel):
    """Partial update: send only the fields to change."""

    name: Name | None = None
    cuisine: Cuisine | None = None
    address: Address | None = None
    lat: Lat | None = None
    lng: Lng | None = None

    @model_validator(mode="after")
    def _check_fields(self) -> "RestaurantUpdate":
        sent = self.model_dump(exclude_unset=True)
        if not sent:
            raise ValueError("provide at least one field to update")
        if any(v is None for v in sent.values()):
            raise ValueError("fields cannot be null")
        return self

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class RestaurantOpen(BaseModel):
    is_open: bool


class RestaurantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    cuisine: str
    address: str
    lat: float
    lng: float
    is_open: bool
    created_at: datetime
