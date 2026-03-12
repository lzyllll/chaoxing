# -*- coding: utf-8 -*-
import random
import re
from dataclasses import dataclass, field
from typing import Any

from chaoxing.core.logger import logger
from chaoxing.services.answer import AnswerQueryResult, Tiku
from chaoxing.utils.answer_check import cut


@dataclass(slots=True)
class WorkAnswerPolicy:
    submission_mode: str = "manual"
    min_cover_rate: float = 0.8
    confidence_threshold: float = 0.8
    allow_ai_auto_submit: bool = False
    low_confidence_action: str = "save_only"


@dataclass(slots=True)
class WorkQuestionOutcome:
    question_id: str
    question_type: str
    question_title: str
    options: list[str] = field(default_factory=list)
    candidate_answers: list[str] = field(default_factory=list)
    final_answer: str = ""
    answer_source: str = ""
    confidence: float = 0.0
    decision: str = ""
    raw_response: Any = None
    matched: bool = False
    submit_answer: str = ""


@dataclass(slots=True)
class WorkSubmissionDecision:
    py_flag: str
    decision: str
    reason: str
    cover_rate: float
    average_confidence: float
    requires_manual_review: bool = False


MULTI_CUT_CHARS = [
    "\n",
    ",",
    "，",
    "|",
    "\r",
    "\t",
    "#",
    "*",
    "-",
    "_",
    "+",
    "@",
    "~",
    "/",
    "\\",
    ".",
    "&",
    " ",
    "、",
]


def split_answer_candidates(answer: str | list[str] | None) -> list[str]:
    if answer is None:
        return []
    if isinstance(answer, list):
        values = answer
    else:
        values = [answer]

    cleaned_values: list[str] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, str):
            parts = cut(value)
            if parts:
                cleaned_values.extend(parts)
            else:
                cleaned_values.append(value)
        else:
            cleaned_values.append(str(value))

    result: list[str] = []
    for value in cleaned_values:
        candidate = value.strip()
        if not candidate:
            continue
        candidate = re.sub(r'^[A-Za-z][.、．:]?', '', candidate) if len(candidate) > 1 else candidate
        candidate = re.sub(r'[.,!?;:，。！？；：]', '', candidate).strip()
        if candidate:
            result.append(candidate)
    return result


def split_question_options(options: str) -> list[str]:
    if not options:
        return []
    result = cut(options)
    if result is None:
        logger.warning("未能正确提取题目选项信息")
        return []
    return [item.strip() for item in result if item and item.strip()]


def is_subsequence(candidate: str, option: str) -> bool:
    iter_option = iter(option)
    return all(char in iter_option for char in candidate)


def random_answer(question: dict[str, Any]) -> str:
    options = question.get("options", "")
    question_type = question.get("type", "")
    if not options:
        return ""

    option_list = split_question_options(options)
    if question_type == "multiple":
        if not option_list:
            return ""
        if len(option_list) <= 1:
            selected = option_list
        else:
            max_possible = min(4, len(option_list))
            min_possible = min(2, len(option_list))
            weights_map = {
                2: [1.0],
                3: [0.3, 0.7],
                4: [0.1, 0.5, 0.4],
                5: [0.1, 0.4, 0.3, 0.2],
            }
            possible_counts = list(range(min_possible, max_possible + 1))
            weights = weights_map.get(max_possible, [0.3, 0.4, 0.3])[: len(possible_counts)]
            weight_sum = sum(weights)
            if weight_sum > 0:
                weights = [weight / weight_sum for weight in weights]
            selected_count = random.choices(possible_counts, weights=weights, k=1)[0]
            selected = random.sample(option_list, selected_count)
        return "".join(sorted(item[:1] for item in selected if item))

    if question_type == "single":
        if not option_list:
            return ""
        return random.choice(option_list)[:1]

    if question_type == "judgement":
        return "true" if random.choice([True, False]) else "false"

    return ""


