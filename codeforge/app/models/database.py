"""Database configuration and session management."""

from collections.abc import AsyncGenerator
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


# Global engine and session factory
_engine: Any = None
_async_session_maker: async_sessionmaker[AsyncSession] | None = None


def _build_engine_url_and_args(raw_url: str) -> tuple[str, dict[str, Any]]:
    """Strip libpq-style query params that asyncpg doesn't accept.

    asyncpg uses connect_args={'ssl': True} instead of ?sslmode=require.
    channel_binding is also unsupported and must be removed.
    """
    parsed = urlparse(raw_url)
    params = parse_qs(parsed.query, keep_blank_values=True)

    sslmode = params.pop("sslmode", [None])[0]
    params.pop("channel_binding", None)

    new_query = urlencode({k: v[0] for k, v in params.items()})
    clean_url = urlunparse(parsed._replace(query=new_query))

    connect_args: dict[str, Any] = {}
    if sslmode in ("require", "verify-ca", "verify-full"):
        connect_args["ssl"] = True
    elif sslmode == "disable":
        connect_args["ssl"] = False

    return clean_url, connect_args


def get_engine() -> Any:
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        clean_url, connect_args = _build_engine_url_and_args(str(settings.database_url))
        _engine = create_async_engine(
            clean_url,
            echo=False,
            pool_size=20,
            max_overflow=40,
            pool_pre_ping=True,
            pool_recycle=3600,
            connect_args=connect_args,
        )
    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Get or create the session maker."""
    global _async_session_maker
    if _async_session_maker is None:
        _async_session_maker = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _async_session_maker


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to get database session."""
    session = get_session_maker()()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


# Alias used by endpoints that call: async with AsyncSessionLocal() as session.
# Calling AsyncSessionLocal() returns an AsyncSession (which IS an async context
# manager), so the pattern works correctly.
AsyncSessionLocal = lambda: get_session_maker()()

# Alias used by deps.py: async for session in get_session()
get_session = get_db_session


async def init_db() -> None:
    """Initialize database tables and run lightweight column migrations."""
    from sqlalchemy import text

    from app.models.orm_models import ModelCall, Task  # noqa: F401

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Add code_files column if it doesn't exist (idempotent migration).
        # ADD COLUMN IF NOT EXISTS is safe to run on every startup in PostgreSQL.
        try:
            await conn.execute(
                text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS code_files JSONB")
            )
        except Exception:
            pass  # column already exists or DB doesn't support IF NOT EXISTS


async def close_db() -> None:
    """Close database connections."""
    global _engine, _async_session_maker
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _async_session_maker = None
