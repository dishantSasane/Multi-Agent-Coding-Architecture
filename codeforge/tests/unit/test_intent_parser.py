"""Unit tests for intent parser."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import IntentParsingError
from app.services.intent_parser import IntentParser


class TestIntentParser:
    """Test intent parser service."""

    def test_init(self):
        """Test intent parser initialization."""
        parser = IntentParser()
        assert parser is not None

    @pytest.mark.asyncio
    async def test_analyze_simple_query(self, sample_query, sample_intent_analysis):
        """Test analysis of simple query."""
        parser = IntentParser()
        
        with patch.object(parser.llm_client, "completion") as mock_completion:
            mock_completion.return_value = json.dumps(sample_intent_analysis)
            
            result = await parser.analyze("test-task-id", sample_query)
            
            assert result.summary is not None
            assert result.confidence_score > 0.8

    @pytest.mark.asyncio
    async def test_analyze_complex_query(self):
        """Test analysis of complex query with context."""
        parser = IntentParser()
        
        complex_query = """
        Build a microservice with:
        - FastAPI backend
        - PostgreSQL database
        - Redis caching
        - JWT authentication
        - Rate limiting
        - Request logging
        - Health check endpoints
        """
        
        with patch.object(parser.llm_client, "completion") as mock_completion:
            mock_completion.return_value = json.dumps({
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
            })
            
            result = await parser.analyze("test-task-id", complex_query)
            
            assert len(result.tech_stack) >= 4
            assert len(result.requirements) >= 6

    @pytest.mark.asyncio
    async def test_low_confidence_generates_questions(self):
        """Test that low confidence generates clarifying questions."""
        parser = IntentParser()
        
        vague_query = "Build something cool"
        
        with patch.object(parser.llm_client, "completion") as mock_completion:
            mock_completion.return_value = json.dumps({
                "summary": "User wants to build an application",
                "tech_stack": [],
                "requirements": [],
                "constraints": [],
                "edge_cases": [],
                "security_concerns": [],
                "clarifying_questions": [
                    "What type of application do you want to build?",
                    "What programming language do you prefer?",
                    "What functionality should it have?",
                ],
                "confidence_score": 0.4,
            })
            
            result = await parser.analyze("test-task-id", vague_query)
            
            assert result.confidence_score < 0.8
            assert len(result.clarifying_questions) > 0

    @pytest.mark.asyncio
    async def test_security_aware_analysis(self):
        """Test that parser identifies security concerns."""
        parser = IntentParser()
        
        security_query = "Create a login system with password storage"
        
        with patch.object(parser.llm_client, "completion") as mock_completion:
            mock_completion.return_value = json.dumps({
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
            })
            
            result = await parser.analyze("test-task-id", security_query)
            
            assert len(result.security_concerns) >= 3

    @pytest.mark.asyncio
    async def test_malformed_llm_response(self):
        """Test handling of malformed LLM response."""
        parser = IntentParser()
        
        with patch.object(parser.llm_client, "completion") as mock_completion:
            mock_completion.return_value = "not valid json"
            
            with pytest.raises(IntentParsingError):
                await parser.analyze("test-task-id", "test query")

    @pytest.mark.asyncio
    async def test_empty_query_handling(self):
        """Test handling of empty query."""
        parser = IntentParser()
        
        with patch.object(parser.llm_client, "completion") as mock_completion:
            mock_completion.return_value = json.dumps({
                "summary": "",
                "tech_stack": [],
                "requirements": [],
                "constraints": [],
                "edge_cases": [],
                "security_concerns": [],
                "clarifying_questions": ["What would you like to build?"],
                "confidence_score": 0.1,
            })
            
            result = await parser.analyze("test-task-id", "")
            
            assert result.confidence_score < 0.5
            assert len(result.clarifying_questions) > 0

    @pytest.mark.asyncio
    async def test_tech_stack_extraction(self):
        """Test extraction of tech stack from query."""
        parser = IntentParser()
        
        tech_query = "Build a React frontend with Node.js backend and MongoDB database"
        
        with patch.object(parser.llm_client, "completion") as mock_completion:
            mock_completion.return_value = json.dumps({
                "summary": "Full-stack web application",
                "tech_stack": ["React", "Node.js", "MongoDB"],
                "requirements": [],
                "constraints": [],
                "edge_cases": [],
                "security_concerns": [],
                "clarifying_questions": [],
                "confidence_score": 0.95,
            })
            
            result = await parser.analyze("test-task-id", tech_query)
            
            assert "React" in result.tech_stack
            assert "Node.js" in result.tech_stack
            assert "MongoDB" in result.tech_stack

    @pytest.mark.asyncio
    async def test_edge_case_identification(self):
        """Test identification of edge cases."""
        parser = IntentParser()
        
        data_query = "Process CSV files and convert to JSON"
        
        with patch.object(parser.llm_client, "completion") as mock_completion:
            mock_completion.return_value = json.dumps({
                "summary": "CSV to JSON converter",
                "tech_stack": ["Python"],
                "requirements": ["Read CSV", "Write JSON"],
                "constraints": [],
                "edge_cases": [
                    "Empty CSV files",
                    "Malformed CSV data",
                    "Very large files",
                    "Special characters in data",
                    "Missing columns",
                ],
                "security_concerns": [],
                "clarifying_questions": [],
                "confidence_score": 0.88,
            })
            
            result = await parser.analyze("test-task-id", data_query)
            
            assert len(result.edge_cases) >= 3
