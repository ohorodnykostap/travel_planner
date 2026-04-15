from typing import Annotated

from fastapi import Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import FAKE_USER_DB, _decode_token, oauth2_scheme
from app.core.database import get_db
from app.models.place import Place
from app.models.project import Project
from app.services import place_service, project_service


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> dict:
    payload = _decode_token(token)

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A refresh token cannot be used to authenticate requests. "
            "Use POST /auth/refresh to obtain a new access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username: str | None = payload.get("sub")
    if not username or username not in FAKE_USER_DB:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return FAKE_USER_DB[username]


async def get_project_or_404(
    project_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
) -> Project:
    project = await project_service.get_project_by_id(db, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with id={project_id} not found",
        )
    return project


async def get_place_or_404(
    project_id: int,
    place_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _user: Annotated[dict, Depends(get_current_user)],
) -> Place:
    place = await place_service.get_place_by_id(db, place_id, project_id=project_id)
    if place is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Place with id={place_id} not found in project {project_id}",
        )
    return place


class PaginationParams:
    def __init__(
        self,
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> None:
        self.page = page
        self.page_size = page_size
