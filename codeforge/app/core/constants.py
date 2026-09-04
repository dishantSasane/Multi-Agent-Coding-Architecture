"""Constants and enums for CodeForge."""

from enum import StrEnum, auto


class TaskStatus(StrEnum):
    """Task status enumeration."""

    PENDING = auto()
    INTENT_ANALYZING = auto()
    AWAITING_CONFIRMATION = auto()
    CONFIRMED = auto()
    DECOMPOSING = auto()
    GENERATING = auto()
    DEBATING = auto()
    SYNTHESIZING = auto()
    VALIDATING = auto()
    SANDBOX_EXECUTING = auto()
    CORRECTING = auto()
    COMPLETED = auto()
    FAILED = auto()


class ModelProvider(StrEnum):
    """LLM provider enumeration."""

    OPENROUTER = "openrouter"  # Free-tier routing via openrouter.ai
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    KIMI = "kimi"
    QWEN = "qwen"
    GEMINI = "gemini"


class TaskType(StrEnum):
    """Task type for routing decisions."""

    ARCHITECTURE = "architecture"
    IMPLEMENTATION = "implementation"
    ALGORITHM = "algorithm"
    DOCUMENTATION = "documentation"
    ANALYSIS = "analysis"
    DEBUGGING = "debugging"
    TESTING = "testing"


class ValidationStage(StrEnum):
    """Validation pipeline stages."""

    SYNTAX = "syntax"
    STATIC_ANALYSIS = "static_analysis"
    SECURITY_SCAN = "security_scan"
    UNIT_TESTS = "unit_tests"
    PROPERTY_TESTS = "property_tests"
    IMPORT_RESOLUTION = "import_resolution"


class ConfirmationStatus(StrEnum):
    """User confirmation status."""

    PENDING = auto()
    CONFIRMED = auto()
    REJECTED = auto()
    CLARIFIED = auto()


# Model routing defaults
DEFAULT_MODEL_TIMEOUT = 30
REASONING_MODEL_TIMEOUT = 120
MAX_CORRECTION_ATTEMPTS = 3
DEFAULT_ENSEMBLE_SIZE = 3

# Circuit breaker defaults
CIRCUIT_BREAKER_FAILURE_THRESHOLD = 5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT = 30

# Sandbox defaults
SANDBOX_TIMEOUT = 30
SANDBOX_MEMORY_LIMIT = "512m"
SANDBOX_CPU_LIMIT = 1.0

# Validation defaults
HYPOTHESIS_ITERATIONS = 100

# Task type to model mapping — all tasks route through Gemini.
TASK_TYPE_MODEL_MAP: dict[TaskType, ModelProvider] = {
    TaskType.ARCHITECTURE:   ModelProvider.GEMINI,
    TaskType.IMPLEMENTATION: ModelProvider.GEMINI,
    TaskType.ALGORITHM:      ModelProvider.GEMINI,
    TaskType.DOCUMENTATION:  ModelProvider.GEMINI,
    TaskType.ANALYSIS:       ModelProvider.GEMINI,
    TaskType.DEBUGGING:      ModelProvider.GEMINI,
    TaskType.TESTING:        ModelProvider.GEMINI,
}

# Model names per provider.
# LiteLLM format for Gemini: "gemini/<model>" — reads GEMINI_API_KEY from env.
PROVIDER_MODELS: dict[ModelProvider, list[str]] = {
    ModelProvider.GEMINI:    ["gemini-3.5-flash-lite"],   # primary: fast + free quota
    ModelProvider.OPENROUTER: ["free"],
    ModelProvider.OPENAI:    ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
    ModelProvider.ANTHROPIC: ["claude-sonnet-5", "claude-opus-5", "claude-haiku-4-5-20251001"],
    ModelProvider.KIMI:      ["kimi-k1.5"],
    ModelProvider.QWEN:      ["qwen-2.5-coder-32b-instruct", "qwen-2.5-72b-instruct"],
}

# Per-task model slug for Gemini (used by _get_model_for_provider).
GEMINI_TASK_MODEL_MAP: dict[TaskType, str] = {
    TaskType.ARCHITECTURE:   "gemini-3.5-flash-lite",
    TaskType.IMPLEMENTATION: "gemini-3.5-flash-lite",
    TaskType.ALGORITHM:      "gemini-3.5-flash-lite",
    TaskType.DOCUMENTATION:  "gemini-3.5-flash-lite",
    TaskType.ANALYSIS:       "gemini-3.5-flash-lite",
    TaskType.DEBUGGING:      "gemini-3.5-flash-lite",
    TaskType.TESTING:        "gemini-3.5-flash-lite",
}

# Kept for backward-compat import (no longer used for routing).
OPENROUTER_TASK_MODEL_MAP: dict[TaskType, str] = {t: "free" for t in TaskType}
