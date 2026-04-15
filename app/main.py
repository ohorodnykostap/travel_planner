import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.settings import settings
from app.router.artworks import router as artworks_router
from app.router.auth import router as auth_router
from app.router.places import router as places_router
from app.router.projects import router as projects_router

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(places_router)
app.include_router(artworks_router)


@app.get("/health", tags=["Health"], summary="Health check")
async def health_check() -> dict:
    return {"status": "ok", "version": settings.APP_VERSION}