"""Query endpoint - Submit coding queries."""

import traceback
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from app.models.models import QueryRequest, TaskStatusResponse
from app.services.orchestrator import get_orchestrator

router = APIRouter()


def _to_str(value) -> str:
    """Safely convert an enum or plain string status to str."""
    return value.value if hasattr(value, "value") else str(value)


class SubmitResponse(BaseModel):
    """Response for submitting a query."""

    task_id: UUID
    status: str
    message: str


async def _run_pipeline_background(task_id: UUID) -> None:
    """Run the full pipeline as a FastAPI background task (no task queue needed)."""
    try:
        orchestrator = get_orchestrator()
        await orchestrator.run_full_pipeline(task_id)
    except Exception:
        traceback.print_exc()


@router.post("", response_model=SubmitResponse)
async def submit_query(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
) -> SubmitResponse:
    """Submit a new coding query.

    Creates the task immediately, returns the task_id, then runs the full
    generation pipeline in the background so the client can poll /status.

    Args:
        request: Query request with user query and optional context.
        background_tasks: FastAPI background task runner.

    Returns:
        Task ID and initial status.
    """
    orchestrator = get_orchestrator()
    task = await orchestrator.create_task(
        user_query=request.query,
        context=request.context,
        preferences=request.preferences,
    )

    # Fire pipeline in background — response returns immediately with task_id
    background_tasks.add_task(_run_pipeline_background, task.id)

    return SubmitResponse(
        task_id=task.id,
        status=_to_str(task.status),
        message="Task created. Pipeline started. Poll /status for updates.",
    )


@router.post("/{task_id}/run", response_model=TaskStatusResponse)
async def run_pipeline(task_id: UUID) -> TaskStatusResponse:
    """Manually trigger the full generation pipeline for a task.

    Args:
        task_id: Task UUID.

    Returns:
        Updated task status.
    """
    orchestrator = get_orchestrator()
    task = await orchestrator.run_full_pipeline(task_id)
    return TaskStatusResponse(**task.to_dict())
