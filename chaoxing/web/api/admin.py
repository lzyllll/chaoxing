# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlmodel import SQLModel

from chaoxing.web.auth import (
    AdminSessionCookie,
    build_admin_session_payload,
    clear_admin_session_cookie,
    is_admin_auth_enabled,
    set_admin_session_cookie,
    verify_admin_credentials,
)
from chaoxing.web.settings import BackendSettings, get_backend_settings

router = APIRouter(tags=["admin"])


class AdminLoginRequest(SQLModel):
    username: str
    password: str


@router.get("/admin/session")
def get_admin_session(
    settings: Annotated[BackendSettings, Depends(get_backend_settings)],
    session_token: AdminSessionCookie = None,
) -> dict[str, object]:
    return build_admin_session_payload(session_token, settings)


@router.post("/admin/login")
def login_admin(
    payload: AdminLoginRequest,
    response: Response,
    settings: Annotated[BackendSettings, Depends(get_backend_settings)],
) -> dict[str, object]:
    if not is_admin_auth_enabled(settings):
        raise HTTPException(status_code=400, detail="Admin auth is not configured")

    username = payload.username.strip()
    if not verify_admin_credentials(username, payload.password, settings):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin credentials")

    set_admin_session_cookie(response, settings)
    return {
        "authEnabled": True,
        "authenticated": True,
        "username": settings.admin_username,
    }


@router.post("/admin/logout")
def logout_admin(
    response: Response,
    settings: Annotated[BackendSettings, Depends(get_backend_settings)],
) -> dict[str, object]:
    clear_admin_session_cookie(response)
    return {
        "authEnabled": is_admin_auth_enabled(settings),
        "authenticated": False,
        "username": None,
    }
