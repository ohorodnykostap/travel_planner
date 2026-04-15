import asyncio
import logging
import math

import httpx
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import settings
from app.models.place import Place
from app.models.project import Project
from app.schemas.base import PaginatedResponseSchema
from app.schemas.place import PlaceCreateSchema, PlaceUpdateSchema
from app.services.artwork_service import get_artwork_by_id

logger = logging.getLogger(__name__)


async def _validate_and_fetch_artwork(external_id: int):
    try:
        artwork = await get_artwork_by_id(external_id)
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Art Institute of Chicago API timed out. Please try again later",
        )
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        logger.error("AIC API error for artwork %s: %s", external_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to reach Art Institute of Chicago API. Please try again later",
        )

    if artwork is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Artwork with external_id={external_id} does not exist in the Art Institute of Chicago API",
        )
    return artwork


async def _check_place_limit(db: AsyncSession, project_id: int) -> None:
    result = await db.execute(
        select(func.count()).select_from(Place).where(Place.project_id == project_id)
    )
    count = result.scalar_one()
    if count >= settings.MAX_PLACES_PER_PROJECT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A project cannot have more than {settings.MAX_PLACES_PER_PROJECT} places",
        )


async def _check_duplicate(db: AsyncSession, project_id: int, external_id: int) -> None:
    result = await db.execute(
        select(Place).where(
            Place.project_id == project_id, Place.external_id == external_id
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"external_id={external_id} is already in this project",
        )


async def add_place_to_project(
    db: AsyncSession, project: Project, payload: PlaceCreateSchema
) -> Place:
    await _check_place_limit(db, project.id)
    await _check_duplicate(db, project.id, payload.external_id)
    artwork = await _validate_and_fetch_artwork(payload.external_id)

    place = Place(
        project_id=project.id,
        external_id=payload.external_id,
        artwork_title=artwork.title,
        artwork_artist=artwork.artist_display,
        artwork_image_id=artwork.image_id,
        notes=payload.notes,
        is_visited=False,
    )
    db.add(place)
    await db.flush()
    await db.refresh(place)
    return place


async def add_places_to_project(
    db: AsyncSession, project: Project, places: list[PlaceCreateSchema]
) -> list[Place]:
    incoming_external_ids = [p.external_id for p in places]

    # Check uniqueness
    if len(incoming_external_ids) != len(set(incoming_external_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate external_id values found in the request",
        )

    result = await db.execute(
        select(func.count()).select_from(Place).where(Place.project_id == project.id)
    )
    existing_count = result.scalar_one()

    if existing_count + len(places) > settings.MAX_PLACES_PER_PROJECT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Adding {len(places)} place(s) would exceed the maximum of "
                f"{settings.MAX_PLACES_PER_PROJECT} places per project "
                f"(currently {existing_count})"
            ),
        )

    # To avoid N+1
    duplicates_result = await db.execute(
        select(Place.external_id).where(
            Place.project_id == project.id, Place.external_id.in_(incoming_external_ids)
        )
    )
    existing_duplicates = duplicates_result.scalars().all()

    if existing_duplicates:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Places with external_ids {list(existing_duplicates)} are already in this project",
        )

    # Concurrency for time economy
    artworks = await asyncio.gather(
        *[_validate_and_fetch_artwork(p.external_id) for p in places]
    )

    added_places: list[Place] = []

    for place_data, artwork in zip(places, artworks, strict=True):
        place = Place(
            project_id=project.id,
            external_id=place_data.external_id,
            artwork_title=artwork.title,
            artwork_artist=artwork.artist_display,
            artwork_image_id=artwork.image_id,
            notes=place_data.notes,
            is_visited=False,
        )
        db.add(place)
        added_places.append(place)

    await db.flush()
    for place in added_places:
        await db.refresh(place)

    return added_places


async def get_place_by_id(
    db: AsyncSession, place_id: int, project_id: int | None = None
) -> Place | None:
    query = select(Place).where(Place.id == place_id)
    if project_id is not None:
        query = query.where(Place.project_id == project_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def list_places_for_project(
    db: AsyncSession,
    project_id: int,
    page: int = 1,
    page_size: int = 20,
    is_visited: bool | None = None,
) -> PaginatedResponseSchema[Place]:
    query = select(Place).where(Place.project_id == project_id)
    count_query = (
        select(func.count()).select_from(Place).where(Place.project_id == project_id)
    )

    if is_visited is not None:
        query = query.where(Place.is_visited == is_visited)
        count_query = count_query.where(Place.is_visited == is_visited)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    query = query.order_by(Place.created_at.asc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    items = list(result.scalars().all())

    return PaginatedResponseSchema(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )


async def update_place(
    db: AsyncSession, place: Place, payload: PlaceUpdateSchema
) -> Place:
    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(place, field, value)

    db.add(place)
    await db.flush()

    # Implement "When all places in a project are marked as visited,
    # the project is marked as completed" logic
    if update_data.get("is_visited") is True:
        unvisited_count_result = await db.execute(
            select(func.count())
            .select_from(Place)
            .where(Place.project_id == place.project_id, Place.is_visited.is_(False))
        )
        unvisited_count = unvisited_count_result.scalar_one()

        if unvisited_count == 0:
            project = await db.get(Project, place.project_id)
            if project and not project.is_completed:
                project.is_completed = True
                db.add(project)
                await db.flush()

    await db.refresh(place)
    return place
