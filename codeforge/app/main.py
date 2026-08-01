"""FastAPI entry point for CodeForge application."""

import contextlib
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.router import api_router
from app.config import settings
from app.core.exceptions import (
    CircuitBreakerOpenError,
    CodeForgeException,
    ModelUnavailableError,
    SandboxExecutionError,
    SecurityViolationError,
    SelfCorrectionExhaustedError,
    ValidationError,
)
from app.models.database import init_db
from app.utils.logging import configure_logging, get_logger

logger = get_logger(__name__)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Add correlation ID to requests for tracing."""

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """Process request with correlation ID."""
        correlation_id = request.headers.get("X-Correlation-ID", None)
        
        if not correlation_id:
            import uuid
            correlation_id = str(uuid.uuid4())
        
        request.state.correlation_id = correlation_id
        
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    logger.info("Starting CodeForge application")
    configure_logging()
    
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down CodeForge application")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="CodeForge",
        description="Multi-Agent Coding Orchestrator System",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    
    # Add middleware
    app.add_middleware(CorrelationIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API router
    app.include_router(api_router, prefix="/api/v1")
    
    # Health check endpoint
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}
    
    # Exception handlers
    @app.exception_handler(CodeForgeException)
    async def codeforge_exception_handler(
        request: Request,
        exc: CodeForgeException,
    ) -> JSONResponse:
        """Handle CodeForge exceptions."""
        logger.error(
            f"CodeForge exception: {exc}",
            correlation_id=getattr(request.state, "correlation_id", None),
        )
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc), "error_type": type(exc).__name__},
        )
    
    @app.exception_handler(SecurityViolationError)
    async def security_violation_handler(
        request: Request,
        exc: SecurityViolationError,
    ) -> JSONResponse:
        """Handle security violations."""
        logger.warning(
            f"Security violation: {exc}",
            correlation_id=getattr(request.state, "correlation_id", None),
        )
        return JSONResponse(
            status_code=403,
            content={"detail": str(exc), "error_type": "SecurityViolation"},
        )
    
    @app.exception_handler(ModelUnavailableError)
    async def model_unavailable_handler(
        request: Request,
        exc: ModelUnavailableError,
    ) -> JSONResponse:
        """Handle model unavailability."""
        logger.error(
            f"Model unavailable: {exc}",
            correlation_id=getattr(request.state, "correlation_id", None),
        )
        return JSONResponse(
            status_code=503,
            content={"detail": str(exc), "error_type": "ModelUnavailable"},
        )
    
    @app.exception_handler(CircuitBreakerOpenError)
    async def circuit_breaker_handler(
        request: Request,
        exc: CircuitBreakerOpenError,
    ) -> JSONResponse:
        """Handle circuit breaker open errors."""
        logger.warning(
            f"Circuit breaker open: {exc}",
            correlation_id=getattr(request.state, "correlation_id", None),
        )
        return JSONResponse(
            status_code=503,
            content={"detail": str(exc), "error_type": "CircuitBreakerOpen"},
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Handle unexpected exceptions."""
        logger.exception(
            f"Unexpected error: {exc}",
            correlation_id=getattr(request.state, "correlation_id", None),
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error_type": "InternalServerError"},
        )
    
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
