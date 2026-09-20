"""Confirmation endpoint - User confirms intent."""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.core.exceptions import TaskNotFoundError
from app.models.models import ConfirmRequest, TaskStatusResponse
from app.api.v1.endpoints.query import _run_pipeline_background
from app.services.orchestrator import get_orchestrator

router = APIRouter()


@router.post("/confirm", response_model=TaskStatusResponse)
async def confirm_intent(
    task_id: UUID,
    request: ConfirmRequest,
    background_tasks: BackgroundTasks,
) -> TaskStatusResponse:
    """Confirm or clarify intent for a task.

    Args:
        task_id: Task UUID.
        request: Confirmation with confirmed flag and optional clarifications.
        background_tasks: Resumes the pipeline once the answer is stored.

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

        # The pipeline stopped at awaiting_confirmation; resume it (confirmed
        # runs straight to generation, clarified re-analyses the intent).
        background_tasks.add_task(_run_pipeline_background, task_id)

        return TaskStatusResponse(**task.to_dict())

    except TaskNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
