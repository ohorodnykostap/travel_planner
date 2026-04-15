import logging

import httpx

from app.core.cache import cached_artwork
from app.core.settings import settings
from app.schemas.place import ArtworkInfoSchema

logger = logging.getLogger(__name__)

IIIF_BASE = "https://www.artic.edu/iiif/2"

_ARTWORK_FIELDS = (
    "id,title,artist_display,image_id,date_display,medium_display,place_of_origin"
)


def _build_thumbnail_url(image_id: str | None) -> str | None:
    if not image_id:
        return None
    return f"{IIIF_BASE}/{image_id}/full/200,/0/default.jpg"


def _parse_artwork(data: dict) -> ArtworkInfoSchema:
    image_id = data.get("image_id")
    return ArtworkInfoSchema(
        id=data["id"],
        title=data.get("title"),
        artist_display=data.get("artist_display"),
        image_id=image_id,
        date_display=data.get("date_display"),
        medium_display=data.get("medium_display"),
        place_of_origin=data.get("place_of_origin"),
        thumbnail_url=_build_thumbnail_url(image_id),
    )


@cached_artwork()
async def get_artwork_by_id(artwork_id: int) -> ArtworkInfoSchema | None:
    url = f"{settings.ARTIC_BASE_URL}/artworks/{artwork_id}"
    params = {"fields": _ARTWORK_FIELDS}

    try:
        async with httpx.AsyncClient(timeout=settings.ARTIC_REQUEST_TIMEOUT) as client:
            response = await client.get(url, params=params)

        if response.status_code == 404:
            logger.info("Artwork %s not found in AIC API (404).", artwork_id)
            return None

        response.raise_for_status()
        data = response.json().get("data", {})
        if not data:
            return None

        return _parse_artwork(data)

    except httpx.TimeoutException:
        logger.error("Timeout while fetching artwork %s from AIC API.", artwork_id)
        raise
    except httpx.HTTPStatusError as exc:
        logger.error(
            "HTTP error %s while fetching artwork %s.",
            exc.response.status_code,
            artwork_id,
        )
        raise
    except httpx.RequestError as exc:
        logger.error("Request error while fetching artwork %s: %s", artwork_id, exc)
        raise


async def search_artworks(query: str, limit: int = 10) -> list[ArtworkInfoSchema]:
    url = f"{settings.ARTIC_BASE_URL}/artworks/search"
    params = {"q": query, "limit": limit, "fields": _ARTWORK_FIELDS}

    try:
        async with httpx.AsyncClient(timeout=settings.ARTIC_REQUEST_TIMEOUT) as client:
            response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json().get("data", [])
        return [_parse_artwork(item) for item in data]

    except httpx.TimeoutException:
        logger.error("Timeout while searching artworks (query=%r).", query)
        raise
    except httpx.HTTPStatusError as exc:
        logger.error(
            "HTTP error %s while searching artworks (query=%r).",
            exc.response.status_code,
            query,
        )
        raise
    except httpx.RequestError as exc:
        logger.error("Request error while searching artworks: %s", exc)
        raise
