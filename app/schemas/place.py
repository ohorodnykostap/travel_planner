from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class PlaceCreateSchema(BaseModel):
    external_id: Annotated[int, Field(gt=0)]
    notes: Annotated[str | None, Field(None, max_length=5000)]


class PlaceUpdateSchema(BaseModel):
    notes: Annotated[str | None, Field(None, max_length=5000)]
    is_visited: Annotated[bool | None, Field(None, description="Mark place as visited")]


class PlaceReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    external_id: int
    artwork_title: str | None
    artwork_artist: str | None
    artwork_image_id: str | None
    notes: str | None = None
    is_visited: bool
    created_at: datetime
    updated_at: datetime


class ArtworkInfoSchema(BaseModel):
    id: int
    title: str | None
    artist_display: str | None
    image_id: str | None
    date_display: str | None
    medium_display: str | None
    place_of_origin: str | None
    thumbnail_url: str | None = None
