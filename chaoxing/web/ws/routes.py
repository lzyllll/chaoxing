# -*- coding: utf-8 -*-
import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from chaoxing.web.db import get_session
from chaoxing.web.services import WebQueryService

router = APIRouter()
query_service = WebQueryService()


@router.websocket("/ws/tasks/{task_id}")
async def task_detail_stream(websocket: WebSocket, task_id: int) -> None:
    await websocket.accept()
    session = get_session()

    try:
        snapshot = query_service.get_task_stream_snapshot(session, task_id)
        if snapshot is None:
            await websocket.send_text(json.dumps({"type": "error", "message": "Task not found"}, ensure_ascii=False))
            await websocket.close(code=1008)
            return

        await websocket.send_text(json.dumps(snapshot, ensure_ascii=False))

        while True:
            await asyncio.sleep(2)
            await websocket.send_text(json.dumps({"type": "heartbeat", "taskId": task_id}, ensure_ascii=False))
    except WebSocketDisconnect:
        return
    finally:
        session.close()
