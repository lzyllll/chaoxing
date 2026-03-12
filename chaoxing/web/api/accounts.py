# -*- coding: utf-8 -*-
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import SQLModel, Session, select

from chaoxing.web.db import get_session
from chaoxing.web.models import Account, AccountStatus
from chaoxing.web.services import WebQueryService

router = APIRouter(tags=["dashboard"])
query_service = WebQueryService()


class CreateAccountRequest(SQLModel):
    name: str
    username: str
    passwordEncrypted: str = ""
    cookiesPath: str | None = None
    status: AccountStatus = AccountStatus.ACTIVE


@router.get("/dashboard/summary")
def get_dashboard_summary(session: Session = Depends(get_session)) -> dict[str, int]:
    return query_service.get_dashboard_summary(session)


@router.get("/accounts")
def list_accounts(session: Session = Depends(get_session)) -> list[dict]:
    return query_service.list_accounts(session)


@router.post("/accounts")
def create_account(payload: CreateAccountRequest, session: Session = Depends(get_session)) -> dict:
    name = payload.name.strip()
    username = payload.username.strip()
    if not name or not username:
        raise HTTPException(status_code=400, detail="name and username are required")

    existing = session.exec(select(Account).where(Account.username == username)).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Account username already exists")

    now = datetime.now(timezone.utc)
    default_cookie_path = str((Path(".runtime") / "accounts" / f"{username}.json").as_posix())
    cookies_path = (payload.cookiesPath or "").strip() or default_cookie_path
    account = Account(
        name=name,
        username=username,
        password_encrypted=payload.passwordEncrypted,
        cookies_path=cookies_path,
        status=payload.status,
        created_at=now,
        updated_at=now,
    )
    session.add(account)
    session.commit()
    session.refresh(account)

    if account.id is None:
        raise HTTPException(status_code=500, detail="Failed to create account")

    return {
        "id": account.id,
        "name": account.name,
        "username": account.username,
        "status": account.status,
        "lastLoginAt": None,
        "updatedAt": now.isoformat(),
        "courseCount": 0,
    }


@router.get("/accounts/{account_id}")
def get_account_detail(account_id: int, session: Session = Depends(get_session)) -> dict:
    detail = query_service.get_account_detail(session, account_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return detail
