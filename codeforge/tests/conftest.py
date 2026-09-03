"""Pytest configuration and fixtures."""

import asyncio
import os
import uuid
from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.main import app
from app.models.database import Base, get_session


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create test database engine."""
    test_db_url = "postgresql+asyncpg://codeforge:codeforge_password@localhost:5432/codeforge_test"
    
    engine = create_async_engine(
        test_db_url,
        echo=False,
        pool_pre_ping=True,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client."""
    async def override_get_session():
        yield db_session
    
    app.dependency_overrides[get_session] = override_get_session
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_task_id() -> str:
    """Generate a sample task ID."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_query() -> str:
    """Sample coding query for tests."""
    return "Create a FastAPI endpoint that returns hello world"


@pytest.fixture
def sample_intent_analysis() -> dict[str, Any]:
    """Sample intent analysis result."""
    return {
        "summary": "Create a simple FastAPI hello world endpoint",
        "tech_stack": ["FastAPI", "Python"],
        "requirements": ["Return hello world response"],
        "constraints": [],
        "edge_cases": [],
        "security_concerns": [],
        "clarifying_questions": [],
        "confidence_score": 0.95,
    }


@pytest.fixture
def sample_model_output() -> dict[str, Any]:
    """Sample model output for tests."""
    return {
        "model_name": "gpt-4o",
        "provider": "openai",
        "code": 'print("Hello, World!")',
        "reasoning": "Simple hello world implementation",
        "confidence": 0.99,
        "estimated_complexity": "low",
        "latency_ms": 1500,
        "success": True,
    }


@pytest.fixture
def mock_llm_response() -> dict[str, Any]:
    """Mock LLM API response."""
    return {
        "choices": [
            {
                "message": {
                    "content": '{"summary": "Test", "confidence_score": 0.9}'
                }
            }
        ],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        },
    }


@pytest.fixture
def sandbox_code() -> str:
    """Sample code for sandbox testing."""
    return """
def add(a: int, b: int) -> int:
    '''Add two numbers.'''
    return a + b

if __name__ == "__main__":
    print(add(2, 3))
"""


@pytest.fixture
def malicious_code() -> str:
    """Malicious code for security testing."""
    return """
import os
os.system('rm -rf /')
"""


@pytest.fixture
def invalid_code() -> str:
    """Invalid code for syntax testing."""
    return """
def broken(
    # Missing closing paren and function body
"""
