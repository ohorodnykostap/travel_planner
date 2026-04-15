import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.core.auth import (
    FAKE_USER_DB,
    _blacklist_jti,
    _decode_token,
    _is_blacklisted,
    authenticate_user,
    create_token_pair,
)
from app.schemas.base import (
    MessageResponseSchema,
    RefreshRequestSchema,
    TokenResponseSchema,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/token",
    response_model=TokenResponseSchema,
    summary="Login — obtain access + refresh token pair",
    description=(
        "Exchange **username** and **password** for a token pair:\n\n"
        "| Token | Field | Lifetime (default) | Purpose |\n"
        "|---|---|---|---|\n"
        "| Access | `access_token` | 15 minutes | Authenticate API requests via `Authorization: Bearer` header |\n"
        "| Refresh | `refresh_token` | 30 days | Obtain a new token pair without re-entering credentials |\n\n"
        "Store the refresh token securely (e.g. `HttpOnly` cookie). "
        "When the access token expires, call `POST /auth/refresh` — "
        "**do not** re-enter credentials."
    ),
    responses={
        200: {"description": "Login successful. Both tokens returned."},
        401: {"description": "Incorrect username or password."},
    },
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> TokenResponseSchema:
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    logger.info("User '%s' logged in.", user["username"])
    return create_token_pair(user["username"])


@router.post(
    "/refresh",
    response_model=TokenResponseSchema,
    summary="Refresh — exchange refresh token for a new token pair",
    description=(
        "Present a valid **refresh token** in the request body to receive a "
        "brand-new access + refresh token pair.\n\n"
        "**Refresh token rotation** is enforced: the submitted refresh token is "
        "immediately blacklisted and can never be reused — even if intercepted. "
        "Always replace both stored tokens with the newly returned pair.\n\n"
        "Returns `401` if the token is:\n"
        "- expired\n"
        "- already used / revoked\n"
        "- not a refresh token (e.g. an access token was submitted by mistake)"
    ),
    responses={
        200: {"description": "Token pair refreshed successfully."},
        401: {
            "description": (
                "Invalid refresh token — expired, already used, revoked, "
                "or wrong token type."
            )
        },
    },
)
async def refresh_tokens(body: RefreshRequestSchema) -> TokenResponseSchema:
    payload = _decode_token(body.refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The provided token is not a refresh token",
        )

    jti: str | None = payload.get("jti")
    if not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed refresh token (missing jti)",
        )

    if _is_blacklisted(jti):
        logger.warning("Reuse of blacklisted refresh token jti=%s", jti)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has already been used or revoked. Please log in again",
        )

    username: str | None = payload.get("sub")
    if not username or username not in FAKE_USER_DB:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
        )

    exp_timestamp: int = payload["exp"]
    expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
    _blacklist_jti(jti, expires_at)

    logger.info("Token refreshed for user '%s' (old jti=%s blacklisted)", username, jti)
    return create_token_pair(username)


@router.post(
    "/logout",
    response_model=MessageResponseSchema,
    summary="Logout — revoke the refresh token",
    description=(
        "Invalidate the provided **refresh token** server-side by adding it to a "
        "blacklist. After a successful logout the token cannot be used to issue "
        "new pairs, even if it has not expired yet.\n\n"
        "The client is responsible for discarding the stored access token. "
        "Access tokens are stateless JWTs — they will naturally expire after "
        "`expires_in` seconds.\n\n"
        "**Note:** this endpoint intentionally does **not** require an `Authorization` "
        "header. A user whose access token has already expired must still be able to "
        "log out by presenting only their refresh token."
    ),
    responses={
        200: {
            "description": (
                "Logout successful. Returned even if the token was already expired "
                "or invalid — to avoid leaking token existence."
            )
        },
        400: {"description": "The provided token is not a refresh token."},
    },
)
async def logout(body: RefreshRequestSchema) -> MessageResponseSchema:
    try:
        payload = _decode_token(body.refresh_token)
    except HTTPException:
        return MessageResponseSchema(message="Logged out successfully")

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The provided token is not a refresh token",
        )

    jti: str | None = payload.get("jti")
    if jti and not _is_blacklisted(jti):
        exp_timestamp: int = payload.get("exp", 0)
        expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        _blacklist_jti(jti, expires_at)
        logger.info(
            "User '%s' logged out (jti=%s blacklisted)", payload.get("sub"), jti
        )

    return MessageResponseSchema(message="Logged out successfully")