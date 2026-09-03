"""Generation endpoint - Trigger code generation."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.models.schemas import TaskStatusResponse
from app.services.orchestrator import Orchestrator

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
    from app.models.database import AsyncSessionLocal

    orchestrator = Orchestrator(db=AsyncSessionLocal)

    try:
        task = await orchestrator.trigger_generation(task_id)

        return TaskStatusResponse.model_validate(task)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
