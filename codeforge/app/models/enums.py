"""Enums for database models."""

import enum

# Re-exported so service files can do `from app.models.enums import ModelProvider`
from app.core.constants import ModelProvider  # noqa: F401


class TaskStatusEnum(str, enum.Enum):
    """Task status enumeration for database."""

    PENDING = "pending"
    INTENT_ANALYZING = "intent_analyzing"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    CONFIRMED = "confirmed"
    DECOMPOSING = "decomposing"
    GENERATING = "generating"
    DEBATING = "debating"
    SYNTHESIZING = "synthesizing"
    VALIDATING = "validating"
    SANDBOX_EXECUTING = "sandbox_executing"
    CORRECTING = "correcting"
    COMPLETED = "completed"
    FAILED = "failed"


class ConfirmationStatusEnum(str, enum.Enum):
    """Confirmation status enumeration."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    CLARIFIED = "clarified"


class ModelProviderEnum(str, enum.Enum):
    """Model provider enumeration for database."""

    OPENROUTER = "openrouter"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    KIMI = "kimi"
    QWEN = "qwen"
    GROQ = "groq"
    GEMINI = "gemini"
