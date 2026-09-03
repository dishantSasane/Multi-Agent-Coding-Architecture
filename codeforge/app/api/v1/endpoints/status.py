"""Status endpoint - Poll generation status."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.models.schemas import TaskStatusResponse
from app.models.database import AsyncSessionLocal
from app.models.models import Task

router = APIRouter()


@router.get("/status", response_model=TaskStatusResponse)
async def get_status(
    task_id: UUID,
) -> TaskStatusResponse:
    """Get current status of a task.

    Args:
        task_id: Task UUID.

    Returns:
        Current task status including any clarifying questions.
    """
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        return TaskStatusResponse.model_validate(task)


@router.get("/result", response_model=TaskStatusResponse)
async def get_result(
    task_id: UUID,
) -> TaskStatusResponse:
    """Get final result when task is completed.

    Args:
        task_id: Task UUID.

    Returns:
        Final task result with generated code.
    """
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        if task.status.value not in ["COMPLETED", "FAILED"]:
            raise HTTPException(
                status_code=400,
                detail=f"Task not yet completed. Current status: {task.status.value}",
            )

        return TaskStatusResponse.model_validate(task)
