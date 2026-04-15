import asyncio
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

from app.core.settings import settings


class TTLCache:
    def __init__(self, ttl: int = settings.CACHE_TTL_SECONDS) -> None:
        self._store: dict[str, tuple[Any, float]] = {}
        self._ttl = ttl
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        async with self._lock:
            ttl = ttl if ttl is not None else self._ttl
            self._store[key] = (value, time.monotonic() + ttl)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()

    @property
    def size(self) -> int:
        return len(self._store)


# Cache instance
artwork_cache = TTLCache(ttl=settings.CACHE_TTL_SECONDS)


# Cache decorator ("Caching responses from the third-party API" as a bonus)
def cached_artwork(ttl: int | None = None) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Build cache key from function name + all arguments
            cache_key = (
                f"{func.__module__}.{func.__qualname__}:{args}:{sorted(kwargs.items())}"
            )
            cached = await artwork_cache.get(cache_key)
            if cached is not None:
                return cached
            result = await func(*args, **kwargs)
            if result is not None:
                await artwork_cache.set(cache_key, result, ttl)
            return result

        return wrapper

    return decorator
