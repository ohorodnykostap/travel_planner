import logging
import math

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.place import Place
from app.models.project import Project
from app.schemas.base import PaginatedResponseSchema
from app.schemas.project import ProjectCreateSchema, ProjectUpdateSchema
from app.services import place_service

logger = logging.getLogger(__name__)


async def create_project(db: AsyncSession, payload: ProjectCreateSchema) -> Project:
    project = Project(
        name=payload.name,
        description=payload.description,
        start_date=payload.start_date,
    )
    db.add(project)
    await db.flush()

    if payload.places:
        await place_service.add_places_to_project(db, project, payload.places)

    await db.refresh(project)
    return project


async def get_project_by_id(db: AsyncSession, project_id: int) -> Project | None:
    result = await db.execute(select(Project).where(Project.id == project_id))
    return result.scalar_one_or_none()


async def list_projects(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    is_completed: bool | None = None,
) -> PaginatedResponseSchema[Project]:
    query = select(Project)
    count_query = select(func.count()).select_from(Project)

    if is_completed is not None:
        query = query.where(Project.is_completed == is_completed)
        count_query = count_query.where(Project.is_completed == is_completed)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Pagination
    offset = (page - 1) * page_size
    query = query.order_by(Project.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    items = list(result.scalars().all())

    return PaginatedResponseSchema(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )


async def update_project(
    db: AsyncSession, project: Project, payload: ProjectUpdateSchema
) -> Project:
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


async def delete_project(db: AsyncSession, project: Project) -> None:
    result = await db.execute(
        select(Place.id)
        .where(Place.project_id == project.id, Place.is_visited.is_(True))
        .limit(1)
    )
    has_visited = result.first() is not None

    if has_visited:
        raise ValueError(
            "Cannot delete a project that has visited places. "
            "Remove or unmark visited places first"
        )
    await db.delete(project)
    await db.flush()
