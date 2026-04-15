import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.settings import settings
from app.schemas.base import TokenResponseSchema

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


_refresh_blacklist: dict[str, datetime] = {}


def _prune_blacklist() -> None:
    now = datetime.now(timezone.utc)
    expired = [jti for jti, exp in _refresh_blacklist.items() if exp <= now]
    for jti in expired:
        del _refresh_blacklist[jti]


def _blacklist_jti(jti: str, expires_at: datetime) -> None:
    _prune_blacklist()
    _refresh_blacklist[jti] = expires_at


def _is_blacklisted(jti: str) -> bool:
    _prune_blacklist()
    return jti in _refresh_blacklist


FAKE_USER_DB: dict[str, dict] = {
    settings.ADMIN_USERNAME: {
        "username": settings.ADMIN_USERNAME,
        "hashed_password": pwd_context.hash(settings.ADMIN_PASSWORD),
    }
}


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def authenticate_user(username: str, password: str) -> dict | None:
    user = FAKE_USER_DB.get(username)
    if not user or not verify_password(password, user["hashed_password"]):
        return None
    return user


def _make_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    jti: str | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "jti": jti or str(uuid.uuid4()),
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_token_pair(username: str) -> TokenResponseSchema:
    access_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    access_token = _make_token(username, "access", access_delta)
    refresh_token = _make_token(username, "refresh", refresh_delta)

    return TokenResponseSchema(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(access_delta.total_seconds()),
    )


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        logger.debug("JWT decode failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
