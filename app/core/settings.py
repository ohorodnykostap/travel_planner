from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    APP_NAME: str = "Travel Planner API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./travel_planner.db"

    # Security
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Default admin creds
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "secret"

    # External API
    ARTIC_BASE_URL: str = "https://api.artic.edu/api/v1"
    ARTIC_REQUEST_TIMEOUT: float = 10.0

    # Cache
    CACHE_TTL_SECONDS: int = 3600

    # Business rules
    MAX_PLACES_PER_PROJECT: int = 10
    MIN_PLACES_PER_PROJECT: int = 1


settings = Settings()
