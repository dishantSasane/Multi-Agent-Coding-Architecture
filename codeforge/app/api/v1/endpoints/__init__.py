"""Endpoints module initialization."""

from app.api.v1.endpoints.confirmation import router as confirmation_router
from app.api.v1.endpoints.generation import router as generation_router
from app.api.v1.endpoints.query import router as query_router
from app.api.v1.endpoints.status import router as status_router

__all__ = [
    "query_router",
    "confirmation_router",
    "generation_router",
    "status_router",
]
