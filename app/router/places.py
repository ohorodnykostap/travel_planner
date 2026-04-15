from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import (
    PaginationParams,
    get_place_or_404,
    get_project_or_404,
)
from app.models.place import Place
from app.models.project import Project
from app.schemas.base import PaginatedResponseSchema
from app.schemas.place import PlaceCreateSchema, PlaceReadSchema, PlaceUpdateSchema
from app.services import place_service

router = APIRouter(
    prefix="/projects/{project_id}/places",
    tags=["Places"],
)


@router.post(
    "",
    response_model=PlaceReadSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add a place to an existing project",
    description=(
        "Validate the `external_id` against the **Art Institute of Chicago API** "
        "and, if found, attach the artwork as a place to the project.\n\n"
        "Artwork metadata (title, artist, image_id) is fetched and stored locally "
        "at creation time so it is always available without hitting the external API again.\n\n"
        "**Constraints:**\n"
        "- A project cannot have more than **10 places** in total.\n"
        "- The same `external_id` cannot be added to the same project twice."
    ),
    responses={
        201: {
            "description": "Place added successfully and returned with artwork metadata."
        },
        400: {"description": "Project already has 10 places (maximum reached)."},
        404: {"description": "Project with the given ID does not exist."},
        409: {"description": "This `external_id` is already present in the project."},
        422: {
            "description": "`external_id` does not exist in the Art Institute of Chicago API."
        },
        503: {
            "description": "Art Institute of Chicago API is temporarily unavailable."
        },
    },
)
async def add_place(
    payload: PlaceCreateSchema,
    project: Annotated[Project, Depends(get_project_or_404)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Place:
    return await place_service.add_place_to_project(db, project, payload)


@router.get(
    "",
    response_model=PaginatedResponseSchema[PlaceReadSchema],
    summary="List all places in a project",
    description=(
        "Return a **paginated** list of places belonging to the given project.\n\n"
        "Use `is_visited` to filter:\n"
        "- `is_visited=false` — only unvisited places\n"
        "- `is_visited=true` — only visited places\n"
        "- *(omit)* — all places\n\n"
        "Results are ordered by creation date (oldest first)."
    ),
    responses={
        200: {"description": "Paginated list of places for the project."},
        404: {"description": "Project with the given ID does not exist."},
    },
)
async def list_places(
    project: Annotated[Project, Depends(get_project_or_404)],
    pagination: Annotated[PaginationParams, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
    is_visited: Annotated[
        bool | None,
        Query(description="Filter by visited status. Omit to return all places."),
    ] = None,
) -> PaginatedResponseSchema[Place]:
    return await place_service.list_places_for_project(
        db,
        project_id=project.id,
        page=pagination.page,
        page_size=pagination.page_size,
        is_visited=is_visited,
    )


@router.get(
    "/{place_id}",
    response_model=PlaceReadSchema,
    summary="Get a single place in a project",
    description=(
        "Fetch a specific place by its ID, scoped to the given project. "
        "Returns artwork metadata alongside any notes and the visited status."
    ),
    responses={
        200: {"description": "Place found and returned."},
        404: {"description": "Project or place with the given ID does not exist."},
    },
)
async def get_place(
    place: Annotated[Place, Depends(get_place_or_404)],
) -> Place:
    return place


@router.patch(
    "/{place_id}",
    response_model=PlaceReadSchema,
    summary="Update a place",
    description=(
        "Partially update a place's **notes** and/or **`is_visited`** flag. "
        "Only fields present in the request body are modified.\n\n"
        "**Auto-completion:** when this update causes *all* places in the project "
        "to be marked as visited, the project's `is_completed` flag is automatically "
        "set to `true`. Conversely, un-marking a place re-opens the project."
    ),
    responses={
        200: {"description": "Place updated successfully."},
        404: {"description": "Project or place with the given ID does not exist."},
        422: {"description": "Request body failed validation."},
    },
)
async def update_place(
    payload: PlaceUpdateSchema,
    place: Annotated[Place, Depends(get_place_or_404)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Place:
    return await place_service.update_place(db, place, payload)


@router.post(
    "/{place_id}/visit",
    response_model=PlaceReadSchema,
    summary="Mark a place as visited",
    description=(
        "Convenience endpoint — equivalent to `PATCH /{place_id}` with "
        '`{"is_visited": true}` in the body, but requires no request body at all.\n\n'
        "**Auto-completion:** if this is the last unvisited place in the project, "
        "the project is automatically marked as `is_completed = true`."
    ),
    responses={
        200: {
            "description": "Place marked as visited. Project may have been auto-completed."
        },
        404: {"description": "Project or place with the given ID does not exist."},
    },
)
async def mark_place_visited(
    place: Annotated[Place, Depends(get_place_or_404)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Place:
    return await place_service.update_place(
        db, place, PlaceUpdateSchema(is_visited=True)
    )