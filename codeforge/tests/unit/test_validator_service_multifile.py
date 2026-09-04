from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.enums import ModelProvider
from app.models.models import CodeFile, DebateResult, ModelOutput, TaskStatusResponse
from app.services.code_extractor import CodeExtractionError, extract_code_files
from app.services.ensemble import EnsembleService
from app.services.orchestrator import OrchestratorService
from app.services.synthesis import SynthesisService
from app.services.validator import ValidatorService


@pytest.mark.asyncio
async def test_validate_all_checks_each_python_file_independently() -> None:
    validator = ValidatorService()

    results = await validator.validate_all(
        code="",
        files=[
            {"filename": "main.py", "content": "def main():\n    return 1\n"},
            {"filename": "agent.py", "content": "    return 1\n"},
            {"filename": "README.md", "content": "# Project\n"},
        ],
    )

    syntax = next(result for result in results if result.stage == "syntax")
    assert not syntax.passed
    assert syntax.errors == ["agent.py: Syntax error at line 1: unexpected indent"]


@pytest.mark.asyncio
async def test_security_scan_ignores_comments_and_strings() -> None:
    validator = ValidatorService()

    results = await validator.validate_all(
        'text = "eval(input)"\n# exec(unsafe)\n',
    )

    security = next(result for result in results if result.stage == "security_scan")
    assert security.passed


@pytest.mark.asyncio
async def test_env_and_documentation_are_not_parsed_as_python() -> None:
    validator = ValidatorService()

    results = await validator.validate_all(
        code="",
        files=[
            {"filename": ".env.example", "content": "GROQ_API_KEY=placeholder\n"},
            {"filename": "main.py", "content": "print('ok')\n"},
            {"filename": "requirements.txt", "content": "httpx==0.27.2\n"},
            {"filename": "README.md", "content": "# Gmail MCP\n"},
        ],
    )

    syntax = next(result for result in results if result.stage == "syntax")
    assert syntax.passed
    assert all(".env.example" not in error for error in syntax.errors)


@pytest.mark.asyncio
async def test_gmail_mcp_project_preserves_nested_paths() -> None:
    validator = ValidatorService()
    files = [
        {"filename": ".env.example", "content": "GMAIL_USER_EMAIL=example@gmail.com\n"},
        {"filename": "main.py", "content": "from agent import run\n"},
        {"filename": "agent.py", "content": "def run() -> None:\n    pass\n"},
        {"filename": "config.py", "content": "MCP_SERVER_COMMAND = 'npx'\n"},
        {"filename": "gmail/client.py", "content": "class GmailClient:\n    pass\n"},
        {"filename": "services/summarizer.py", "content": "def summarize() -> str:\n    return ''\n"},
        {"filename": "requirements.txt", "content": "httpx==0.27.2\n"},
        {"filename": "README.md", "content": "# Gmail MCP\n"},
    ]

    results = await validator.validate_all(code="", files=files)

    assert len(files) == 8
    assert next(result for result in results if result.stage == "syntax").passed


def test_named_fences_and_unsafe_paths() -> None:
    content = (
        "```python main.py\nprint('main')\n```\n"
        "```gmail/client.py\nclass Client:\n    pass\n```\n"
        "```.env.example\nKEY=value\n```\n"
    )

    files = extract_code_files(content)

    assert [file["filename"] for file in files or []] == [
        "main.py", "gmail/client.py", ".env.example"
    ]
    assert files[0]["language"] == "python"
    assert files[2]["file_type"] == "configuration"
    with pytest.raises(CodeExtractionError):
        extract_code_files("# ==================== ../../escape.py ====================\n")


