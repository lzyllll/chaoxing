# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Protocol

from chaoxing.services.work_answer import WorkQuestionOutcome, WorkSubmissionDecision


class AnswerRecordService(Protocol):
    def save_work_outcomes(
        self,
        *,
        task_id: int | None,
        work_job_id: str,
        course_title: str,
        chapter_title: str,
        outcomes: list[WorkQuestionOutcome],
        submission: WorkSubmissionDecision,
    ) -> None: ...


class NullAnswerRecordService:
    def save_work_outcomes(
        self,
        *,
        task_id: int | None,
        work_job_id: str,
        course_title: str,
        chapter_title: str,
        outcomes: list[WorkQuestionOutcome],
        submission: WorkSubmissionDecision,
    ) -> None:
        return
