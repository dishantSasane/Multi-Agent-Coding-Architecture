"""Unit tests for OrchestratorService (app/services/orchestrator.py)."""

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import CodeForgeException, SelfCorrectionExhaustedError, TaskNotFoundError
from app.models.enums import TaskStatusEnum
from app.models.orm_models import Task
from app.services.orchestrator import OrchestratorService


def _fake_session_maker():
    """A session_maker whose `async with maker() as session` yields a mock
    AsyncSession where add/commit/refresh are no-ops. This mirrors real
    SQLAlchemy usage closely enough that Task objects keep whatever fields
    the orchestrator set on them without needing a real database.
    """
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()

    @asynccontextmanager
    async def _cm():
        yield session

    return (lambda: _cm()), session


@pytest.fixture
def orchestrator():
    with patch("app.services.orchestrator.get_session_maker") as mock_get_maker:
        maker, session = _fake_session_maker()
        mock_get_maker.return_value = maker
        service = OrchestratorService()
        service._session = session  # exposed for assertions
        yield service


def _scalar_result(task: Task | None):
    result = MagicMock()
    result.scalar_one_or_none.return_value = task
    return result


class TestOrchestratorService:
    """Test orchestrator service."""

    @pytest.mark.asyncio
    async def test_create_task(self, orchestrator, sample_query):
        task = await orchestrator.create_task(user_query=sample_query)

        assert task.user_query == sample_query
        assert task.status == TaskStatusEnum.PENDING

    @pytest.mark.asyncio
    async def test_analyze_intent_not_found_raises(self, orchestrator):
        orchestrator._session.execute.return_value = _scalar_result(None)

        with pytest.raises(TaskNotFoundError):
            await orchestrator.analyze_intent(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_analyze_intent_success(self, orchestrator, sample_intent_analysis):
        task = Task(user_query="build a thing", status=TaskStatusEnum.PENDING)
        orchestrator._session.execute.return_value = _scalar_result(task)

        fake_intent = MagicMock()
        fake_intent.model_dump.return_value = sample_intent_analysis
        fake_intent.clarifying_questions = []
        fake_intent.confidence_score = 0.95
        orchestrator.intent_parser.parse_intent = AsyncMock(return_value=fake_intent)
        orchestrator.intent_parser.needs_clarification = MagicMock(return_value=False)

        result = await orchestrator.analyze_intent(uuid.uuid4())

        assert result is fake_intent
        assert task.status == TaskStatusEnum.CONFIRMED

    @pytest.mark.asyncio
    async def test_analyze_intent_needs_clarification(self, orchestrator, sample_intent_analysis):
        task = Task(user_query="build a thing", status=TaskStatusEnum.PENDING)
        orchestrator._session.execute.return_value = _scalar_result(task)

        fake_intent = MagicMock()
        fake_intent.model_dump.return_value = sample_intent_analysis
        fake_intent.clarifying_questions = ["What language?"]
        fake_intent.confidence_score = 0.4
        orchestrator.intent_parser.parse_intent = AsyncMock(return_value=fake_intent)
        orchestrator.intent_parser.needs_clarification = MagicMock(return_value=True)

        await orchestrator.analyze_intent(uuid.uuid4())

        assert task.status == TaskStatusEnum.AWAITING_CONFIRMATION

    @pytest.mark.asyncio
    async def test_analyze_intent_marks_failed_on_error(self, orchestrator):
        task = Task(user_query="build a thing", status=TaskStatusEnum.PENDING)
        orchestrator._session.execute.return_value = _scalar_result(task)
        orchestrator.intent_parser.parse_intent = AsyncMock(
            side_effect=CodeForgeException("intent parsing failed")
        )

        with pytest.raises(CodeForgeException):
            await orchestrator.analyze_intent(uuid.uuid4())

        assert task.status == TaskStatusEnum.FAILED
        assert task.last_error == "intent parsing failed"

    @pytest.mark.asyncio
    async def test_confirm_intent_confirmed(self, orchestrator):
        task = Task(user_query="q", status=TaskStatusEnum.AWAITING_CONFIRMATION)
        orchestrator._session.execute.return_value = _scalar_result(task)

        result = await orchestrator.confirm_intent(uuid.uuid4(), confirmed=True)

        assert result.status == TaskStatusEnum.CONFIRMED

    @pytest.mark.asyncio
    async def test_confirm_intent_clarified_goes_back_to_analyzing(self, orchestrator):
        task = Task(user_query="q", status=TaskStatusEnum.AWAITING_CONFIRMATION)
        orchestrator._session.execute.return_value = _scalar_result(task)

        result = await orchestrator.confirm_intent(
            uuid.uuid4(), confirmed=False, clarifications="use Python"
        )

        assert result.status == TaskStatusEnum.INTENT_ANALYZING
        assert result.user_clarifications == "use Python"

    @pytest.mark.asyncio
    async def test_generate_code(self, orchestrator, sample_model_output):
        task = Task(user_query="build a thing", status=TaskStatusEnum.CONFIRMED)
        orchestrator._session.execute.return_value = _scalar_result(task)

        fake_output = MagicMock()
        fake_output.model_dump.return_value = sample_model_output
        orchestrator.ensemble.generate_ensemble = AsyncMock(return_value=[fake_output])

        result = await orchestrator.generate_code(uuid.uuid4())

        assert result.status == TaskStatusEnum.GENERATING
        assert result.model_outputs == [sample_model_output]

    @pytest.mark.asyncio
    async def test_generate_code_no_outputs_raises(self, orchestrator):
        task = Task(user_query="build a thing", status=TaskStatusEnum.CONFIRMED)
        orchestrator._session.execute.return_value = _scalar_result(task)
        orchestrator.ensemble.generate_ensemble = AsyncMock(return_value=[])

        with pytest.raises(CodeForgeException):
            await orchestrator.generate_code(uuid.uuid4())

        assert task.status == TaskStatusEnum.FAILED

    @pytest.mark.asyncio
    async def test_run_debate(self, orchestrator):
        task = Task(user_query="q", status=TaskStatusEnum.GENERATING, model_outputs=[])

        fake_result = MagicMock()
        fake_result.model_dump.return_value = {"winner_provider": "groq"}
        fake_result.winner_provider = "groq"
        orchestrator._session.execute.return_value = _scalar_result(task)
        orchestrator.debate_engine.run_debate = AsyncMock(return_value=fake_result)

        result = await orchestrator.run_debate(uuid.uuid4())

        assert result.debate_result == {"winner_provider": "groq"}

    @pytest.mark.asyncio
    async def test_select_best_output_heuristic(self, orchestrator, sample_model_output):
        outputs = [
            {**sample_model_output, "provider": "groq", "code": "def f(): pass"},
            {**sample_model_output, "provider": "openrouter", "code": "TODO"},
        ]
        task = Task(user_query="q", status=TaskStatusEnum.GENERATING, model_outputs=outputs)
        orchestrator._session.execute.return_value = _scalar_result(task)

        result = await orchestrator.select_best_output(uuid.uuid4())

        assert result.debate_result["winner_provider"] == "groq"

    @pytest.mark.asyncio
    async def test_validate_code_all_passed_moves_to_sandbox(self, orchestrator):
        task = Task(
            user_query="q",
            status=TaskStatusEnum.SYNTHESIZING,
            synthesized_code="print('hi')",
            correction_attempts=0,
        )
        orchestrator._session.execute.return_value = _scalar_result(task)

        passing_result = MagicMock()
        passing_result.passed = True
        passing_result.model_dump.return_value = {"stage": "syntax", "passed": True}
        orchestrator.validator.validate_all = AsyncMock(return_value=[passing_result])
        orchestrator.validator.all_passed = MagicMock(return_value=True)

        result = await orchestrator.validate_code(uuid.uuid4())

        assert result.status == TaskStatusEnum.SANDBOX_EXECUTING

    @pytest.mark.asyncio
    async def test_validate_code_failure_moves_to_correcting(self, orchestrator):
        task = Task(
            user_query="q",
            status=TaskStatusEnum.SYNTHESIZING,
            synthesized_code="print('hi'",  # syntax error
            correction_attempts=0,
        )
        orchestrator._session.execute.return_value = _scalar_result(task)
        # max_correction_attempts defaults to 0 (self-correction disabled by
        # default) — set it explicitly to exercise the increment path.
        orchestrator.settings.max_correction_attempts = 3

        failing_result = MagicMock()
        failing_result.passed = False
        failing_result.stage = "syntax"
        failing_result.errors = ["SyntaxError"]
        failing_result.model_dump.return_value = {"stage": "syntax", "passed": False}
        orchestrator.validator.validate_all = AsyncMock(return_value=[failing_result])
        orchestrator.validator.all_passed = MagicMock(return_value=False)
        orchestrator.self_correction.correct_code = AsyncMock(return_value="print('hi')")

        result = await orchestrator.validate_code(uuid.uuid4())

        assert result.status == TaskStatusEnum.CORRECTING
        assert result.correction_attempts == 1
        assert result.synthesized_code == "print('hi')"
        orchestrator.self_correction.correct_code.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_in_sandbox_success(self, orchestrator):
        task = Task(user_query="q", status=TaskStatusEnum.SANDBOX_EXECUTING, synthesized_code="x=1")
        orchestrator._session.execute.return_value = _scalar_result(task)
        orchestrator.sandbox.execute_python = AsyncMock(return_value={"success": True})

        result = await orchestrator.execute_in_sandbox(uuid.uuid4())

        assert result.status == TaskStatusEnum.COMPLETED
        assert result.final_code == "x=1"

    @pytest.mark.asyncio
    async def test_execute_in_sandbox_failure_moves_to_correcting(self, orchestrator):
        task = Task(
            user_query="q",
            status=TaskStatusEnum.SANDBOX_EXECUTING,
            synthesized_code="x=1",
            correction_attempts=0,
        )
        orchestrator._session.execute.return_value = _scalar_result(task)
        orchestrator.sandbox.execute_python = AsyncMock(
            return_value={"success": False, "stderr": "boom"}
        )
        orchestrator.settings.max_correction_attempts = 3
        orchestrator.self_correction.correct_code = AsyncMock(return_value="x=2")

        result = await orchestrator.execute_in_sandbox(uuid.uuid4())

        assert result.status == TaskStatusEnum.CORRECTING
        assert result.correction_attempts == 1
        assert result.synthesized_code == "x=2"
        orchestrator.self_correction.correct_code.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_full_pipeline_fails_fast_when_max_corrections_zero(self, orchestrator):
        task_id = uuid.uuid4()
        task = Task(
            id=task_id,
            user_query="q",
            status=TaskStatusEnum.PENDING,
            correction_attempts=0,
        )
        orchestrator._session.execute.return_value = _scalar_result(task)
        orchestrator.settings.max_correction_attempts = 0
        orchestrator.settings.use_debate_engine = False
        orchestrator.settings.sandbox_enabled = False

        orchestrator.intent_parser.parse_intent = AsyncMock(
            return_value=MagicMock(
                model_dump=lambda: {}, clarifying_questions=[], confidence_score=0.9
            )
        )
        orchestrator.intent_parser.needs_clarification = MagicMock(return_value=False)

        fake_output = MagicMock()
        fake_output.model_dump.return_value = {
            "provider": "groq",
            "model_name": "test-model",
            "code": "TODO",
            "reasoning": "",
            "confidence": 0.5,
            "estimated_complexity": "low",
            "success": True,
        }
        orchestrator.ensemble.generate_ensemble = AsyncMock(return_value=[fake_output])

        orchestrator.synthesis.synthesize = AsyncMock(
            return_value={"code": "print(1)", "reasoning": "", "known_limitations": []}
        )

        failing_result = MagicMock()
        failing_result.passed = False
        failing_result.stage = "syntax"
        failing_result.errors = ["bad"]
        failing_result.model_dump.return_value = {"stage": "syntax", "passed": False}
        orchestrator.validator.validate_all = AsyncMock(return_value=[failing_result])
        orchestrator.validator.all_passed = MagicMock(return_value=False)

        result = await orchestrator.run_full_pipeline(task_id)

        assert result.status == TaskStatusEnum.FAILED

    @pytest.mark.asyncio
    async def test_run_full_pipeline_stops_at_confirmation(self, orchestrator):
        task_id = uuid.uuid4()
        task = Task(id=task_id, user_query="q", status=TaskStatusEnum.AWAITING_CONFIRMATION)
        orchestrator._session.execute.return_value = _scalar_result(task)

        orchestrator.intent_parser.parse_intent = AsyncMock(
            return_value=MagicMock(
                model_dump=lambda: {}, clarifying_questions=["?"], confidence_score=0.3
            )
        )
        orchestrator.intent_parser.needs_clarification = MagicMock(return_value=True)

        result = await orchestrator.run_full_pipeline(task_id)

        assert result.status == TaskStatusEnum.AWAITING_CONFIRMATION

    @pytest.mark.asyncio
    async def test_task_not_found_raises_across_methods(self, orchestrator):
        orchestrator._session.execute.return_value = _scalar_result(None)

        with pytest.raises(TaskNotFoundError):
            await orchestrator.confirm_intent(uuid.uuid4(), confirmed=True)


if __name__ == "__main__":
    import asyncio

    async def demo() -> None:
        with patch("app.services.orchestrator.get_session_maker") as mock_get_maker:
            maker, session = _fake_session_maker()
            mock_get_maker.return_value = maker
            service = OrchestratorService()
            task = await service.create_task(user_query="demo")
            assert task.status == TaskStatusEnum.PENDING
        print("self-check passed")

    asyncio.run(demo())


def test_test_requests_use_multi_file_prompt():
    """Code + tests come back as two files, so they need the multi-file format."""
    from app.services.orchestrator import OrchestratorService

    kw = OrchestratorService._MULTI_FILE_KEYWORDS
    assert kw.search("Write is_palindrome with a few pytest tests")
    assert not kw.search("Write a single Python function is_palindrome")


@pytest.mark.asyncio
async def test_invalid_candidate_loses_to_valid_one(orchestrator):
    """A longer candidate that fails validation must not beat a clean shorter one."""
    from app.models.models import ModelOutput

    def _out(provider: str, code: str) -> ModelOutput:
        return ModelOutput(
            provider=provider,
            model_name="m",
            code=code,
            reasoning="",
            confidence=0.85,
            estimated_complexity="medium",
            success=True,
        )

    # Longer, but uses eval() -> security scan fails.
    bad = _out("groq", "def run(expr: str) -> float:\n    return eval(expr)\n" + "# pad\n" * 80)
    good = _out("gemini", "def run(expr: str) -> float:\n    return float(expr)\n")

    kept = await orchestrator._validated_outputs([bad, good])
    assert [o.provider for o in kept] == ["gemini"]
    assert orchestrator._heuristic_vote(kept).provider == "gemini"


@pytest.mark.asyncio
async def test_all_invalid_candidates_are_kept(orchestrator):
    """When nothing validates, keep every candidate so real errors still surface."""
    from app.models.models import ModelOutput

    bad = ModelOutput(
        provider="groq",
        model_name="m",
        code="def run(e):\n    return eval(e)\n",
        reasoning="",
        confidence=0.85,
        estimated_complexity="medium",
        success=True,
    )
    assert await orchestrator._validated_outputs([bad]) == [bad]
