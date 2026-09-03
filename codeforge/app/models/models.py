"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# Intent Analysis Schemas
class IntentAnalysis(BaseModel):
    """Schema for intent analysis results."""

    summary: str = Field(..., description="Brief summary of the request")
    tech_stack: list[str] = Field(default_factory=list, description="Identified tech stack")
    requirements: list[str] = Field(default_factory=list, description="Extracted requirements")
    constraints: list[str] = Field(default_factory=list, description="Constraints and limitations")
    edge_cases: list[str] = Field(default_factory=list, description="Edge cases to handle")
    security_concerns: list[str] = Field(default_factory=list, description="Security considerations")
    clarifying_questions: list[str] = Field(default_factory=list, description="Questions for user")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in analysis")
    task_type: str = Field(..., description="Type of task (architecture, implementation, etc.)")


# Request Schemas
class QueryRequest(BaseModel):
    """Request schema for submitting a coding query."""

    query: str = Field(..., min_length=1, max_length=10000, description="The coding query")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context")
    preferences: dict[str, Any] = Field(
        default_factory=dict,
        description="User preferences (style, testing level, etc.)",
    )


class ConfirmRequest(BaseModel):
    """Request schema for confirming intent."""

    confirmed: bool = Field(..., description="Whether the user confirms the intent")
    clarifications: str | None = Field(None, description="User clarifications if not confirmed")


# Response Schemas
class TaskStatusResponse(BaseModel):
    """Response schema for task status."""

    id: UUID
    status: str
    user_query: str
    intent_analysis: IntentAnalysis | None = None
    confirmation_status: str
    clarifying_questions: list[str] | None = None
    correction_attempts: int = 0
    error_log: dict | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class ModelOutput(BaseModel):
    """Schema for model output from ensemble."""

    provider: str
    model_name: str
    code: str
    reasoning: str
    confidence: float
    estimated_complexity: str
    latency_ms: int | None = None
    success: bool


class DebateResult(BaseModel):
    """Schema for debate engine results."""

    winner_provider: str
    scores: dict[str, dict[str, float]] = Field(
        default_factory=dict,
        description="Scores per model: {provider: {correctness, security, performance, maintainability}}",
    )
    critiques: list[str] = Field(default_factory=list, description="Critiques from each model")
    consensus_reached: bool
    synthesis_required: bool


class ValidationResult(BaseModel):
    """Schema for validation pipeline results."""

    stage: str
    passed: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    duration_ms: int | None = None


class SandboxResult(BaseModel):
    """Schema for sandbox execution results."""

    success: bool
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    execution_time_ms: int | None = None
    memory_used_bytes: int | None = None
    timeout: bool = False
    error_message: str | None = None


class TaskResult(BaseModel):
    """Response schema for final task result."""

    id: UUID
    status: str
    final_code: str
    final_tests: str | None = None
    final_documentation: str | None = None
    known_limitations: str | None = None
    validation_results: list[ValidationResult] | None = None
    sandbox_results: SandboxResult | None = None
    model_calls: list[dict] = Field(default_factory=list, description="Model call metadata")
    total_tokens: int | None = None
    total_latency_ms: int | None = None
    created_at: datetime
    completed_at: datetime | None = None


class ErrorResponse(BaseModel):
    """Standard error response schema."""

    error: str
    message: str
    details: dict | None = None


# WebSocket Message Schemas
class WSMessage(BaseModel):
    """Base WebSocket message schema."""

    type: str  # "status_update", "progress", "error", "complete"
    task_id: UUID
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime | None = None


class ProgressUpdate(BaseModel):
    """Progress update message."""

    stage: str
    progress_percent: float
    message: str
    details: dict[str, Any] | None = None
