# -*- coding: utf-8 -*-
import json
import threading
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlmodel import delete, func, select

from chaoxing.core.exceptions import LoginError
from chaoxing.services.runner import init_chaoxing, process_course, sanitize_common_config
from chaoxing.web.db import session_context
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
from chaoxing.web.settings import load_backend_config


@dataclass
class TaskRuntimeState:
    total_courses: int = 0
    completed_course_ids: set[str] = field(default_factory=set)
    current_course_id: str = ""
    current_course_title: str = ""
    current_course_total_points: int = 0
    completed_chapter_ids: set[str] = field(default_factory=set)
    current_chapter_id: str = ""
    current_chapter_title: str = ""
    current_job_name: str = ""
    current_video_progress_pct: float = 0.0
    last_video_progress_pct: float = -1.0
    last_video_event_at: float = 0.0


class TaskRuntimeService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._threads: dict[int, threading.Thread] = {}
        self._event_counters: dict[int, int] = {}
        self._states: dict[int, TaskRuntimeState] = {}

    def ensure_account_config(self, session, account_id: int) -> AccountStudyConfig:
        config = session.exec(
            select(AccountStudyConfig).where(AccountStudyConfig.account_id == account_id)
        ).first()
        if config is not None:
            return config

        config = AccountStudyConfig(account_id=account_id)
        session.add(config)
        session.flush()
        return config

    def sync_account_courses(self, account_id: int) -> dict[str, Any]:
        with session_context() as session:
            account = session.get(Account, account_id)
            if account is None:
                raise LookupError("Account not found")

            config = self.ensure_account_config(session, account_id)
            session.commit()
            account_data = self._account_payload(account)
            config_data = self._config_payload(config)

            chaoxing = self._build_chaoxing(
                account=account_data,
                config=config_data,
                selected_courses=None,
                tiku_config={"provider": ""},
            )
            login_state = chaoxing.login(login_with_cookies=True)
            if not login_state["status"]:
                raise LoginError(login_state["msg"])

            courses = chaoxing.get_course_list()
            self._store_course_snapshots(session, account, courses)
            session.refresh(account)
            return {
                "accountId": account_id,
                "courseCount": len(courses),
                "fetchedAt": account.updated_at.isoformat() if account.updated_at else None,
            }

    def start_task(self, task_id: int) -> None:
        with self._lock:
            active = self._threads.get(task_id)
            if active is not None and active.is_alive():
                return

            self._states[task_id] = TaskRuntimeState()
            self._event_counters[task_id] = self._load_event_seq(task_id)

            thread = threading.Thread(
                target=self._run_task,
                args=(task_id,),
                name=f"web-task-{task_id}",
                daemon=True,
            )
            self._threads[task_id] = thread
            thread.start()

    def recover_interrupted_tasks(self) -> int:
        recovered_count = 0
        recovered_at = datetime.now(timezone.utc)

        with session_context() as session:
            tasks = session.exec(
                select(TaskRun).where(TaskRun.status.in_([TaskStatus.QUEUED, TaskStatus.RUNNING]))
            ).all()

            for task in tasks:
                if task.id is None:
                    continue

                if task.status == TaskStatus.RUNNING:
                    task.status = TaskStatus.FAILED
                    task.error_message = "任务因服务重启或异常退出中断，请重新创建任务"
                else:
                    task.status = TaskStatus.CANCELLED
                    task.error_message = "任务在启动前因服务重启或异常退出被取消，请重新创建任务"

                task.finished_at = recovered_at
                task.current_job = ""
                session.add(task)
                session.add(
                    TaskLog(
                        task_id=task.id,
                        level="warning",
                        message=task.error_message,
                        context_json=json.dumps({"recoveredAt": recovered_at.isoformat()}, ensure_ascii=False),
                    )
                )
                recovered_count += 1

            if recovered_count:
                session.commit()

        return recovered_count

    def append_log(self, task_id: int, level: str, message: str, context: dict[str, Any] | None = None) -> None:
        payload = json.dumps(context or {}, ensure_ascii=False)
        with session_context() as session:
            session.add(
                TaskLog(
                    task_id=task_id,
                    level=level.lower(),
                    message=message,
                    context_json=payload,
                )
            )
            session.commit()

    def handle_runtime_event(self, task_id: int, event_type: str, payload: dict[str, Any]) -> None:
        persist_event = event_type != "video_progress"
        task_updates: dict[str, Any] = {}
        event_payload = dict(payload)

        with self._lock:
            state = self._states.setdefault(task_id, TaskRuntimeState())
            now = time.monotonic()

            if event_type == "course_started":
                state.current_course_id = str(payload.get("courseId") or "")
                state.current_course_title = str(payload.get("courseTitle") or "")
                state.current_course_total_points = 0
                state.completed_chapter_ids = set()
                state.current_chapter_id = ""
                state.current_chapter_title = ""
                state.current_job_name = ""
                state.current_video_progress_pct = 0.0
                task_updates["current_course"] = state.current_course_title
                task_updates["current_chapter"] = ""
                task_updates["current_job"] = ""

            elif event_type == "course_points_loaded":
                state.current_course_total_points = int(payload.get("totalPoints") or 0)

            elif event_type == "chapter_started":
                state.current_chapter_id = str(payload.get("chapterId") or "")
                state.current_chapter_title = str(payload.get("chapterTitle") or "")
                state.current_job_name = ""
                state.current_video_progress_pct = 0.0
                task_updates["current_chapter"] = state.current_chapter_title
                task_updates["current_job"] = ""

            elif event_type == "chapter_completed":
                chapter_id = str(payload.get("chapterId") or "")
                if chapter_id and chapter_id not in state.completed_chapter_ids:
                    state.completed_chapter_ids.add(chapter_id)
                state.current_video_progress_pct = 0.0

            elif event_type == "chapter_not_open":
                state.current_video_progress_pct = 0.0

            elif event_type == "job_started":
                state.current_job_name = str(payload.get("jobName") or payload.get("jobType") or "")
                task_updates["current_job"] = state.current_job_name

            elif event_type == "job_completed":
                if payload.get("jobType") != "video":
                    state.current_video_progress_pct = 0.0
                state.current_job_name = str(payload.get("jobName") or state.current_job_name)
                task_updates["current_job"] = state.current_job_name

            elif event_type == "job_failed":
                state.current_job_name = str(payload.get("jobName") or state.current_job_name)
                task_updates["current_job"] = f"{state.current_job_name} 失败".strip()

            elif event_type == "video_progress":
                progress_pct = float(payload.get("progressPct") or 0.0)
                task_updates["current_job"] = f"{payload.get('jobName') or '视频任务'} {progress_pct:.1f}%"
                should_persist = (
                    progress_pct >= 99.9
                    or progress_pct - state.last_video_progress_pct >= 2
                    or now - state.last_video_event_at >= 1.0
                )
                if should_persist:
                    state.last_video_event_at = now
                    state.last_video_progress_pct = progress_pct
                    persist_event = True
                state.current_video_progress_pct = progress_pct

            elif event_type == "video_completed":
                state.current_video_progress_pct = 100.0
                task_updates["current_job"] = f"{payload.get('jobName') or '视频任务'} 已完成"

            elif event_type == "course_completed":
                course_id = str(payload.get("courseId") or state.current_course_id)
                if course_id:
                    state.completed_course_ids.add(course_id)
                state.current_video_progress_pct = 0.0
                state.current_chapter_id = ""
                state.current_chapter_title = ""
                state.current_job_name = ""
                task_updates["current_chapter"] = ""
                task_updates["current_job"] = ""

            task_updates["progress_pct"] = self._calculate_progress(state)

        if persist_event:
            self._append_event(task_id, event_type, event_payload)
        self._update_task_fields(task_id, **task_updates)

    def cleanup_task(self, task_id: int) -> None:
        with self._lock:
            self._threads.pop(task_id, None)
            self._states.pop(task_id, None)
            self._event_counters.pop(task_id, None)

    def is_task_active(self, task_id: int) -> bool:
        with self._lock:
            thread = self._threads.get(task_id)
            return thread is not None and thread.is_alive()

    def delete_task(self, task_id: int) -> None:
        with session_context() as session:
            task = session.get(TaskRun, task_id)
            if task is None:
                raise LookupError("Task not found")

            if self.is_task_active(task_id) or task.status in {TaskStatus.QUEUED, TaskStatus.RUNNING}:
                raise RuntimeError("Task is still running and cannot be deleted")

            session.exec(delete(PendingDecision).where(PendingDecision.task_id == task_id))
            session.exec(delete(AnswerRecord).where(AnswerRecord.task_id == task_id))
            session.exec(delete(TaskLog).where(TaskLog.task_id == task_id))
            session.exec(delete(TaskEvent).where(TaskEvent.task_id == task_id))
            session.exec(delete(TaskRun).where(TaskRun.id == task_id))
            session.commit()

        self.cleanup_task(task_id)

    def delete_account(self, account_id: int) -> None:
        with session_context() as session:
            account = session.get(Account, account_id)
            if account is None:
                raise LookupError("Account not found")

            tasks = session.exec(select(TaskRun).where(TaskRun.account_id == account_id)).all()
            task_ids = [task.id for task in tasks if task.id is not None]
            active_task_ids = [
                task.id
                for task in tasks
                if task.id is not None and (self.is_task_active(task.id) or task.status in {TaskStatus.QUEUED, TaskStatus.RUNNING})
            ]
            if active_task_ids:
                raise RuntimeError("Account has running tasks and cannot be deleted")

            cookies_path = account.cookies_path
            if task_ids:
                session.exec(delete(PendingDecision).where(PendingDecision.task_id.in_(task_ids)))
                session.exec(delete(AnswerRecord).where(AnswerRecord.task_id.in_(task_ids)))
                session.exec(delete(TaskLog).where(TaskLog.task_id.in_(task_ids)))
                session.exec(delete(TaskEvent).where(TaskEvent.task_id.in_(task_ids)))
                session.exec(delete(TaskRun).where(TaskRun.account_id == account_id))

            session.exec(delete(CourseSnapshot).where(CourseSnapshot.account_id == account_id))
            session.exec(delete(AccountStudyConfig).where(AccountStudyConfig.account_id == account_id))
            session.exec(delete(Account).where(Account.id == account_id))
            session.commit()

        for task_id in task_ids:
            self.cleanup_task(task_id)
        self._delete_cookie_file(cookies_path)

    @staticmethod
    def _delete_cookie_file(cookies_path: str | None) -> None:
        if not cookies_path:
            return
        try:
            path = Path(cookies_path)
            if path.exists():
                path.unlink()
        except OSError:
            pass

    def _run_task(self, task_id: int) -> None:
        try:
            with session_context() as session:
                task = session.get(TaskRun, task_id)
                if task is None:
                    return

                account = session.get(Account, task.account_id)
                if account is None:
                    raise LookupError("Account not found")

                config = self.ensure_account_config(session, account.id or 0)
                session.commit()
                account_data = self._account_payload(account)
                config_data = self._config_payload(config)

                selected_courses = self._selected_courses(task.selected_courses_json)
                if not selected_courses:
                    raise ValueError("selectedCourses cannot be empty")

                now = datetime.now(timezone.utc)
                task.status = TaskStatus.RUNNING
                task.started_at = now
                task.finished_at = None
                task.error_message = ""
                task.progress_pct = 0.0
                task.current_course = ""
                task.current_chapter = ""
                task.current_job = ""
                session.add(task)
                session.commit()

            self.append_log(task_id, "info", "任务已开始，准备登录账号")
            self._append_event(task_id, "task_started", {"taskId": task_id})

            tiku_config = self._load_tiku_config(config_data)
            chaoxing = self._build_chaoxing(
                account=account_data,
                config=config_data,
                selected_courses=selected_courses,
                tiku_config=tiku_config,
                task_id=task_id,
            )

            login_state = chaoxing.login(login_with_cookies=True)
            if not login_state["status"]:
                raise LoginError(login_state["msg"])

            all_courses = chaoxing.get_course_list()
            with session_context() as session:
                session_account = session.get(Account, account_data["id"])
                if session_account is not None:
                    self._store_course_snapshots(session, session_account, all_courses)

            course_map = {str(course.get("courseId")): course for course in all_courses}
            course_queue = [course_map[course_id] for course_id in selected_courses if course_id in course_map]
            if not course_queue:
                raise ValueError("未找到已选择的课程，请先同步课程列表")

            with self._lock:
                self._states.setdefault(task_id, TaskRuntimeState()).total_courses = len(course_queue)

            self.append_log(task_id, "info", f"已获取 {len(course_queue)} 门待刷课程")
            self._append_event(
                task_id,
                "courses_selected",
                {
                    "count": len(course_queue),
                    "courseIds": selected_courses,
                    "courseTitles": [course.get("title", "") for course in course_queue],
                },
            )

            common_config = self._build_common_config(account_data, config_data, selected_courses)
            for course in course_queue:
                process_course(chaoxing, course, common_config)

            status = TaskStatus.SUCCEEDED
            with session_context() as session:
                pending_count = session.exec(
                    select(func.count()).select_from(PendingDecision).where(
                        PendingDecision.task_id == task_id,
                        PendingDecision.status == "pending",
                    )
                ).one()
                if pending_count:
                    status = TaskStatus.WAITING_CONFIRMATION

                task = session.get(TaskRun, task_id)
                if task is not None:
                    task.status = status
                    task.finished_at = datetime.now(timezone.utc)
                    task.progress_pct = 100.0
                    task.current_chapter = ""
                    task.current_job = ""
                    session.add(task)
                    session.commit()

            self.append_log(task_id, "info", "任务执行完成")
            self._append_event(task_id, "task_finished", {"status": status})
        except BaseException as exc:
            error_message = str(exc)
            self.append_log(task_id, "error", error_message, {"traceback": traceback.format_exc()})
            self._append_event(task_id, "task_failed", {"message": error_message})
            with session_context() as session:
                task = session.get(TaskRun, task_id)
                if task is not None:
                    task.status = TaskStatus.FAILED
                    task.error_message = error_message
                    task.finished_at = datetime.now(timezone.utc)
                    session.add(task)
                    session.commit()
        finally:
            self.cleanup_task(task_id)

    def _build_chaoxing(
        self,
        *,
        account: dict[str, Any],
        config: dict[str, Any],
        selected_courses: list[str] | None,
        tiku_config: dict[str, Any],
        task_id: int | None = None,
    ):
        common_config = self._build_common_config(account, config, selected_courses)
        runtime_kwargs: dict[str, Any] = {
            "cookies_path": account["cookies_path"],
            "task_id": task_id,
        }
        if task_id is not None:
            runtime_kwargs["event_callback"] = lambda event_type, payload: self.handle_runtime_event(task_id, event_type, payload)
            runtime_kwargs["log_callback"] = lambda level, message, context: self.append_log(task_id, level, message, context)

        return init_chaoxing(
            common_config,
            tiku_config,
            prompt=lambda _: "",
            **runtime_kwargs,
        )

    def _build_common_config(
        self,
        account: dict[str, Any],
        config: dict[str, Any],
        selected_courses: list[str] | None,
    ) -> dict[str, Any]:
        return sanitize_common_config(
            {
                "username": account["username"],
                "password": account["password_encrypted"],
                "use_cookies": True,
                "course_list": selected_courses,
                "speed": config["speed"],
                "jobs": config["jobs"],
                "notopen_action": config["notopen_action"],
            }
        )

    def _load_tiku_config(self, config: dict[str, Any]) -> dict[str, Any]:
        parser = load_backend_config()
        payload: dict[str, Any] = {}
        if parser.has_section("tiku"):
            payload = dict(parser.items("tiku"))

        if config["answer_provider"]:
            payload["provider"] = config["answer_provider"]
        if config["provider_config_json"]:
            try:
                payload.update(json.loads(config["provider_config_json"]))
            except json.JSONDecodeError:
                pass

        if "provider" not in payload:
            payload["provider"] = ""
        if "submit" not in payload:
            payload["submit"] = "false"
        if "cover_rate" not in payload:
            payload["cover_rate"] = str(config["min_cover_rate"])
        if "true_list" not in payload:
            payload["true_list"] = "正确,对,true,是"
        if "false_list" not in payload:
            payload["false_list"] = "错误,错,false,否"
        return payload

    @staticmethod
    def _account_payload(account: Account) -> dict[str, Any]:
        return {
            "id": account.id,
            "username": account.username,
            "password_encrypted": account.password_encrypted,
            "cookies_path": account.cookies_path,
        }

    @staticmethod
    def _config_payload(config: AccountStudyConfig) -> dict[str, Any]:
        return {
            "speed": config.speed,
            "jobs": config.jobs,
            "notopen_action": config.notopen_action,
            "answer_provider": config.answer_provider,
            "min_cover_rate": config.min_cover_rate,
            "provider_config_json": config.provider_config_json,
        }

    def _store_course_snapshots(self, session, account: Account, courses: list[dict[str, Any]]) -> None:
        now = datetime.now(timezone.utc)
        session.exec(delete(CourseSnapshot).where(CourseSnapshot.account_id == account.id))
        for course in courses:
            session.add(
                CourseSnapshot(
                    account_id=account.id or 0,
                    course_id=str(course.get("courseId") or ""),
                    clazz_id=str(course.get("clazzId") or ""),
                    cpi=str(course.get("cpi") or ""),
                    title=str(course.get("title") or ""),
                    teacher=str(course.get("teacher") or ""),
                    fetched_at=now,
                )
            )

        account.last_login_at = now
        account.updated_at = now
        session.add(account)
        session.commit()

    def _append_event(self, task_id: int, event_type: str, payload: dict[str, Any]) -> None:
        with self._lock:
            seq = self._event_counters.get(task_id, self._load_event_seq(task_id)) + 1
            self._event_counters[task_id] = seq

        with session_context() as session:
            session.add(
                TaskEvent(
                    task_id=task_id,
                    seq=seq,
                    event_type=event_type,
                    payload_json=json.dumps(payload, ensure_ascii=False),
                )
            )
            session.commit()

    def _update_task_fields(self, task_id: int, **fields: Any) -> None:
        updates = {key: value for key, value in fields.items() if value is not None}
        if not updates:
            return

        with session_context() as session:
            task = session.get(TaskRun, task_id)
            if task is None:
                return

            if "current_course" in updates:
                task.current_course = str(updates["current_course"] or "")
            if "current_chapter" in updates:
                task.current_chapter = str(updates["current_chapter"] or "")
            if "current_job" in updates:
                task.current_job = str(updates["current_job"] or "")
            if "progress_pct" in updates:
                task.progress_pct = max(0.0, min(100.0, float(updates["progress_pct"] or 0.0)))
            session.add(task)
            session.commit()

    def _load_event_seq(self, task_id: int) -> int:
        with session_context() as session:
            current = session.exec(
                select(func.max(TaskEvent.seq)).where(TaskEvent.task_id == task_id)
            ).one()
            return int(current or 0)

    @staticmethod
    def _selected_courses(value: str | None) -> list[str]:
        if not value:
            return []
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return [str(item).strip() for item in parsed if str(item).strip()]

    @staticmethod
    def _calculate_progress(state: TaskRuntimeState) -> float:
        if state.total_courses <= 0:
            return 0.0

        completed_courses = len(state.completed_course_ids)
        current_course_progress = 0.0
        if state.current_course_id and state.current_course_id not in state.completed_course_ids:
            total_points = max(state.current_course_total_points, 1)
            completed_points = min(len(state.completed_chapter_ids), total_points)
            current_course_progress = completed_points / total_points
            if len(state.completed_chapter_ids) < total_points and state.current_video_progress_pct > 0:
                current_course_progress = min(
                    1.0,
                    (completed_points + (state.current_video_progress_pct / 100.0)) / total_points,
                )

        return round(((completed_courses + current_course_progress) / state.total_courses) * 100, 2)


task_runtime_service = TaskRuntimeService()

__all__ = ["TaskRuntimeService", "task_runtime_service"]
