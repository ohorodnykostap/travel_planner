from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import get_current_user
from app.schemas.place import ArtworkInfoSchema
from app.services.artwork_service import get_artwork_by_id, search_artworks

router = APIRouter(
    prefix="/artworks",
    tags=["Artworks (AIC API Proxy)"],
)


@router.get(
    "/search",
    response_model=list[ArtworkInfoSchema],
    summary="Search artworks in the Art Institute of Chicago",
    description=(
        "Proxy a keyword search to the **Art Institute of Chicago (AIC) public API** "
        "and return matching artworks.\n\n"
        "Use this endpoint to **discover `external_id` values** before adding places "
        "to a project. The `id` field in each result is the value to pass as "
        "`external_id` when creating or adding a place.\n\n"
        "**Note:** search results are **not cached** because queries are too varied. "
        "For repeated lookups of a specific artwork, use `GET /artworks/{artwork_id}` "
        "which benefits from caching."
    ),
    responses={
        200: {
            "description": "List of matching artworks (may be empty if no results found)."
        },
        503: {
            "description": "Art Institute of Chicago API is temporarily unavailable."
        },
    },
)
async def search(
    q: Annotated[
        str,
        Query(
            min_length=1,
            description="Keyword search query, e.g. `monet`, `sunday afternoon`",
        ),
    ],
    _user: Annotated[dict, Depends(get_current_user)],
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=50,
            description="Maximum number of results to return. Defaults to 10.",
        ),
    ] = 10,
) -> list[ArtworkInfoSchema]:
    try:
        return await search_artworks(q, limit=limit)
    except (httpx.TimeoutException, httpx.RequestError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Art Institute of Chicago API is temporarily unavailable",
        )


@router.get(
    "/{artwork_id}",
    response_model=ArtworkInfoSchema,
    summary="Get a specific artwork by ID",
    description=(
        "Fetch detailed information for a single artwork from the "
        "**Art Institute of Chicago API** by its numeric ID.\n\n"
        "Responses are **cached in memory** for `CACHE_TTL_SECONDS` (default 1 hour), "
        "so repeated lookups of the same ID do not incur additional network calls.\n\n"
        "Useful for verifying an `external_id` before adding it to a project, or for "
        "displaying artwork details in the UI.\n\n"
        "**Known valid IDs for testing:**\n"
        "| ID | Title |\n"
        "|---|---|\n"
        "| `27992` | A Sunday on La Grande Jatte — Seurat |\n"
        "| `111628` | American Gothic — Grant Wood |\n"
        "| `80607` | The Old Guitarist — Picasso |\n"
        "| `16487` | Two Sisters (On the Terrace) — Renoir |\n"
        "| `28560` | The Assumption of the Virgin — El Greco |"
    ),
    responses={
        200: {"description": "Artwork found and returned with full metadata."},
        404: {"description": "No artwork with the given ID exists in the AIC API."},
        503: {
            "description": "Art Institute of Chicago API is temporarily unavailable."
        },
    },
)
async def get_artwork(
    artwork_id: int,
    _user: Annotated[dict, Depends(get_current_user)],
) -> ArtworkInfoSchema:
    try:
        artwork = await get_artwork_by_id(artwork_id)
    except (httpx.TimeoutException, httpx.RequestError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Art Institute of Chicago API is temporarily unavailable",
        )

    if artwork is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artwork with id={artwork_id} not found",
        )
    return artwork