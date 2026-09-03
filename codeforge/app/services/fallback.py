"""Fallback Service - Multiple fallback strategies."""

import asyncio
from typing import Any, Callable

import structlog

from app.core.exceptions import CodeForgeException
from app.models.enums import ModelProvider
from app.services.model_router import ModelRouterService

logger = structlog.get_logger(__name__)


class FallbackService:
    """Service for implementing fallback strategies."""

    def __init__(self) -> None:
        """Initialize fallback service."""
        self.router = ModelRouterService()

    async def try_with_fallback(
        self,
        primary_func: Callable,
        fallback_funcs: list[Callable],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Try a function with fallback alternatives.

        Args:
            primary_func: Primary function to try.
            fallback_funcs: List of fallback functions.
            args: Arguments to pass to functions.
            kwargs: Keyword arguments to pass.

        Returns:
            Result from first successful function.

        Raises:
            CodeForgeException: If all functions fail.
        """
        all_funcs = [primary_func] + fallback_funcs
        last_error = None

        for i, func in enumerate(all_funcs):
            try:
                logger.info("trying_function", attempt=i + 1, total=len(all_funcs))
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                logger.warning(
                    "function_failed",
                    attempt=i + 1,
                    error=str(e),
                )
                continue

        logger.error("all_fallbacks_exhausted")
        raise CodeForgeException(
            "All fallback strategies failed",
            {"last_error": str(last_error)},
        )

    async def model_fallback(
        self,
        messages: list[dict[str, str]],
        preferred_provider: ModelProvider | None = None,
    ) -> dict[str, Any]:
        """Try models with fallback chain.

        Args:
            messages: Messages for the LLM.
            preferred_provider: Preferred provider to start with.

        Returns:
            Model response dictionary.
        """
        # Get fallback chain
        if preferred_provider:
            providers = [preferred_provider] + self.router.get_fallback_chain(
                preferred_provider
            )
        else:
            providers = list(ModelProvider)

        logger.info("model_fallback_chain", providers=[p.value for p in providers])

        last_error = None
        for provider in providers:
            try:
                return await self.router.execute_with_model(
                    provider=provider,
                    messages=messages,
                )
            except Exception as e:
                last_error = e
                logger.warning("provider_failed", provider=provider.value, error=str(e))
                continue

        raise CodeForgeException(
            "All model providers failed",
            {"last_error": str(last_error)},
        )

    async def strategy_fallback(
        self,
        ensemble_func: Callable,
        single_model_func: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Fallback from ensemble to single model.

        Args:
            ensemble_func: Ensemble generation function.
            single_model_func: Single model function.
            args: Arguments to pass.
            kwargs: Keyword arguments.

        Returns:
            Generation result.
        """
        try:
            return await ensemble_func(*args, **kwargs)
        except Exception as e:
            logger.warning("ensemble_failed_falling_back", error=str(e))
            return await single_model_func(*args, **kwargs)

    async def sandbox_fallback(
        self,
        code: str,
        docker_execute_func: Callable,
        subprocess_execute_func: Callable | None = None,
    ) -> dict[str, Any]:
        """Fallback from Docker to subprocess execution.

        Args:
            code: Code to execute.
            docker_execute_func: Docker execution function.
            subprocess_execute_func: Optional subprocess function.

        Returns:
            Execution results.
        """
        try:
            return await docker_execute_func(code)
        except Exception as e:
            logger.warning("docker_failed_falling_back", error=str(e))

            if subprocess_execute_func:
                return await subprocess_execute_func(code)

            # Return synthetic failure result
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Docker execution failed: {str(e)}",
                "error_message": str(e),
            }

    async def validation_fallback(
        self,
        strict_validation_func: Callable,
        relaxed_validation_func: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> tuple[Any, bool]:
        """Fallback from strict to relaxed validation.

        Args:
            strict_validation_func: Strict validation function.
            relaxed_validation_func: Relaxed validation function.
            args: Arguments to pass.
            kwargs: Keyword arguments.

        Returns:
            Tuple of (validation_result, used_relaxed).
        """
        try:
            result = await strict_validation_func(*args, **kwargs)
            return result, False
        except Exception as e:
            logger.warning("strict_validation_failed", error=str(e))
            result = await relaxed_validation_func(*args, **kwargs)
            return result, True

    async def circuit_breaker_fallback(
        self,
        provider: ModelProvider,
        messages: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Handle circuit breaker open scenario.

        Args:
            provider: Original provider.
            messages: Messages for LLM.

        Returns:
            Model response from alternative provider.
        """
        # Check if circuit is open
        if not await self.router.circuit_breaker.can_execute(provider.value):
            logger.warning("circuit_breaker_open", provider=provider.value)

            # Try fallback providers
            return await self.model_fallback(messages, preferred_provider=None)

        # Circuit is closed, use preferred provider
        return await self.router.execute_with_model(
            provider=provider,
            messages=messages,
        )
