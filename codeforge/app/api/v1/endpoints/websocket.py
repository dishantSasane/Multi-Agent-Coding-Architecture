"""WebSocket endpoint - Real-time task status updates."""

import asyncio
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.models.database import get_session_maker
from app.models.orm_models import Task

router = APIRouter()


@router.websocket("/ws/{task_id}")
async def websocket_task_updates(websocket: WebSocket, task_id: UUID) -> None:
    await websocket.accept()  # MUST be absolute first line, nothing before it

    # All logic goes AFTER accept
    task_id_str = str(task_id)
    try:
        while True:
            # poll task status from DB every 2 seconds
            async with get_session_maker()() as session:
                result = await session.execute(
                    select(Task).where(Task.id == task_id)
                )
                task = result.scalar_one_or_none()

            if task is None:
                await websocket.send_json({"type": "error", "message": "Task not found"})
                break

            status = task.status.value if hasattr(task.status, 'value') else task.status

            # Omit `data` — it contains UUID objects that break JSON
            # serialisation. The frontend fetches the full task via REST once
            # the `completed` message arrives, so this field is never needed.
            await websocket.send_json({
                "type": "status_update",
                "task_id": task_id_str,
                "status": status,
            })

            if status in ["completed", "failed"]:
                await websocket.send_json({"type": status, "task_id": task_id_str})
                break

            await asyncio.sleep(2)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
