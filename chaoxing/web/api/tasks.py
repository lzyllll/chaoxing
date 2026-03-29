# -*- coding: utf-8 -*-
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import SQLModel, Session, select

from chaoxing.web.db import get_session
from chaoxing.web.models import Account, CourseSnapshot, TaskRun, TaskStatus
from chaoxing.web.services.queries import WebQueryService
from chaoxing.web.services.runtime import task_runtime_service

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
    if account.status != "active":
        raise HTTPException(status_code=400, detail="Account is disabled")

    selected_courses = [course_id.strip() for course_id in payload.selectedCourses if course_id.strip()]
    if not selected_courses:
        raise HTTPException(status_code=400, detail="selectedCourses cannot be empty")

    available_courses = session.exec(
        select(CourseSnapshot.course_id).where(CourseSnapshot.account_id == payload.accountId)
    ).all()
    available_course_ids = {course_id for course_id in available_courses}
    if not available_course_ids:
        raise HTTPException(status_code=400, detail="Please sync account courses first")

    missing_courses = [course_id for course_id in selected_courses if course_id not in available_course_ids]
    if missing_courses:
        raise HTTPException(status_code=400, detail=f"Unknown selected courses: {', '.join(missing_courses)}")

    task = TaskRun(
        account_id=payload.accountId,
        status=TaskStatus.QUEUED,
        selected_courses_json=json.dumps(selected_courses, ensure_ascii=False),
    )
    session.add(task)
    session.commit()
    session.refresh(task)

    if task.id is None:
        raise HTTPException(status_code=500, detail="Failed to create task")

    task_runtime_service.start_task(task.id)

    account_names = query_service._account_name_map(session)
    return query_service._serialize_task(task, account_names)


@router.get("/tasks/{task_id}")
def get_task_detail(task_id: int, session: Session = Depends(get_session)) -> dict:
    detail = query_service.get_task_detail(session, task_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return detail


@router.delete("/tasks/{task_id}")
def delete_task(task_id: int) -> dict[str, bool]:
    try:
        task_runtime_service.delete_task(task_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return {"ok": True}
