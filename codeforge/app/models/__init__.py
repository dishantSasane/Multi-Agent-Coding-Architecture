"""Models module initialization."""

from app.models.database import Base, close_db, get_db_session, init_db
from app.models.enums import ConfirmationStatusEnum, ModelProviderEnum, TaskStatusEnum
from app.models.models import (
    ConfirmRequest,
    DebateResult,
    ErrorResponse,
    IntentAnalysis,
    ModelCall,
    ModelOutput,
    ProgressUpdate,
    QueryRequest,
    SandboxResult,
    Task,
    TaskResult,
    TaskStatusResponse,
    ValidationResult,
    WSMessage,
)

__all__ = [
    # Database
    "Base",
    "get_db_session",
    "init_db",
    "close_db",
    # Enums
    "ConfirmationStatusEnum",
    "ModelProviderEnum",
    "TaskStatusEnum",
    # Models
    "Task",
    "ModelCall",
    # Pydantic Schemas
    "ConfirmRequest",
    "DebateResult",
    "ErrorResponse",
    "IntentAnalysis",
    "ModelOutput",
    "ProgressUpdate",
    "QueryRequest",
    "SandboxResult",
    "TaskResult",
    "TaskStatusResponse",
    "ValidationResult",
    "WSMessage",
]
