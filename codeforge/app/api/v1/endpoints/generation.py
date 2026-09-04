"""Generation endpoint - Trigger code generation."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.models.models import TaskStatusResponse
from app.services.orchestrator import get_orchestrator

router = APIRouter()


@router.post("/generate", response_model=TaskStatusResponse)
async def trigger_generation(
    task_id: UUID,
) -> TaskStatusResponse:
    """Trigger code generation for a confirmed task.

    Args:
        task_id: Task UUID.

    Returns:
        Updated task status.
    """
    try:
        orchestrator = get_orchestrator()
        task = await orchestrator.trigger_generation(task_id)
        return TaskStatusResponse(**task.to_dict())

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