def resolve_question_answer(
    question: dict[str, Any],
    query_result: AnswerQueryResult,
    tiku: Tiku,
) -> WorkQuestionOutcome:
    options = split_question_options(question.get("options", ""))
    outcome = WorkQuestionOutcome(
        question_id=question.get("id", ""),
        question_type=question.get("type", ""),
        question_title=question.get("title", ""),
        options=options,
        candidate_answers=list(query_result.candidates),
        raw_response=query_result.raw_response,
    )

    answer = ""
    if query_result.answer:
        if outcome.question_type == "multiple":
            for candidate in split_answer_candidates(query_result.answer):
                for option in options:
                    if is_subsequence(candidate, option):
                        answer += option[:1]
                        break
            answer = "".join(sorted(answer))
        elif outcome.question_type == "single":
            candidates = split_answer_candidates(query_result.answer)
            if candidates:
                for option in options:
                    if is_subsequence(candidates[0], option):
                        answer = option[:1]
                        break
        elif outcome.question_type == "judgement":
            answer = "true" if tiku.judgement_select(query_result.answer) else "false"
        elif outcome.question_type == "completion":
            if isinstance(query_result.answer, list):
                answer = "".join(query_result.answer)
            else:
                answer = str(query_result.answer)
        else:
            answer = str(query_result.answer)

    if answer:
        outcome.final_answer = answer
        outcome.submit_answer = answer
        outcome.answer_source = query_result.source or "provider"
        outcome.confidence = query_result.confidence
        outcome.decision = "covered"
        outcome.matched = True
        return outcome

    random_selected = random_answer(question)
    outcome.final_answer = random_selected
    outcome.submit_answer = random_selected
    outcome.answer_source = "random"
    outcome.confidence = 0.0
    outcome.decision = "random_fallback" if query_result.answer else "no_match"
    outcome.matched = False
    return outcome


def decide_submission(
    outcomes: list[WorkQuestionOutcome],
    policy: WorkAnswerPolicy,
    tiku: Tiku,
    rollback_times: int,
) -> WorkSubmissionDecision:
    total_questions = len(outcomes)
    covered = [item for item in outcomes if item.matched]
    cover_rate = (len(covered) / total_questions) if total_questions else 0.0
    average_confidence = (
        sum(item.confidence for item in covered) / len(covered) if covered else 0.0
    )
    uses_ai_answers = any(item.answer_source in {"ai", "llm"} for item in covered)

    if policy.submission_mode == "manual":
        return WorkSubmissionDecision(
            py_flag="1",
            decision="save_only",
            reason="manual_mode",
            cover_rate=cover_rate,
            average_confidence=average_confidence,
        )

    if policy.submission_mode == "auto":
        if uses_ai_answers and not policy.allow_ai_auto_submit:
            return WorkSubmissionDecision(
                py_flag="1",
                decision="save_only",
                reason="ai_auto_submit_disabled",
                cover_rate=cover_rate,
                average_confidence=average_confidence,
                requires_manual_review=True,
            )
        return WorkSubmissionDecision(
            py_flag="",
            decision="submit",
            reason="auto_mode",
            cover_rate=cover_rate,
            average_confidence=average_confidence,
        )

    min_cover_rate = max(0.0, min(1.0, policy.min_cover_rate or tiku.COVER_RATE))
    confidence_threshold = max(0.0, min(1.0, policy.confidence_threshold or 0.8))

    if rollback_times >= 1:
        return WorkSubmissionDecision(
            py_flag="",
            decision="submit",
            reason="rollback_override",
            cover_rate=cover_rate,
            average_confidence=average_confidence,
        )

    if uses_ai_answers and not policy.allow_ai_auto_submit:
        manual_decision = "wait_manual" if policy.low_confidence_action == "pause" else "save_only"
        return WorkSubmissionDecision(
            py_flag="1",
            decision=manual_decision,
            reason="ai_auto_submit_disabled",
            cover_rate=cover_rate,
            average_confidence=average_confidence,
            requires_manual_review=policy.low_confidence_action == "pause",
        )

    if cover_rate < min_cover_rate:
        manual_decision = "wait_manual" if policy.low_confidence_action == "pause" else "save_only"
        return WorkSubmissionDecision(
            py_flag="1",
            decision=manual_decision,
            reason="cover_rate_below_threshold",
            cover_rate=cover_rate,
            average_confidence=average_confidence,
            requires_manual_review=policy.low_confidence_action == "pause",
        )

    if average_confidence < confidence_threshold:
        manual_decision = "wait_manual" if policy.low_confidence_action == "pause" else "save_only"
        if policy.low_confidence_action == "skip":
            manual_decision = "skip"
        return WorkSubmissionDecision(
            py_flag="1",
            decision=manual_decision,
            reason="confidence_below_threshold",
            cover_rate=cover_rate,
            average_confidence=average_confidence,
            requires_manual_review=policy.low_confidence_action == "pause",
        )

    return WorkSubmissionDecision(
        py_flag="",
        decision="submit",
        reason="intelligent_threshold_passed",
        cover_rate=cover_rate,
        average_confidence=average_confidence,
    )
