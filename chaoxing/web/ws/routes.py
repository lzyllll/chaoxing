# -*- coding: utf-8 -*-
import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from chaoxing.web.auth import ensure_admin_websocket_session
from chaoxing.web.db import session_context
from chaoxing.web.services import WebQueryService

router = APIRouter()
query_service = WebQueryService()


@router.websocket("/ws/tasks/{task_id}")
async def task_detail_stream(websocket: WebSocket, task_id: int) -> None:
    if not await ensure_admin_websocket_session(websocket):
        return

    await websocket.accept()
    last_snapshot = ""
    heartbeat = 0

    try:
        while True:
            with session_context() as session:
                snapshot = query_service.get_task_stream_snapshot(session, task_id)

            if snapshot is None:
                await websocket.send_text(json.dumps({"type": "error", "message": "Task not found"}, ensure_ascii=False))
                await websocket.close(code=1008)
                return

            encoded_snapshot = json.dumps(snapshot, ensure_ascii=False, sort_keys=True)
            if encoded_snapshot != last_snapshot:
                await websocket.send_text(json.dumps(snapshot, ensure_ascii=False))
                last_snapshot = encoded_snapshot

            heartbeat += 1
            if heartbeat >= 10:
                await websocket.send_text(json.dumps({"type": "heartbeat", "taskId": task_id}, ensure_ascii=False))
                heartbeat = 0

            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return
