# -*- coding: utf-8 -*-
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import SQLModel, Session, select

from chaoxing.web.db import get_session
from chaoxing.web.models import Account, AccountStatus
from chaoxing.web.settings import default_account_cookies_path
from chaoxing.web.services import WebQueryService, task_runtime_service

router = APIRouter(tags=["dashboard"])
query_service = WebQueryService()


class CreateAccountRequest(SQLModel):
    name: str
    username: str
    passwordEncrypted: str = ""
    cookiesPath: str | None = None
    status: AccountStatus = AccountStatus.ACTIVE


class UpdateAccountStudyConfigRequest(SQLModel):
    speed: float = 1.0
    jobs: int = 4
    notopenAction: str = "retry"
    answerProvider: str = ""
    submissionMode: str = "intelligent"
    confidenceThreshold: float = 0.8
    minCoverRate: float = 0.7
    allowAiAutoSubmit: bool = False
    lowConfidenceAction: str = "pause"
    providerConfigJson: str = "{}"


class UpdateAccountRequest(CreateAccountRequest):
    config: UpdateAccountStudyConfigRequest = UpdateAccountStudyConfigRequest()


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
    default_cookie_path = default_account_cookies_path(username).as_posix()
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
        "passwordEncrypted": account.password_encrypted,
        "cookiesPath": account.cookies_path,
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


@router.put("/accounts/{account_id}")
def update_account(
    account_id: int,
    payload: UpdateAccountRequest,
    session: Session = Depends(get_session),
) -> dict:
    account = session.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")

    name = payload.name.strip()
    username = payload.username.strip()
    if not name or not username:
        raise HTTPException(status_code=400, detail="name and username are required")

    existing = session.exec(select(Account).where(Account.username == username, Account.id != account_id)).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Account username already exists")

    now = datetime.now(timezone.utc)
    default_cookie_path = default_account_cookies_path(username).as_posix()
    account.name = name
    account.username = username
    account.password_encrypted = payload.passwordEncrypted
    account.cookies_path = (payload.cookiesPath or "").strip() or default_cookie_path
    account.status = payload.status
    account.updated_at = now
    session.add(account)

    config = task_runtime_service.ensure_account_config(session, account_id)
    config.speed = payload.config.speed
    config.jobs = payload.config.jobs
    config.notopen_action = payload.config.notopenAction
    config.answer_provider = payload.config.answerProvider
    config.submission_mode = payload.config.submissionMode
    config.confidence_threshold = payload.config.confidenceThreshold
    config.min_cover_rate = payload.config.minCoverRate
    config.allow_ai_auto_submit = payload.config.allowAiAutoSubmit
    config.low_confidence_action = payload.config.lowConfidenceAction
    config.provider_config_json = payload.config.providerConfigJson
    config.updated_at = now
    session.add(config)
    session.commit()

    detail = query_service.get_account_detail(session, account_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return detail


@router.post("/accounts/{account_id}/sync-courses")
def sync_account_courses(account_id: int, session: Session = Depends(get_session)) -> dict:
    try:
        result = task_runtime_service.sync_account_courses(account_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session.expire_all()
    detail = query_service.get_account_detail(session, account_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return {
        "summary": result,
        "detail": detail,
    }


@router.delete("/accounts/{account_id}")
def delete_account(account_id: int) -> dict[str, bool]:
    try:
        task_runtime_service.delete_account(account_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return {"ok": True}
