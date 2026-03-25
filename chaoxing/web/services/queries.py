# -*- coding: utf-8 -*-
import json
from datetime import datetime
from typing import Any

from sqlmodel import Session, col, func, select

from chaoxing.web.models import (
    Account,
    AccountStudyConfig,
    AnswerRecord,
    CourseSnapshot,
    PendingDecision,
    TaskEvent,
    TaskLog,
    TaskRun,
    TaskStatus,
)


class WebQueryService:
    def get_dashboard_summary(self, session: Session) -> dict[str, int]:
        account_count = session.exec(select(func.count()).select_from(Account)).one()
        active_task_count = session.exec(
            select(func.count()).select_from(TaskRun).where(
                col(TaskRun.status).in_([TaskStatus.QUEUED, TaskStatus.RUNNING, TaskStatus.WAITING_CONFIRMATION])
            )
        ).one()
        pending_decision_count = session.exec(
            select(func.count()).select_from(PendingDecision).where(PendingDecision.status == "pending")
        ).one()
        total_task_count = session.exec(select(func.count()).select_from(TaskRun)).one()
        succeeded_task_count = session.exec(
            select(func.count()).select_from(TaskRun).where(TaskRun.status == TaskStatus.SUCCEEDED)
        ).one()
        success_rate = 0
        if total_task_count:
            success_rate = round((succeeded_task_count / total_task_count) * 100)

        return {
            "accountCount": int(account_count or 0),
            "activeTaskCount": int(active_task_count or 0),
            "pendingDecisionCount": int(pending_decision_count or 0),
            "successRate": int(success_rate),
        }

    def list_accounts(self, session: Session) -> list[dict[str, Any]]:
        accounts = session.exec(select(Account).order_by(Account.id)).all()
        course_counts = {
            account_id: count
            for account_id, count in session.exec(
                select(CourseSnapshot.account_id, func.count())
                .group_by(CourseSnapshot.account_id)
            ).all()
        }

        return [
            {
                "id": account.id,
                "name": account.name,
                "username": account.username,
                "status": account.status,
                "lastLoginAt": self._iso(account.last_login_at),
                "updatedAt": self._iso(account.updated_at),
                "courseCount": int(course_counts.get(account.id or 0, 0)),
            }
            for account in accounts
            if account.id is not None
        ]

    def get_account_detail(self, session: Session, account_id: int) -> dict[str, Any] | None:
        account = session.get(Account, account_id)
        if account is None or account.id is None:
            return None

        config = session.exec(
            select(AccountStudyConfig).where(AccountStudyConfig.account_id == account_id)
        ).first()
        courses = session.exec(
            select(CourseSnapshot)
            .where(CourseSnapshot.account_id == account_id)
            .order_by(CourseSnapshot.fetched_at.desc(), CourseSnapshot.id)
        ).all()

        return {
            "account": {
                "id": account.id,
                "name": account.name,
                "username": account.username,
                "passwordEncrypted": account.password_encrypted,
                "cookiesPath": account.cookies_path,
                "status": account.status,
                "lastLoginAt": self._iso(account.last_login_at),
                "updatedAt": self._iso(account.updated_at),
                "courseCount": len(courses),
            },
            "config": {
                "speed": config.speed if config else 1.0,
                "jobs": config.jobs if config else 4,
                "notopenAction": config.notopen_action if config else "retry",
                "answerProvider": config.answer_provider if config else "",
                "submissionMode": config.submission_mode if config else "intelligent",
                "confidenceThreshold": config.confidence_threshold if config else 0.8,
                "minCoverRate": config.min_cover_rate if config else 0.7,
                "allowAiAutoSubmit": config.allow_ai_auto_submit if config else False,
                "lowConfidenceAction": config.low_confidence_action if config else "pause",
                "providerConfigJson": config.provider_config_json if config else "{}",
            },
            "courses": [
                {
                    "id": course.id,
                    "accountId": course.account_id,
                    "courseId": course.course_id,
                    "clazzId": course.clazz_id,
                    "cpi": course.cpi,
                    "title": course.title,
                    "teacher": course.teacher,
                    "fetchedAt": self._iso(course.fetched_at),
                }
                for course in courses
                if course.id is not None
            ],
        }

    def list_tasks(self, session: Session) -> list[dict[str, Any]]:
        tasks = session.exec(select(TaskRun).order_by(TaskRun.created_at.desc(), TaskRun.id.desc())).all()
        account_names = self._account_name_map(session)
        return [self._serialize_task(task, account_names) for task in tasks if task.id is not None]

    def get_task_detail(self, session: Session, task_id: int) -> dict[str, Any] | None:
        task = session.get(TaskRun, task_id)
        if task is None or task.id is None:
            return None

        account_names = self._account_name_map(session)
        events = session.exec(
            select(TaskEvent)
            .where(TaskEvent.task_id == task_id)
            .order_by(TaskEvent.seq.asc(), TaskEvent.id.asc())
        ).all()
        logs = session.exec(
            select(TaskLog)
            .where(TaskLog.task_id == task_id)
            .order_by(TaskLog.created_at.asc(), TaskLog.id.asc())
        ).all()
        answers = session.exec(
            select(AnswerRecord)
            .where(AnswerRecord.task_id == task_id)
            .order_by(AnswerRecord.created_at.desc(), AnswerRecord.id.desc())
        ).all()

        return {
            "task": self._serialize_task(task, account_names),
            "events": [
                {
                    "id": event.id,
                    "taskId": event.task_id,
                    "seq": event.seq,
                    "eventType": event.event_type,
                    "createdAt": self._iso(event.created_at),
                    "payload": self._from_json(event.payload_json, default={}),
                }
                for event in events
                if event.id is not None
            ],
            "logs": [
                {
                    "id": log.id,
                    "taskId": log.task_id,
                    "level": log.level,
                    "message": log.message,
                    "createdAt": self._iso(log.created_at),
                }
                for log in logs
                if log.id is not None
            ],
            "answers": [
                {
                    "id": answer.id,
                    "taskId": answer.task_id,
                    "courseTitle": answer.course_title,
                    "chapterTitle": answer.chapter_title,
                    "questionId": answer.question_id,
                    "questionType": answer.question_type,
                    "questionTitle": answer.question_title,
                    "options": self._from_json(answer.options_json, default=[]),
                    "candidateAnswers": self._from_json(answer.candidate_answers_json, default=[]),
                    "finalAnswer": answer.final_answer,
                    "answerSource": answer.answer_source,
                    "confidence": answer.confidence,
                    "decision": answer.decision,
                    "submitResult": answer.submit_result,
                    "createdAt": self._iso(answer.created_at),
                }
                for answer in answers
                if answer.id is not None
            ],
        }

    def list_pending_decisions(self, session: Session) -> list[dict[str, Any]]:
        decisions = session.exec(
            select(PendingDecision)
            .order_by(PendingDecision.created_at.desc(), PendingDecision.id.desc())
        ).all()
        return [
            {
                "id": decision.id,
                "taskId": decision.task_id,
                "answerRecordId": decision.answer_record_id,
                "reason": decision.reason,
                "status": decision.status,
                "createdAt": self._iso(decision.created_at),
            }
            for decision in decisions
            if decision.id is not None
        ]

    def get_task_stream_snapshot(self, session: Session, task_id: int) -> dict[str, Any] | None:
        detail = self.get_task_detail(session, task_id)
        if detail is None:
            return None

        return {
            "type": "snapshot",
            "task": detail["task"],
            "events": detail["events"],
            "logs": detail["logs"],
            "answers": detail["answers"],
        }

    def _account_name_map(self, session: Session) -> dict[int, str]:
        accounts = session.exec(select(Account.id, Account.name)).all()
        return {account_id: name for account_id, name in accounts if account_id is not None}

    def _serialize_task(self, task: TaskRun, account_names: dict[int, str]) -> dict[str, Any]:
        return {
            "id": task.id,
            "accountId": task.account_id,
            "accountName": account_names.get(task.account_id, f"账号#{task.account_id}"),
            "status": task.status,
            "selectedCourses": self._from_json(task.selected_courses_json, default=[]),
            "progressPct": task.progress_pct,
            "currentCourse": task.current_course,
            "currentChapter": task.current_chapter,
            "currentJob": task.current_job,
            "errorMessage": task.error_message,
            "createdAt": self._iso(task.created_at),
            "startedAt": self._iso(task.started_at),
            "finishedAt": self._iso(task.finished_at),
        }

    @staticmethod
    def _from_json(value: str | None, *, default: Any) -> Any:
        if not value:
            return default
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default

    @staticmethod
    def _iso(value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.isoformat()
