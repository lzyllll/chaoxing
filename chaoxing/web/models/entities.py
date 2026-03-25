# -*- coding: utf-8 -*-
from datetime import datetime, timezone
from enum import StrEnum
from typing import Optional

from sqlmodel import Field, SQLModel


class AccountStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class TaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_CONFIRMATION = "waiting_confirmation"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SubmissionMode(StrEnum):
    MANUAL = "manual"
    AUTO = "auto"
    INTELLIGENT = "intelligent"


class LowConfidenceAction(StrEnum):
    PAUSE = "pause"
    SKIP = "skip"
    SAVE_ONLY = "save_only"


class Account(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    username: str
    password_encrypted: str = ""
    cookies_path: str
    status: AccountStatus = Field(default=AccountStatus.ACTIVE)
    last_login_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AccountStudyConfig(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(index=True, unique=True)
    speed: float = 1.0
    jobs: int = 4
    notopen_action: str = "retry"
    answer_provider: str = ""
    submission_mode: SubmissionMode = Field(default=SubmissionMode.INTELLIGENT)
    confidence_threshold: float = 0.8
    min_cover_rate: float = 0.7
    allow_ai_auto_submit: bool = False
    low_confidence_action: LowConfidenceAction = Field(default=LowConfidenceAction.PAUSE)
    provider_config_json: str = "{}"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CourseSnapshot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(index=True)
    course_id: str = Field(index=True)
    clazz_id: str
    cpi: str
    title: str
    teacher: str = ""
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TaskRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(index=True)
    status: TaskStatus = Field(default=TaskStatus.QUEUED, index=True)
    selected_courses_json: str = "[]"
    progress_pct: float = 0.0
    current_course: str = ""
    current_chapter: str = ""
    current_job: str = ""
    error_message: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class TaskEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(index=True)
    seq: int = Field(index=True)
    event_type: str = Field(index=True)
    payload_json: str = "{}"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)


class TaskLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(index=True)
    level: str = Field(index=True)
    message: str
    context_json: str = "{}"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)


class AnswerRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(index=True)
    work_job_id: str = Field(index=True)
    course_title: str = ""
    chapter_title: str = ""
    question_id: str = Field(index=True)
    question_type: str
    question_title: str
    options_json: str = "[]"
    candidate_answers_json: str = "[]"
    final_answer: str = ""
    answer_source: str = ""
    confidence: float = 0.0
    decision: str = ""
    submit_result: str = ""
    raw_response_json: str = "{}"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)


class PendingDecision(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: int = Field(index=True)
    answer_record_id: int = Field(index=True)
    reason: str
    status: str = Field(default="pending", index=True)
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), index=True)
