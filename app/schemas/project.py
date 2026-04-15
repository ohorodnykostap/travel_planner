from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.place import PlaceCreateSchema, PlaceReadSchema


class ProjectCreateSchema(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=255)]
    description: Annotated[str | None, Field(None, max_length=2000)]
    start_date: Annotated[date | None, Field(None)]
    places: Annotated[
        list[PlaceCreateSchema],
        Field(
            default_factory=list,
            description="Initial places to add (1–10). Can be empty if places are added later",
        ),
    ]

    @model_validator(mode="after")
    def validate_places_count(self) -> "ProjectCreateSchema":
        if self.places and len(self.places) > 10:
            raise ValueError("A project cannot have more than 10 places")
        return self


class ProjectUpdateSchema(BaseModel):
    name: Annotated[str | None, Field(None, min_length=1, max_length=255)]
    description: Annotated[str | None, Field(None, max_length=2000)]
    start_date: date | None = None


class ProjectReadSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    start_date: date | None
    is_completed: bool
    created_at: datetime
    updated_at: datetime


class ProjectReadWithPlacesSchema(ProjectReadSchema):
    model_config = ConfigDict(from_attributes=True)

    places: Annotated[list[PlaceReadSchema], Field(default_factory=list)]
