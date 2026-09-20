"""Unit tests for IntentParserService (app/services/intent_parser.py)."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import IntentParsingError
from app.services.intent_parser import IntentParserService


def _llm_response(content: str) -> SimpleNamespace:
    """Build a fake litellm acompletion response shape."""
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def _make_parser() -> IntentParserService:
    parser = IntentParserService()
    parser.redis.get = AsyncMock(side_effect=RuntimeError("no redis in tests"))
    parser.redis.setex = AsyncMock(side_effect=RuntimeError("no redis in tests"))
    return parser


class TestIntentParserService:
    """Test intent parser service."""

    def test_init(self):
        parser = _make_parser()
        assert parser is not None
        assert parser.prompt_template

    @pytest.mark.asyncio
    async def test_parse_intent_simple_query(self, sample_query, sample_intent_analysis):
        parser = _make_parser()

        with patch(
            "app.services.intent_parser.acompletion",
            AsyncMock(return_value=_llm_response(json.dumps(sample_intent_analysis))),
        ):
            result = await parser.parse_intent(sample_query)

            assert result.summary
            assert result.confidence_score > 0.8

    @pytest.mark.asyncio
    async def test_parse_intent_complex_query(self):
        parser = _make_parser()
        complex_query = (
            "Build a microservice with FastAPI, PostgreSQL, Redis caching, "
            "JWT authentication, rate limiting, request logging, health checks."
        )
        payload = {
            "summary": "Build a complete FastAPI microservice",
            "tech_stack": ["FastAPI", "PostgreSQL", "Redis", "JWT"],
            "requirements": [
                "REST API endpoints",
                "Database integration",
                "Authentication system",
                "Rate limiting",
                "Logging",
                "Health checks",
            ],
            "constraints": ["Must be production-ready"],
            "edge_cases": ["Handle database connection failures"],
            "security_concerns": ["SQL injection", "JWT token security"],
            "clarifying_questions": [],
            "confidence_score": 0.85,
        }

        with patch(
            "app.services.intent_parser.acompletion",
            AsyncMock(return_value=_llm_response(json.dumps(payload))),
        ):
            result = await parser.parse_intent(complex_query)

            assert len(result.tech_stack) >= 4
            assert len(result.requirements) >= 6

    @pytest.mark.asyncio
    async def test_low_confidence_needs_clarification(self):
        parser = _make_parser()
        payload = {
            "summary": "User wants to build an application",
            "tech_stack": [],
            "requirements": [],
            "constraints": [],
            "edge_cases": [],
            "security_concerns": [],
            "clarifying_questions": [
                "What type of application do you want to build?",
                "What programming language do you prefer?",
            ],
            "confidence_score": 0.4,
        }

        with patch(
            "app.services.intent_parser.acompletion",
            AsyncMock(return_value=_llm_response(json.dumps(payload))),
        ):
            result = await parser.parse_intent("Build something cool")

            assert result.confidence_score < 0.8
            assert parser.needs_clarification(result) is True

    @pytest.mark.asyncio
    async def test_security_aware_analysis(self):
        parser = _make_parser()
        payload = {
            "summary": "User authentication system",
            "tech_stack": ["Python", "bcrypt"],
            "requirements": ["Password hashing", "User verification"],
            "constraints": [],
            "edge_cases": ["Invalid credentials", "Account lockout"],
            "security_concerns": [
                "Password hashing algorithm",
                "SQL injection prevention",
                "Session management",
                "Brute force protection",
            ],
            "clarifying_questions": [],
            "confidence_score": 0.9,
        }

        with patch(
            "app.services.intent_parser.acompletion",
            AsyncMock(return_value=_llm_response(json.dumps(payload))),
        ):
            result = await parser.parse_intent("Create a login system with password storage")

            assert len(result.security_concerns) >= 3

    @pytest.mark.asyncio
    async def test_malformed_llm_response_raises(self):
        parser = _make_parser()

        with patch(
            "app.services.intent_parser.acompletion",
            AsyncMock(return_value=_llm_response("not valid json")),
        ):
            with pytest.raises(IntentParsingError):
                await parser.parse_intent("test query")

    @pytest.mark.asyncio
    async def test_tech_stack_extraction(self):
        parser = _make_parser()
        payload = {
            "summary": "Full-stack web application",
            "tech_stack": ["React", "Node.js", "MongoDB"],
            "requirements": [],
            "constraints": [],
            "edge_cases": [],
            "security_concerns": [],
            "clarifying_questions": [],
            "confidence_score": 0.95,
        }

        with patch(
            "app.services.intent_parser.acompletion",
            AsyncMock(return_value=_llm_response(json.dumps(payload))),
        ):
            result = await parser.parse_intent(
                "Build a React frontend with Node.js backend and MongoDB database"
            )

            assert {"React", "Node.js", "MongoDB"}.issubset(set(result.tech_stack))

    @pytest.mark.asyncio
    async def test_cache_hit_skips_llm_call(self, sample_intent_analysis):
        parser = _make_parser()
        cached_payload = {**sample_intent_analysis, "task_type": "implementation"}
        parser.redis.get = AsyncMock(return_value=json.dumps(cached_payload))

        with patch(
            "app.services.intent_parser.acompletion", AsyncMock()
        ) as mock_llm:
            result = await parser.parse_intent("Create a FastAPI endpoint that returns hello world")

            mock_llm.assert_not_called()
            assert result.summary == sample_intent_analysis["summary"]


if __name__ == "__main__":
    import asyncio

    async def demo() -> None:
        parser = _make_parser()
        payload = {
            "summary": "demo",
            "tech_stack": [],
            "requirements": [],
            "constraints": [],
            "edge_cases": [],
            "security_concerns": [],
            "clarifying_questions": [],
            "confidence_score": 0.9,
        }
        with patch(
            "app.services.intent_parser.acompletion",
            AsyncMock(return_value=_llm_response(json.dumps(payload))),
        ):
            result = await parser.parse_intent("demo query")
            assert result.summary == "demo"
        print("self-check passed")

    asyncio.run(demo())
