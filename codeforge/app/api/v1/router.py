"""API router combining all v1 endpoints."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    confirmation_router,
    generation_router,
    query_router,
    status_router,
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    query_router,
    prefix="/query",
    tags=["Query"],
)

api_router.include_router(
    confirmation_router,
    prefix="/query/{task_id}",
    tags=["Confirmation"],
)

api_router.include_router(
    generation_router,
    prefix="/query/{task_id}",
    tags=["Generation"],
)

api_router.include_router(
    status_router,
    prefix="/query/{task_id}",
    tags=["Status"],
)
