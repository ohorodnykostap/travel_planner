from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import PaginationParams, get_current_user, get_project_or_404
from app.models.project import Project
from app.schemas.base import PaginatedResponseSchema
from app.schemas.project import (
    ProjectCreateSchema,
    ProjectReadSchema,
    ProjectReadWithPlacesSchema,
    ProjectUpdateSchema,
)
from app.services import project_service

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post(
    "",
    response_model=ProjectReadWithPlacesSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a travel project",
    description=(
        "Create a new travel project. Optionally include up to **10 places** "
        "in the same request — each `external_id` is validated against the "
        "Art Institute of Chicago API before the project is saved.\n\n"
        "If any `external_id` is invalid, the entire request is rejected and "
        "nothing is persisted."
    ),
    responses={
        201: {"description": "Project created successfully, returned with its places."},
        400: {
            "description": "Validation error — e.g. more than 10 places supplied or duplicate `external_id` within the batch."
        },
        422: {
            "description": "One or more `external_id` values do not exist in the Art Institute of Chicago API."
        },
        503: {
            "description": "Art Institute of Chicago API is temporarily unavailable."
        },
    },
)
async def create_project(
    payload: ProjectCreateSchema,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
) -> Project:
    try:
        return await project_service.create_project(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "",
    response_model=PaginatedResponseSchema[ProjectReadSchema],
    summary="List travel projects",
    description=(
        "Return a **paginated** list of all travel projects.\n\n"
        "Use `is_completed` to filter:\n"
        "- `is_completed=false` — only active projects\n"
        "- `is_completed=true` — only finished projects\n"
        "- *(omit)* — all projects\n\n"
        "Results are ordered by creation date (newest first)."
    ),
    responses={
        200: {"description": "Paginated list of projects."},
    },
)
async def list_projects(
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
    pagination: Annotated[PaginationParams, Depends()],
    is_completed: Annotated[
        bool | None,
        Query(description="Filter by completion status. Omit to return all projects."),
    ] = None,
) -> PaginatedResponseSchema[ProjectReadSchema]:
    return await project_service.list_projects(
        db,
        page=pagination.page,
        page_size=pagination.page_size,
        is_completed=is_completed,
    )


@router.get(
    "/{project_id}",
    response_model=ProjectReadWithPlacesSchema,
    summary="Get a single travel project",
    description=(
        "Fetch a travel project by its ID. "
        "The response includes the full list of associated **places** "
        "(artwork title, artist, visited status, notes, etc.)."
    ),
    responses={
        200: {"description": "Project found and returned with its places."},
        404: {"description": "Project with the given ID does not exist."},
    },
)
async def get_project(
    project: Annotated[Project, Depends(get_project_or_404)],
) -> Project:
    return project


@router.patch(
    "/{project_id}",
    response_model=ProjectReadWithPlacesSchema,
    summary="Update a travel project",
    description=(
        "Partially update a project's **name**, **description**, or **start_date**. "
        "Only fields included in the request body are changed — omitted fields keep "
        "their current value.\n\n"
        "The `is_completed` flag is managed automatically by the system and "
        "cannot be set directly through this endpoint."
    ),
    responses={
        200: {"description": "Project updated successfully."},
        404: {"description": "Project with the given ID does not exist."},
        422: {"description": "Request body failed validation (e.g. empty name)."},
    },
)
async def update_project(
    payload: ProjectUpdateSchema,
    project: Annotated[Project, Depends(get_project_or_404)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Project:
    return await project_service.update_project(db, project, payload)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a travel project",
    description=(
        "Permanently delete a travel project and all of its places.\n\n"
        "**Constraint:** deletion is blocked if **any place** in the project is "
        "marked as `is_visited = true`. Un-mark visited places first, or use a "
        "project that has no visited places.\n\n"
        "On success the response body is empty (HTTP 204)."
    ),
    responses={
        204: {"description": "Project deleted successfully. No content returned."},
        404: {"description": "Project with the given ID does not exist."},
        409: {
            "description": "Cannot delete — the project has one or more visited places."
        },
    },
)
async def delete_project(
    project: Annotated[Project, Depends(get_project_or_404)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    try:
        await project_service.delete_project(db, project)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))