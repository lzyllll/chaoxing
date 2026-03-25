# -*- coding: utf-8 -*-
"""Web 服务包。"""

from chaoxing.web.services.answer_records import AnswerRecordService
from chaoxing.web.services.queries import WebQueryService
from chaoxing.web.services.runtime import TaskRuntimeService, task_runtime_service

__all__ = ["AnswerRecordService", "WebQueryService", "TaskRuntimeService", "task_runtime_service"]
