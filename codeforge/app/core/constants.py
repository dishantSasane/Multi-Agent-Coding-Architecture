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
    GROQ = "groq"
    GEMINI = "gemini"  # Google AI Studio free tier


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
MAX_CORRECTION_ATTEMPTS = 0
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

# Task type to model mapping — all tasks route through Groq.
TASK_TYPE_MODEL_MAP: dict[TaskType, ModelProvider] = {
    TaskType.ARCHITECTURE:   ModelProvider.GROQ,
    TaskType.IMPLEMENTATION: ModelProvider.GROQ,
    TaskType.ALGORITHM:      ModelProvider.GROQ,
    TaskType.DOCUMENTATION:  ModelProvider.GROQ,
    TaskType.ANALYSIS:       ModelProvider.GROQ,
    TaskType.DEBUGGING:      ModelProvider.GROQ,
    TaskType.TESTING:        ModelProvider.GROQ,
}

# OpenRouter: only ":free" models, so a paid model can never be picked.
# Tried in order on 429/503 — free endpoints go down constantly.
OPENROUTER_FREE_POOL = [
    "qwen/qwen3.8-27b:free",
    "deepseek/deepseek-v4-flash-0731:free",
    "cohere/north-mini-code:free",
    "google/gemma-4-31b-it:free",
]
OPENROUTER_FREE_MODEL = OPENROUTER_FREE_POOL[0]

# Model names per provider.
# LiteLLM format for Groq: "groq/<model>" — reads GROQ_API_KEY from env.
PROVIDER_MODELS: dict[ModelProvider, list[str]] = {
    ModelProvider.GROQ:      ["openai/gpt-oss-120b"],
    ModelProvider.OPENROUTER: [OPENROUTER_FREE_MODEL],
    ModelProvider.GEMINI:    ["gemini-3.1-flash-lite"],
    ModelProvider.OPENAI:    ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
    ModelProvider.ANTHROPIC: ["claude-sonnet-5", "claude-opus-5", "claude-haiku-4-5-20251001"],
    ModelProvider.KIMI:      ["kimi-k1.5"],
    ModelProvider.QWEN:      ["qwen-2.5-coder-32b-instruct", "qwen-2.5-72b-instruct"],
}

# Kept for backward-compat import (no longer used for routing).
OPENROUTER_TASK_MODEL_MAP: dict[TaskType, str] = {t: OPENROUTER_FREE_MODEL for t in TaskType}
