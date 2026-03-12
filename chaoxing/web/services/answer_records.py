# -*- coding: utf-8 -*-
import json
from typing import Any

from chaoxing.services.work_answer import WorkQuestionOutcome, WorkSubmissionDecision
from chaoxing.web.db import get_session
from chaoxing.web.models import AnswerRecord, PendingDecision


class AnswerRecordService:
    def save_work_outcomes(
        self,
        *,
        task_id: int | None,
        work_job_id: str,
        outcomes: list[WorkQuestionOutcome],
        submission: WorkSubmissionDecision,
    ) -> None:
        if not task_id or not outcomes:
            return

        with get_session() as session:
            records: list[AnswerRecord] = []
            for outcome in outcomes:
                record = AnswerRecord(
                    task_id=task_id,
                    work_job_id=work_job_id,
                    question_id=outcome.question_id,
                    question_type=outcome.question_type,
                    question_title=outcome.question_title,
                    options_json=self._to_json(outcome.options, default=[]),
                    candidate_answers_json=self._to_json(outcome.candidate_answers, default=[]),
                    final_answer=outcome.final_answer,
                    answer_source=outcome.answer_source,
                    confidence=outcome.confidence,
                    decision=outcome.decision,
                    submit_result=submission.decision,
                    raw_response_json=self._to_json(outcome.raw_response, default={}),
                )
                session.add(record)
                records.append(record)

            session.flush()

            if submission.requires_manual_review:
                for record in records:
                    session.add(
                        PendingDecision(
                            task_id=task_id,
                            answer_record_id=record.id,
                            reason=submission.reason,
                        )
                    )

            session.commit()

    @staticmethod
    def _to_json(value: Any, *, default: Any) -> str:
        payload = default if value is None else value
        return json.dumps(payload, ensure_ascii=False)
