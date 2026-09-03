"""Celery configuration for CodeForge."""

import os
from celery import Celery
from kombu import Exchange, Queue

# Celery configuration
celery_app = Celery(
    "codeforge",
    broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0"),
    include=[
        "app.services.orchestrator",
        "app.services.intent_parser",
        "app.services.ensemble",
        "app.services.debate_engine",
        "app.services.synthesis",
        "app.services.sandbox",
        "app.services.validator",
        "app.services.self_correction",
    ],
)

# Task queues
celery_app.conf.task_queues = (
    Queue("default", Exchange("default"), routing_key="default"),
    Queue("llm_tasks", Exchange("llm_tasks"), routing_key="llm_tasks"),
    Queue("sandbox_tasks", Exchange("sandbox_tasks"), routing_key="sandbox_tasks"),
    Queue("validation_tasks", Exchange("validation_tasks"), routing_key="validation_tasks"),
)

celery_app.conf.task_default_queue = "default"
celery_app.conf.task_default_exchange = "default"
celery_app.conf.task_default_routing_key = "default"

# Task settings
celery_app.conf.task_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.result_serializer = "json"
celery_app.conf.timezone = "UTC"
celery_app.conf.enable_utc = True

# Retry settings
celery_app.conf.task_acks_late = True
celery_app.conf.task_reject_on_worker_or_lost = True
celery_app.conf.worker_prefetch_multiplier = 1

# Rate limiting
celery_app.conf.task_default_rate_limit = "10/m"

# Task time limits
celery_app.conf.task_time_limit = 300  # 5 minutes
celery_app.conf.task_soft_time_limit = 240  # 4 minutes


@celery_app.task(bind=True, max_retries=3)
def analyze_intent_task(self, task_id: str) -> dict:
    """Analyze user intent asynchronously."""
    try:
        from app.models.database import AsyncSessionLocal
        from app.services.intent_parser import IntentParser
        
        parser = IntentParser()
        result = parser.analyze(task_id)
        
        return {"success": True, "result": result}
    
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=3)
def generate_code_task(self, task_id: str, model_names: list[str] | None = None) -> dict:
    """Generate code using ensemble of models."""
    try:
        from app.services.ensemble import EnsembleEngine
        
        engine = EnsembleEngine()
        result = engine.generate(task_id, model_names)
        
        return {"success": True, "result": result}
    
    except Exception as exc:
        raise self.retry(exc=exc, countdown=120)


@celery_app.task(bind=True, max_retries=2)
def run_debate_task(self, task_id: str, model_outputs: list[dict]) -> dict:
    """Run adversarial debate between models."""
    try:
        from app.services.debate_engine import DebateEngine
        
        engine = DebateEngine()
        result = engine.run_debate(task_id, model_outputs)
        
        return {"success": True, "result": result}
    
    except Exception as exc:
        raise self.retry(exc=exc, countdown=90)


@celery_app.task(bind=True, max_retries=2)
def synthesize_task(self, task_id: str, debate_result: dict) -> dict:
    """Synthesize final solution from debate results."""
    try:
        from app.services.synthesis import SynthesisEngine
        
        engine = SynthesisEngine()
        result = engine.synthesize(task_id, debate_result)
        
        return {"success": True, "result": result}
    
    except Exception as exc:
        raise self.retry(exc=exc, countdown=90)


@celery_app.task(bind=True, max_retries=3)
def validate_task(self, task_id: str, code: str) -> dict:
    """Run validation pipeline on generated code."""
    try:
        from app.services.validator import Validator
        
        validator = Validator()
        result = validator.validate_all(task_id, code)
        
        return {"success": True, "result": result}
    
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=3)
def sandbox_execute_task(self, task_id: str, code: str, language: str = "python") -> dict:
    """Execute code in Docker sandbox."""
    try:
        from app.services.sandbox import SandboxExecutor
        
        executor = SandboxExecutor()
        result = executor.execute(task_id, code, language)
        
        return {"success": True, "result": result}
    
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(bind=True, max_retries=3)
def self_correct_task(
    self,
    task_id: str,
    code: str,
    error_context: dict,
    attempt: int = 1,
) -> dict:
    """Attempt to fix validation errors."""
    try:
        from app.services.self_correction import SelfCorrectionEngine
        
        engine = SelfCorrectionEngine()
        result = engine.correct(task_id, code, error_context, attempt)
        
        return {"success": True, "result": result}
    
    except Exception as exc:
        if attempt < 3:
            raise self.retry(exc=exc, countdown=60 * attempt)
        raise


@celery_app.task
def notify_user_task(task_id: str, status: str, message: str | None = None) -> dict:
    """Send notification to user about task status."""
    # This would integrate with WebSocket or other notification systems
    return {
        "success": True,
        "task_id": task_id,
        "status": status,
        "message": message,
    }
