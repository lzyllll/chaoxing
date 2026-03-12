# -*- coding: utf-8 -*-
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import SQLModel, Session

from chaoxing.web.db import get_session
from chaoxing.web.models import Account, TaskRun, TaskStatus
from chaoxing.web.services import WebQueryService

router = APIRouter(tags=["tasks"])
query_service = WebQueryService()


class CreateTaskRequest(SQLModel):
    accountId: int
    selectedCourses: list[str]


@router.get("/tasks")
def list_tasks(session: Session = Depends(get_session)) -> list[dict]:
    return query_service.list_tasks(session)


@router.post("/tasks")
def create_task(payload: CreateTaskRequest, session: Session = Depends(get_session)) -> dict:
    account = session.get(Account, payload.accountId)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")

    selected_courses = [course_id.strip() for course_id in payload.selectedCourses if course_id.strip()]
    if not selected_courses:
        raise HTTPException(status_code=400, detail="selectedCourses cannot be empty")

    task = TaskRun(
        account_id=payload.accountId,
        status=TaskStatus.QUEUED,
        selected_courses_json=json.dumps(selected_courses, ensure_ascii=False),
    )
    session.add(task)
    session.commit()
    session.refresh(task)

    account_names = query_service._account_name_map(session)
    return query_service._serialize_task(task, account_names)


@router.get("/tasks/{task_id}")
def get_task_detail(task_id: int, session: Session = Depends(get_session)) -> dict:
    detail = query_service.get_task_detail(session, task_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return detail
