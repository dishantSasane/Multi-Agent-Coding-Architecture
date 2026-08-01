"""Enums for database models."""

import enum


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

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    KIMI = "kimi"
    QWEN = "qwen"
    GEMINI = "gemini"
