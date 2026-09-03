"""Unit tests for orchestrator service."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.core.exceptions import CodeForgeException
from app.models.enums import TaskStatus
from app.services.orchestrator import Orchestrator


class TestOrchestrator:
    """Test orchestrator service."""

    @pytest_asyncio.fixture
    async def mock_db(self):
        """Create mock database session."""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        return mock_session

    @pytest_asyncio.fixture
    def orchestrator(self, mock_db):
        """Create orchestrator instance."""
        return Orchestrator(db=lambda: mock_db)

    @pytest.mark.asyncio
    async def test_create_task(self, orchestrator, mock_db, sample_query):
        """Test task creation."""
        task_id = str(uuid.uuid4())
        
        with patch("uuid.uuid4", return_value=task_id):
            task = await orchestrator.create_task(
                user_query=sample_query,
                context=None,
                preferences=None,
            )
            
            assert task.id == task_id
            assert task.user_query == sample_query
            assert task.status == TaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_analyze_intent(self, orchestrator, mock_db, sample_intent_analysis):
        """Test intent analysis."""
        task_id = str(uuid.uuid4())
        
        with patch.object(orchestrator.intent_parser, "analyze") as mock_analyze:
            mock_analyze.return_value = sample_intent_analysis
            
            result = await orchestrator.analyze_intent(task_id)
            
            assert result is not None
            mock_analyze.assert_called_once()

    @pytest.mark.asyncio
    async def test_confirm_intent(self, orchestrator, mock_db):
        """Test intent confirmation."""
        task_id = str(uuid.uuid4())
        
        mock_task = MagicMock()
        mock_task.id = task_id
        mock_task.status = TaskStatus.AWAITING_CONFIRMATION
        
        with patch.object(orchestrator, "_get_task", return_value=mock_task):
            with patch.object(orchestrator, "_update_task_status") as mock_update:
                result = await orchestrator.confirm_intent(
                    task_id=task_id,
                    confirmed=True,
                    clarifications=None,
                )
                
                mock_update.assert_called_once()
                assert result.status == TaskStatus.CONFIRMED

    @pytest.mark.asyncio
    async def test_generate_code_ensemble(self, orchestrator, mock_db, sample_model_output):
        """Test code generation with ensemble."""
        task_id = str(uuid.uuid4())
        
        mock_outputs = [sample_model_output.copy() for _ in range(3)]
        
        with patch.object(orchestrator.ensemble, "generate") as mock_generate:
            mock_generate.return_value = {"outputs": mock_outputs}
            
            result = await orchestrator.generate_code(task_id)
            
            assert result is not None
            mock_generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_debate(self, orchestrator, mock_db):
        """Test debate engine."""
        task_id = str(uuid.uuid4())
        model_outputs = [{"code": f"print({i})"} for i in range(3)]
        
        with patch.object(orchestrator.debate_engine, "run_debate") as mock_debate:
            mock_debate.return_value = {"winner": "model_1", "consensus": True}
            
            result = await orchestrator.run_debate(task_id, model_outputs)
            
            assert result is not None
            mock_debate.assert_called_once()

    @pytest.mark.asyncio
    async def test_synthesize_solution(self, orchestrator, mock_db):
        """Test solution synthesis."""
        task_id = str(uuid.uuid4())
        debate_result = {"winner": "model_1"}
        
        with patch.object(orchestrator.synthesis_engine, "synthesize") as mock_synthesize:
            mock_synthesize.return_value = {
                "final_code": "print('hello')",
                "tests": "def test_hello(): pass",
            }
            
            result = await orchestrator.synthesize(task_id, debate_result)
            
            assert result is not None
            mock_synthesize.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_code(self, orchestrator, mock_db):
        """Test code validation."""
        task_id = str(uuid.uuid4())
        code = "print('hello')"
        
        with patch.object(orchestrator.validator, "validate_all") as mock_validate:
            mock_validate.return_value = {
                "syntax_valid": True,
                "security_valid": True,
                "all_passed": True,
            }
            
            result = await orchestrator.validate_code(task_id, code)
            
            assert result["all_passed"] is True
            mock_validate.assert_called_once()

    @pytest.mark.asyncio
    async def test_sandbox_execute(self, orchestrator, mock_db):
        """Test sandbox execution."""
        task_id = str(uuid.uuid4())
        code = "print('hello')"
        
        with patch.object(orchestrator.sandbox, "execute") as mock_execute:
            mock_execute.return_value = {
                "exit_code": 0,
                "stdout": "hello\n",
                "stderr": "",
                "success": True,
            }
            
            result = await orchestrator.execute_in_sandbox(task_id, code)
            
            assert result["success"] is True
            mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_self_correction(self, orchestrator, mock_db):
        """Test self-correction loop."""
        task_id = str(uuid.uuid4())
        code = "print('hello')"
        error_context = {"error": "SyntaxError", "message": "invalid syntax"}
        
        with patch.object(orchestrator.self_correction, "correct") as mock_correct:
            mock_correct.return_value = {
                "corrected_code": "print('hello')",
                "success": True,
            }
            
            result = await orchestrator.self_correct(task_id, code, error_context, attempt=1)
            
            assert result["success"] is True
            mock_correct.assert_called_once()

    @pytest.mark.asyncio
    async def test_full_pipeline(self, orchestrator, mock_db):
        """Test full pipeline execution."""
        task_id = str(uuid.uuid4())
        
        mock_task = MagicMock()
        mock_task.id = task_id
        mock_task.status = TaskStatus.PENDING
        
        with patch.object(orchestrator, "_get_task", return_value=mock_task):
            with patch.object(orchestrator, "analyze_intent"):
                with patch.object(orchestrator, "generate_code"):
                    with patch.object(orchestrator, "run_debate"):
                        with patch.object(orchestrator, "synthesize"):
                            with patch.object(orchestrator, "validate_code"):
                                with patch.object(orchestrator, "execute_in_sandbox"):
                                    result = await orchestrator.run_full_pipeline(task_id)
                                    
                                    assert result is not None

    @pytest.mark.asyncio
    async def test_error_handling(self, orchestrator, mock_db):
        """Test error handling in orchestrator."""
        task_id = str(uuid.uuid4())
        
        with patch.object(orchestrator.intent_parser, "analyze") as mock_analyze:
            mock_analyze.side_effect = CodeForgeException("Intent parsing failed")
            
            with pytest.raises(CodeForgeException):
                await orchestrator.analyze_intent(task_id)
