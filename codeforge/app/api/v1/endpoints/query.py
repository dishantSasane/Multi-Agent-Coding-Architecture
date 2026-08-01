"""Query endpoint - Submit coding queries."""

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.models import QueryRequest, TaskResult, TaskStatusResponse
from app.services.orchestrator import get_orchestrator

router = APIRouter()


class SubmitResponse(BaseModel):
    """Response for submitting a query."""

    task_id: UUID
    status: str
    message: str


@router.post("", response_model=SubmitResponse)
async def submit_query(request: QueryRequest) -> SubmitResponse:
    """Submit a new coding query.

    Args:
        request: Query request with user query and optional context.

    Returns:
        Task ID and initial status.
    """
    orchestrator = get_orchestrator()

    try:
        # Create task
        task = await orchestrator.create_task(
            user_query=request.query,
            context=request.context,
            preferences=request.preferences,
        )

        return SubmitResponse(
            task_id=task.id,
            status=task.status.value,
            message="Task created successfully. Use /status endpoint to poll for updates.",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{task_id}/run", response_model=TaskStatusResponse)
async def run_pipeline(task_id: UUID) -> TaskStatusResponse:
    """Run the full generation pipeline for a task.

    Args:
        task_id: Task UUID.

    Returns:
        Updated task status.
    """
    orchestrator = get_orchestrator()

    try:
        task = await orchestrator.run_full_pipeline(task_id)

        return TaskStatusResponse(**task.to_dict())

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
