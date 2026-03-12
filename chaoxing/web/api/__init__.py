# -*- coding: utf-8 -*-
"""Web API 路由包。"""

from chaoxing.web.api.accounts import router as accounts_router
from chaoxing.web.api.decisions import router as decisions_router
from chaoxing.web.api.tasks import router as tasks_router

__all__ = ["accounts_router", "decisions_router", "tasks_router"]
