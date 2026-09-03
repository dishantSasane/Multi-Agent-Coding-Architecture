"""Confirmation endpoint - User confirms intent."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.models.models import ConfirmRequest, TaskStatusResponse
from app.services.orchestrator import get_orchestrator

router = APIRouter()


@router.post("/confirm", response_model=TaskStatusResponse)
async def confirm_intent(
    task_id: UUID,
    request: ConfirmRequest,
) -> TaskStatusResponse:
    """Confirm or clarify intent for a task.

    Args:
        task_id: Task UUID.
        request: Confirmation with confirmed flag and optional clarifications.

    Returns:
        Updated task status.
    """
    orchestrator = get_orchestrator()

    try:
        task = await orchestrator.confirm_intent(
            task_id=task_id,
            confirmed=request.confirmed,
            clarifications=request.clarifications,
        )

        return TaskStatusResponse(**task.to_dict())

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
