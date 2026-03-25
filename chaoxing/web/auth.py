# -*- coding: utf-8 -*-
import base64
import hashlib
import hmac
import time
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Response, WebSocket
from starlette import status

from chaoxing.web.settings import BackendSettings, get_backend_settings

SESSION_COOKIE_NAME = "chaoxing_admin_session"
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60
AdminSessionCookie = Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)]


def is_admin_auth_enabled(settings: BackendSettings) -> bool:
    return bool(settings.admin_username and settings.admin_password)


def verify_admin_credentials(username: str, password: str, settings: BackendSettings) -> bool:
    if not is_admin_auth_enabled(settings):
        return False

    return hmac.compare_digest(username, settings.admin_username) and hmac.compare_digest(
        password,
        settings.admin_password,
    )


def _get_session_secret(settings: BackendSettings) -> bytes:
    source = f"{settings.config_path}:{settings.admin_username}:{settings.admin_password}"
    return hashlib.sha256(source.encode("utf8")).digest()


def _encode_token(username: str, expires_at: int, signature: str) -> str:
    payload = f"{username}\n{expires_at}\n{signature}".encode("utf8")
    return base64.urlsafe_b64encode(payload).decode("ascii")


def _decode_token(token: str) -> tuple[str, int, str] | None:
    try:
        decoded = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf8")
    except (ValueError, UnicodeDecodeError):
        return None

    parts = decoded.split("\n")
    if len(parts) != 3:
        return None

    username, expires_at_raw, signature = parts
    try:
        expires_at = int(expires_at_raw)
    except ValueError:
        return None

    return username, expires_at, signature


def create_admin_session_token(settings: BackendSettings) -> str:
    expires_at = int(time.time()) + SESSION_TTL_SECONDS
    payload = f"{settings.admin_username}\n{expires_at}"
    signature = hmac.new(
        _get_session_secret(settings),
        payload.encode("utf8"),
        hashlib.sha256,
    ).hexdigest()
    return _encode_token(settings.admin_username, expires_at, signature)


def is_admin_session_authenticated(token: str | None, settings: BackendSettings) -> bool:
    if not is_admin_auth_enabled(settings):
        return True
    if not token:
        return False

    decoded = _decode_token(token)
    if decoded is None:
        return False

    username, expires_at, signature = decoded
    if username != settings.admin_username or expires_at < int(time.time()):
        return False

    payload = f"{username}\n{expires_at}"
    expected_signature = hmac.new(
        _get_session_secret(settings),
        payload.encode("utf8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)


def build_admin_session_payload(token: str | None, settings: BackendSettings) -> dict[str, object]:
    auth_enabled = is_admin_auth_enabled(settings)
    authenticated = is_admin_session_authenticated(token, settings)
    username = settings.admin_username if auth_enabled and authenticated else None
    return {
        "authEnabled": auth_enabled,
        "authenticated": authenticated,
        "username": username,
    }


def set_admin_session_cookie(response: Response, settings: BackendSettings) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=create_admin_session_token(settings),
        httponly=True,
        max_age=SESSION_TTL_SECONDS,
        samesite="lax",
        secure=False,
        path="/",
    )


def clear_admin_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")


def require_admin_session(
    settings: Annotated[BackendSettings, Depends(get_backend_settings)],
    session_token: AdminSessionCookie = None,
) -> None:
    if is_admin_session_authenticated(session_token, settings):
        return
    raise HTTPException(status_code=401, detail="Admin login required")


async def ensure_admin_websocket_session(websocket: WebSocket) -> bool:
    settings = get_backend_settings()
    if is_admin_session_authenticated(websocket.cookies.get(SESSION_COOKIE_NAME), settings):
        return True

    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    return False


__all__ = [
    "AdminSessionCookie",
    "SESSION_COOKIE_NAME",
    "build_admin_session_payload",
    "clear_admin_session_cookie",
    "ensure_admin_websocket_session",
    "is_admin_auth_enabled",
    "require_admin_session",
    "set_admin_session_cookie",
    "verify_admin_credentials",
]
