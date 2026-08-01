"""Orchestrator Service - Main state machine coordinating all services."""

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import (
    CodeForgeException,
    ConfirmationRequiredError,
    SelfCorrectionExhaustedError,
    TaskNotFoundError,
)
from app.models.database import get_session_maker
from app.models.enums import ConfirmationStatusEnum, TaskStatusEnum
from app.models.models import IntentAnalysis, Task
from app.services.debate_engine import DebateEngineService
from app.services.ensemble import EnsembleService
from app.services.fallback import FallbackService
from app.services.intent_parser import IntentParserService
from app.services.model_router import ModelRouterService
from app.services.sandbox import SandboxService
from app.services.self_correction import SelfCorrectionService
from app.services.synthesis import SynthesisService
from app.services.task_decomposer import TaskDecomposerService
from app.services.validator import ValidatorService

logger = structlog.get_logger(__name__)


class OrchestratorService:
    """Main orchestrator coordinating the code generation pipeline."""

    def __init__(self) -> None:
        """Initialize orchestrator service."""
        self.settings = get_settings()
        self.session_maker = get_session_maker()

        # Initialize all services
        self.intent_parser = IntentParserService()
        self.task_decomposer = TaskDecomposerService()
        self.model_router = ModelRouterService()
        self.ensemble = EnsembleService()
        self.debate_engine = DebateEngineService()
        self.synthesis = SynthesisService()
        self.validator = ValidatorService()
        self.sandbox = SandboxService()
        self.self_correction = SelfCorrectionService()
        self.fallback = FallbackService()

    async def create_task(
        self,
        user_query: str,
        context: dict[str, Any] | None = None,
        preferences: dict[str, Any] | None = None,
    ) -> Task:
        """Create a new task.

        Args:
            user_query: The user's coding query.
            context: Optional additional context.
            preferences: Optional user preferences.

        Returns:
            Created Task object.
        """
        logger.info("creating_task", query_length=len(user_query))

        async with self.session_maker() as session:
            task = Task(
                user_query=user_query,
                status=TaskStatusEnum.PENDING,
            )

            session.add(task)
            await session.commit()
            await session.refresh(task)

            logger.info("task_created", task_id=str(task.id))
            return task

    async def analyze_intent(self, task_id: UUID) -> IntentAnalysis:
        """Analyze intent for a task.

        Args:
            task_id: Task UUID.

        Returns:
            IntentAnalysis result.

        Raises:
            TaskNotFoundError: If task not found.
        """
        logger.info("analyzing_intent", task_id=str(task_id))

        async with self.session_maker() as session:
            task = await self._get_task(session, task_id)
            if not task:
                raise TaskNotFoundError(str(task_id))

            # Update status
            task.status = TaskStatusEnum.INTENT_ANALYZING
            await session.commit()

            try:
                # Parse intent
                intent = await self.intent_parser.parse_intent(
                    query=task.user_query,
                    context=task.intent_analysis or {},
                )

                # Store results
                task.intent_analysis = intent.model_dump()
                task.clarifying_questions = intent.clarifying_questions or []

                # Check if confirmation needed
                if self.intent_parser.needs_clarification(intent):
                    task.status = TaskStatusEnum.AWAITING_CONFIRMATION
                else:
                    task.status = TaskStatusEnum.CONFIRMED

                await session.commit()

                logger.info(
                    "intent_analyzed",
                    task_id=str(task_id),
                    confidence=intent.confidence_score,
                )

                return intent

            except Exception as e:
                logger.exception("intent_analysis_failed", error=str(e))
                task.status = TaskStatusEnum.FAILED
                task.last_error = str(e)
                await session.commit()
                raise

    async def confirm_intent(
        self,
        task_id: UUID,
        confirmed: bool,
        clarifications: str | None = None,
    ) -> Task:
        """Confirm or clarify intent.

        Args:
            task_id: Task UUID.
            confirmed: Whether user confirmed.
            clarifications: Optional clarifications from user.

        Returns:
            Updated Task.

        Raises:
            TaskNotFoundError: If task not found.
        """
        logger.info("confirming_intent", task_id=str(task_id), confirmed=confirmed)

        async with self.session_maker() as session:
            task = await self._get_task(session, task_id)
            if not task:
                raise TaskNotFoundError(str(task_id))

            if confirmed:
                task.confirmation_status = ConfirmationStatusEnum.CONFIRMED
                task.status = TaskStatusEnum.CONFIRMED
            else:
                task.confirmation_status = ConfirmationStatusEnum.CLARIFIED
                task.user_clarifications = clarifications
                task.status = TaskStatusEnum.INTENT_ANALYZING  # Re-analyze

            await session.commit()
            await session.refresh(task)

            return task

    async def generate_code(self, task_id: UUID) -> Task:
        """Generate code using ensemble approach.

        Args:
            task_id: Task UUID.

        Returns:
            Updated Task.

        Raises:
            TaskNotFoundError: If task not found.
        """
        logger.info("generating_code", task_id=str(task_id))

        async with self.session_maker() as session:
            task = await self._get_task(session, task_id)
            if not task:
                raise TaskNotFoundError(str(task_id))

            task.status = TaskStatusEnum.GENERATING
            await session.commit()

            try:
                # Get intent
                intent_data = task.intent_analysis or {}
                intent = IntentAnalysis(**intent_data) if intent_data else None

                # Build prompt
                prompt = self._build_generation_prompt(task, intent)

                # Generate ensemble
                outputs = await self.ensemble.generate_ensemble(
                    prompt=prompt,
                    system_prompt=self._get_system_prompt(),
                )

                if not outputs:
                    raise CodeForgeException("No model outputs generated")

                # Store outputs
                task.model_outputs = [o.model_dump() for o in outputs]
                await session.commit()

                logger.info(
                    "code_generated",
                    task_id=str(task_id),
                    output_count=len(outputs),
                )

                return task

            except Exception as e:
                logger.exception("code_generation_failed", error=str(e))
                task.status = TaskStatusEnum.FAILED
                task.last_error = str(e)
                await session.commit()
                raise

    async def run_debate(self, task_id: UUID) -> Task:
        """Run adversarial debate on generated code.

        Args:
            task_id: Task UUID.

        Returns:
            Updated Task.
        """
        logger.info("running_debate", task_id=str(task_id))

        async with self.session_maker() as session:
            task = await self._get_task(session, task_id)
            if not task:
                raise TaskNotFoundError(str(task_id))

            task.status = TaskStatusEnum.DEBATING
            await session.commit()

            try:
                # Load model outputs
                from app.models.models import ModelOutput

                outputs = [
                    ModelOutput(**o) for o in (task.model_outputs or [])
                ]

                # Run debate
                debate_result = await self.debate_engine.run_debate(outputs)

                # Store results
                task.debate_result = debate_result.model_dump()
                await session.commit()

                logger.info(
                    "debate_complete",
                    task_id=str(task_id),
                    winner=debate_result.winner_provider,
                )

                return task

            except Exception as e:
                logger.exception("debate_failed", error=str(e))
                task.status = TaskStatusEnum.FAILED
                task.last_error = str(e)
                await session.commit()
                raise

    async def synthesize_solution(self, task_id: UUID) -> Task:
        """Synthesize final solution from debate results.

        Args:
            task_id: Task UUID.

        Returns:
            Updated Task.
        """
        logger.info("synthesizing_solution", task_id=str(task_id))

        async with self.session_maker() as session:
            task = await self._get_task(session, task_id)
            if not task:
                raise TaskNotFoundError(str(task_id))

            task.status = TaskStatusEnum.SYNTHESIZING
            await session.commit()

            try:
                # Load data
                from app.models.models import DebateResult, ModelOutput

                outputs = [
                    ModelOutput(**o) for o in (task.model_outputs or [])
                ]
                debate_result = DebateResult(**(task.debate_result or {}))

                # Synthesize
                synthesis_result = await self.synthesis.synthesize(
                    outputs, debate_result
                )

                # Store results
                task.synthesized_code = synthesis_result["code"]
                task.synthesized_reasoning = synthesis_result["reasoning"]
                task.known_limitations = "\n".join(
                    synthesis_result.get("known_limitations", [])
                )
                await session.commit()

                logger.info(
                    "synthesis_complete",
                    task_id=str(task_id),
                    code_length=len(synthesis_result["code"]),
                )

                return task

            except Exception as e:
                logger.exception("synthesis_failed", error=str(e))
                task.status = TaskStatusEnum.FAILED
                task.last_error = str(e)
                await session.commit()
                raise

    async def validate_code(self, task_id: UUID) -> Task:
        """Validate synthesized code.

        Args:
            task_id: Task UUID.

        Returns:
            Updated Task.
        """
        logger.info("validating_code", task_id=str(task_id))

        async with self.session_maker() as session:
            task = await self._get_task(session, task_id)
            if not task:
                raise TaskNotFoundError(str(task_id))

            task.status = TaskStatusEnum.VALIDATING
            await session.commit()

            try:
                # Validate
                validation_results = await self.validator.validate_all(
                    code=task.synthesized_code or "",
                    test_code=task.final_tests,
                )

                # Store results
                task.validation_results = [r.model_dump() for r in validation_results]

                # Check if passed
                if self.validator.all_passed(validation_results):
                    task.status = TaskStatusEnum.SANDBOX_EXECUTING
                else:
                    task.status = TaskStatusEnum.CORRECTING
                    task.correction_attempts += 1

                await session.commit()

                logger.info(
                    "validation_complete",
                    task_id=str(task_id),
                    passed=self.validator.all_passed(validation_results),
                )

                return task

            except Exception as e:
                logger.exception("validation_failed", error=str(e))
                task.status = TaskStatusEnum.FAILED
                task.last_error = str(e)
                await session.commit()
                raise

    async def execute_in_sandbox(self, task_id: UUID) -> Task:
        """Execute code in sandbox.

        Args:
            task_id: Task UUID.

        Returns:
            Updated Task.
        """
        logger.info("executing_in_sandbox", task_id=str(task_id))

        async with self.session_maker() as session:
            task = await self._get_task(session, task_id)
            if not task:
                raise TaskNotFoundError(str(task_id))

            try:
                # Execute
                result = await self.sandbox.execute_python(
                    code=task.synthesized_code or "",
                    test_code=task.final_tests,
                )

                # Store results
                task.sandbox_results = result

                if result.get("success"):
                    task.status = TaskStatusEnum.COMPLETED
                    task.final_code = task.synthesized_code
                    task.completed_at = datetime.now(timezone.utc)
                else:
                    task.status = TaskStatusEnum.CORRECTING
                    task.correction_attempts += 1

                await session.commit()

                logger.info(
                    "sandbox_execution_complete",
                    task_id=str(task_id),
                    success=result.get("success"),
                )

                return task

            except Exception as e:
                logger.exception("sandbox_execution_failed", error=str(e))
                task.status = TaskStatusEnum.FAILED
                task.last_error = str(e)
                await session.commit()
                raise

    async def run_full_pipeline(self, task_id: UUID) -> Task:
        """Run the full code generation pipeline.

        Args:
            task_id: Task UUID.

        Returns:
            Final Task state.
        """
        logger.info("running_full_pipeline", task_id=str(task_id))

        try:
            # Step 1: Analyze intent
            await self.analyze_intent(task_id)

            # Step 2: Check if confirmation needed
            async with self.session_maker() as session:
                task = await self._get_task(session, task_id)
                if task and task.status == TaskStatusEnum.AWAITING_CONFIRMATION:
                    logger.info("awaiting_confirmation", task_id=str(task_id))
                    return task

            # Step 3: Generate code
            await self.generate_code(task_id)

            # Step 4: Run debate
            await self.run_debate(task_id)

            # Step 5: Synthesize
            await self.synthesize_solution(task_id)

            # Step 6: Validate and potentially correct
            max_corrections = self.settings.max_correction_attempts

            for attempt in range(max_corrections + 1):
                # Validate
                await self.validate_code(task_id)

                async with self.session_maker() as session:
                    task = await self._get_task(session, task_id)
                    if not task:
                        break

                    if task.status == TaskStatusEnum.SANDBOX_EXECUTING:
                        break

                    if task.correction_attempts >= max_corrections:
                        task.status = TaskStatusEnum.FAILED
                        task.last_error = "Max correction attempts reached"
                        await session.commit()
                        raise SelfCorrectionExhaustedError(
                            attempts=max_corrections,
                            last_error="Validation failed after all corrections",
                        )

            # Step 7: Execute in sandbox
            await self.execute_in_sandbox(task_id)

            logger.info("pipeline_complete", task_id=str(task_id))

            async with self.session_maker() as session:
                task = await self._get_task(session, task_id)
                return task or Task()

        except Exception as e:
            logger.exception("pipeline_failed", error=str(e))
            raise

    async def _get_task(
        self, session: AsyncSession, task_id: UUID
    ) -> Task | None:
        """Get task by ID.

        Args:
            session: Database session.
            task_id: Task UUID.

        Returns:
            Task or None.
        """
        result = await session.execute(
            select(Task).where(Task.id == task_id)
        )
        return result.scalar_one_or_none()

    def _build_generation_prompt(
        self,
        task: Task,
        intent: IntentAnalysis | None,
    ) -> str:
        """Build code generation prompt.

        Args:
            task: Task object.
            intent: Parsed intent.

        Returns:
            Generation prompt string.
        """
        lines = ["Generate production-ready code for the following request:\n"]

        if intent:
            lines.append(f"**Summary:** {intent.summary}")
            lines.append(f"**Requirements:**\n" + "\n".join(f"- {r}" for r in intent.requirements))
            lines.append(f"**Tech Stack:** {', '.join(intent.tech_stack)}")
            if intent.constraints:
                lines.append(f"**Constraints:**\n" + "\n".join(f"- {c}" for c in intent.constraints))
            if intent.edge_cases:
                lines.append(f"**Edge Cases:**\n" + "\n".join(f"- {e}" for e in intent.edge_cases))

        lines.append(f"\n**Original Query:** {task.user_query}")

        if task.user_clarifications:
            lines.append(f"\n**User Clarifications:** {task.user_clarifications}")

        lines.append("\n\nRules:")
        lines.append("- Write complete, working code")
        lines.append("- Include comprehensive error handling")
        lines.append("- Add type hints and docstrings")
        lines.append("- Follow best practices")
        lines.append("- Handle all edge cases")
        lines.append("- Consider security implications")
        lines.append("- NO placeholder code or TODOs")

        return "\n".join(lines)

    def _get_system_prompt(self) -> str:
        """Get system prompt for code generation.

        Returns:
            System prompt string.
        """
        return """You are an expert software developer specializing in writing production-ready code.
Your code is always:
- Complete and functional
- Well-documented with docstrings
- Type-hinted
- Secure and follows best practices
- Handles all edge cases
- Includes proper error handling

Never use placeholders or TODOs. Always write complete, working solutions."""


# Global orchestrator instance
_orchestrator: OrchestratorService | None = None


def get_orchestrator() -> OrchestratorService:
    """Get global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = OrchestratorService()
    return _orchestrator
