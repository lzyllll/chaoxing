# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from sqlmodel import Session

from chaoxing.web.db import get_session
from chaoxing.web.services import WebQueryService

router = APIRouter(tags=["decisions"])
query_service = WebQueryService()


@router.get("/decisions")
def list_pending_decisions(session: Session = Depends(get_session)) -> list[dict]:
    return query_service.list_pending_decisions(session)