def test_gmail_mcp_legacy_output_extracts_all_eight_files() -> None:
    file_contents = {
        ".env.example": "GMAIL_USER_EMAIL=example@gmail.com\n",
        "main.py": "from agent import run\n",
        "agent.py": "def run() -> None:\n    pass\n",
        "config.py": "MCP_SERVER_COMMAND = 'npx'\n",
        "gmail/client.py": "class GmailClient:\n    pass\n",
        "services/summarizer.py": "def summarize() -> str:\n    return ''\n",
        "requirements.txt": "httpx==0.27.2\n",
        "README.md": "# Gmail MCP\n",
    }
    content = "\n".join(
        f"# ==================== {filename} ====================\n{file_content}"
        for filename, file_content in file_contents.items()
    )

    files = extract_code_files(content)

    assert files is not None
    assert [file["filename"] for file in files] == list(file_contents)


def test_ambiguous_multiple_fences_fail_clearly() -> None:
    with pytest.raises(CodeExtractionError, match="without reliable file names"):
        extract_code_files("```python\nprint(1)\n```\n```python\nprint(2)\n```")


def test_legacy_multifile_markers_are_split() -> None:
    code = (
        "# ==================== main.py ====================\n"
        "print('main')\n"
        "# ==================== agent.py ====================\n"
        "print('agent')\n"
    )

    files = ValidatorService._normalize_files(code, None)

    assert files == {"main.py": "print('main')", "agent.py": "print('agent')"}


def test_file_markers_extract_structured_project() -> None:
    files = extract_code_files(
        "FILE: main.py\nprint('main')\n"
        "FILE: .env.example\nAPI_KEY=placeholder\n"
    )

    assert files is not None
    assert [file["filename"] for file in files] == ["main.py", ".env.example"]
    assert files[1]["language"] == "dotenv"


def test_single_python_assignment_is_not_misclassified_as_env() -> None:
    from app.services.code_extractor import looks_like_unparsed_configuration

    assert not looks_like_unparsed_configuration("value = 1\n")
    assert looks_like_unparsed_configuration("API_KEY=placeholder\n")


def test_ensemble_prefers_structured_manifest_over_largest_code_block() -> None:
    service = EnsembleService()
    content = (
        "Summary for the project\n\n"
        "```python main.py\nprint('main')\n```\n"
        "```python agent.py\ndef run():\n    return 'ok'\n```\n"
    )

    files = extract_code_files(content)
    code, reasoning = service._parse_response(content, files)

    assert files is not None
    assert code == "print('main')"
    assert "Summary for the project" in reasoning


@pytest.mark.asyncio
async def test_synthesis_derives_compatibility_code_from_structured_files() -> None:
    service = SynthesisService()
    output = ModelOutput(
        provider="gemini",
        model_name="test-model",
        code="",
        reasoning="generated project",
        confidence=0.85,
        estimated_complexity="medium",
        success=True,
        files=[
            CodeFile(filename="main.py", content="print('main')\n"),
            CodeFile(filename="README.md", content="# Project\n"),
        ],
    )

    result = await service.synthesize(
        [output],
        DebateResult(
            winner_provider="gemini",
            consensus_reached=True,
            synthesis_required=False,
        ),
    )

    assert result["files"] == output.files
    assert result["code"] == "print('main')\n"


@pytest.mark.asyncio
async def test_empty_generation_fails_validation() -> None:
    results = await ValidatorService().validate_all(
        code="",
        files=[{"filename": "<generated>.py", "content": ""}],
    )

    assert len(results) == 1
    assert results[0].stage == "generation"
    assert not results[0].passed
    assert results[0].errors == ["Generated project is empty"]


@pytest.mark.asyncio
async def test_synthesis_rejects_empty_structured_generation() -> None:
    task = SimpleNamespace(
        id=uuid4(),
        model_outputs=[
            ModelOutput(
                provider="gemini",
                model_name="test-model",
                code="",
                reasoning="",
                confidence=0.85,
                estimated_complexity="medium",
                success=True,
                files=[CodeFile(filename="main.py", content="")],
            ).model_dump()
        ],
        debate_result={
            "winner_provider": "gemini",
            "consensus_reached": True,
            "synthesis_required": False,
        },
        synthesized_code=None,
        synthesized_reasoning=None,
        known_limitations=None,
        code_files=None,
        status=None,
    )

    class SessionContext:
        async def __aenter__(self) -> "SessionContext":
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

        async def commit(self) -> None:
            return None

    orchestrator = object.__new__(OrchestratorService)
    orchestrator.synthesis = SynthesisService()
    orchestrator.session_maker = lambda: SessionContext()

    async def get_task(_session: object, _task_id: object) -> SimpleNamespace:
        return task

    orchestrator._get_task = get_task

    with pytest.raises(CodeExtractionError, match="no file content"):
        await orchestrator.synthesize_solution(task.id)

    assert task.status.name == "FAILED"


