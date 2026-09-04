"""SQLAlchemy ORM models for database persistence."""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.database import Base
from app.models.enums import ConfirmationStatusEnum, TaskStatusEnum


class Task(Base):
    """SQLAlchemy ORM model for code generation tasks."""

    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_query: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[TaskStatusEnum] = mapped_column(
        String(50),
        nullable=False,
        default=TaskStatusEnum.PENDING,
    )
    confirmation_status: Mapped[ConfirmationStatusEnum] = mapped_column(
        String(50),
        nullable=False,
        default=ConfirmationStatusEnum.PENDING,
    )

    # Intent & clarification
    intent_analysis: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    clarifying_questions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    user_clarifications: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Generation results
    model_outputs: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    debate_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Synthesis
    synthesized_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    synthesized_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    known_limitations: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Validation & sandbox
    validation_results: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    sandbox_results: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Final output
    final_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_tests: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_documentation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Multi-file output — populated when synthesized_code contains file markers.
    # Each element: {"filename": "models.py", "content": "..."}
    code_files: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Error tracking
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    correction_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert ORM model to dict compatible with TaskStatusResponse schema."""
        from app.models.models import IntentAnalysis

        intent = None
        if self.intent_analysis:
            try:
                intent = IntentAnalysis(**self.intent_analysis)
            except Exception:
                intent = None

        return {
            "id": self.id,
            "status": self.status.value if isinstance(self.status, TaskStatusEnum) else self.status,
            "user_query": self.user_query,
            "intent_analysis": intent,
            "confirmation_status": (
                self.confirmation_status.value
                if isinstance(self.confirmation_status, ConfirmationStatusEnum)
                else self.confirmation_status
            ),
            "clarifying_questions": self.clarifying_questions or [],
            "correction_attempts": self.correction_attempts or 0,
            "error_log": {"message": self.last_error} if self.last_error else None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            # Generated code — populated once the pipeline reaches COMPLETED
            "synthesized_code": self.synthesized_code,
            "final_code": self.final_code,
            # Multi-file split — None when code is a single file
            "code_files": self.code_files,
            "validation_results": self.validation_results,
            "last_error": self.last_error,
        }

    def __repr__(self) -> str:
        return f"<Task id={self.id} status={self.status}>"


class ModelCall(Base):
    """SQLAlchemy ORM model for tracking individual LLM API calls."""

    __tablename__ = "model_calls"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(nullable=False, default=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<ModelCall id={self.id} provider={self.provider} task={self.task_id}>"
