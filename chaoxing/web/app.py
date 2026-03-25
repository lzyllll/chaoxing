# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from chaoxing import __version__
from chaoxing.web.api.admin import router as admin_router
from chaoxing.web.api.accounts import router as accounts_router
from chaoxing.web.api.decisions import router as decisions_router
from chaoxing.web.api.tasks import router as tasks_router
from chaoxing.web.auth import require_admin_session
from chaoxing.web.db import create_db_and_tables
from chaoxing.web.settings import get_backend_settings
from chaoxing.web.services import task_runtime_service
from chaoxing.web.ws.routes import router as ws_router

api_router = APIRouter(prefix="/api")
api_router.include_router(admin_router)
api_router.include_router(accounts_router, dependencies=[Depends(require_admin_session)])
api_router.include_router(tasks_router, dependencies=[Depends(require_admin_session)])
api_router.include_router(decisions_router, dependencies=[Depends(require_admin_session)])


@api_router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


def create_app() -> FastAPI:
    settings = get_backend_settings()
    app = FastAPI(title="Chaoxing Web API", version=__version__)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    app.include_router(ws_router)

    @app.on_event("startup")
    def on_startup() -> None:
        create_db_and_tables()
        task_runtime_service.recover_interrupted_tasks()

    return app


app = create_app()

__all__ = ["app", "create_app", "api_router"]