def test_status_response_exposes_structured_files() -> None:
    response = TaskStatusResponse(
        id=uuid4(),
        status="completed",
        user_query="generate a project",
        confirmation_status="confirmed",
        created_at="2026-09-04T00:00:00Z",
        updated_at="2026-09-04T00:00:00Z",
        code_files=[{"filename": "main.py", "content": "print('ok')\n"}],
    )

    assert response.code_files is not None
    assert response.code_files[0].content == "print('ok')\n"


@pytest.mark.asyncio
async def test_gmail_project_manifest_survives_generation_to_validation() -> None:
    file_contents = {
        ".env.example": "GMAIL_USER_EMAIL=example@gmail.com\n",
        "main.py": "from agent import run\n",
        "agent.py": "def run() -> None:\n    pass\n",
        "config.py": "MCP_SERVER_COMMAND = 'npx'\n",
        "gmail/client.py": "class GmailClient:\n    pass\n",
        "services/summarizer.py": "def summarize() -> str:\n    return ''\n",
        "requirements.txt": "httpx==0.27.2\n",
        "README.md": "# Gmail MCP\n",
    }
    response = "\n".join(
        f"# ==================== {filename} ====================\n{content}"
        for filename, content in file_contents.items()
    )

    ensemble = EnsembleService()

    async def captured_response(**_: object) -> dict[str, object]:
        return {"content": response, "model": "test-model", "latency_ms": 1}

    ensemble.router.execute_with_model = captured_response

    files = extract_code_files(response)
    code, _ = ensemble._parse_response(response, files)
    output = ensemble._generate_with_provider
    assert files is not None
    assert len(files) == 8
    assert code == file_contents["main.py"].strip()

    structured_output = await output(
        provider=ModelProvider.GROQ,
        messages=[],
        timeout_seconds=1,
    )
    task = SimpleNamespace(
        id=uuid4(),
        model_outputs=[structured_output.model_dump()],
        debate_result={
            "winner_provider": structured_output.provider,
            "consensus_reached": True,
            "synthesis_required": False,
        },
        synthesized_code=None,
        synthesized_reasoning=None,
        known_limitations=None,
        code_files=None,
        status=None,
        final_tests=None,
    )

    class SessionContext:
        async def __aenter__(self) -> "SessionContext":
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

        async def commit(self) -> None:
            return None

    orchestrator = object.__new__(OrchestratorService)
    orchestrator.synthesis = SynthesisService()
    orchestrator.session_maker = lambda: SessionContext()

    async def get_task(_session: object, _task_id: object) -> SimpleNamespace:
        return task

    orchestrator._get_task = get_task
    await orchestrator.synthesize_solution(task.id)

    captured: dict[str, object] = {}

    class ValidatorSpy:
        async def validate_all(self, **kwargs: object) -> list[object]:
            captured.update(kwargs)
            return []

        @staticmethod
        def all_passed(_results: list[object]) -> bool:
            return True

    orchestrator.validator = ValidatorSpy()
    await orchestrator.validate_code(task.id)

    manifest = task.code_files
    assert captured["files"] is manifest
    validation = await ValidatorService().validate_all(
        code=task.synthesized_code,
        files=manifest,
    )

    assert len(manifest) == 8
    assert [file["filename"] for file in manifest] == list(file_contents)
    assert manifest[0]["file_type"] == "configuration"
    assert all(result.passed for result in validation)
