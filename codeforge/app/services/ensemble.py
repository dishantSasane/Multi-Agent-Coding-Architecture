"""Ensemble Service - Parallel dispatch to multiple LLMs."""

import asyncio
from typing import Any

import structlog

from app.config import get_settings
from app.core.exceptions import CodeForgeException
from app.models.models import ModelOutput
from app.services.model_router import ModelRouterService
from app.models.enums import ModelProvider

logger = structlog.get_logger(__name__)


class EnsembleService:
    """Service for dispatching tasks to multiple models in parallel."""

    def __init__(self) -> None:
        """Initialize ensemble service."""
        self.settings = get_settings()
        self.router = ModelRouterService()
        self.ensemble_size = self.settings.default_ensemble_size

    async def generate_ensemble(
        self,
        prompt: str,
        system_prompt: str | None = None,
        providers: list[ModelProvider] | None = None,
        timeout_seconds: int = 60,
    ) -> list[ModelOutput]:
        """Generate code from multiple models in parallel.

        Args:
            prompt: The code generation prompt.
            system_prompt: Optional system prompt.
            providers: List of providers to use. Defaults to top N.
            timeout_seconds: Timeout for each model.

        Returns:
            List of ModelOutput objects from each provider.
        """
        logger.info("generating_ensemble", size=self.ensemble_size)

        if providers is None:
            # Use top providers by priority
            providers = list(ModelProvider)[: self.ensemble_size]

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Create tasks for parallel execution
        tasks = [
            self._generate_with_provider(provider, messages, timeout_seconds)
            for provider in providers
        ]

        # Execute in parallel with graceful degradation
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter successful results
        outputs = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(
                    "ensemble_member_failed",
                    provider=providers[i].value,
                    error=str(result),
                )
            elif isinstance(result, ModelOutput):
                outputs.append(result)

        logger.info("ensemble_complete", successful_count=len(outputs))
        return outputs

    async def _generate_with_provider(
        self,
        provider: ModelProvider,
        messages: list[dict[str, str]],
        timeout_seconds: int,
    ) -> ModelOutput:
        """Generate output from a single provider.

        Args:
            provider: The provider to use.
            messages: Message list for the API.
            timeout_seconds: Request timeout.

        Returns:
            ModelOutput object.
        """
        try:
            result = await asyncio.wait_for(
                self.router.execute_with_model(
                    provider=provider,
                    messages=messages,
                    max_tokens=4000,
                    temperature=0.7,
                ),
                timeout=timeout_seconds,
            )

            # Parse the response to extract code and reasoning
            content = result["content"]
            code, reasoning = self._parse_response(content)

            return ModelOutput(
                provider=provider.value,
                model_name=result["model"],
                code=code,
                reasoning=reasoning,
                confidence=0.85,  # Default confidence
                estimated_complexity="medium",
                latency_ms=result["latency_ms"],
                success=True,
            )

        except asyncio.TimeoutError:
            logger.warning("model_timeout", provider=provider.value)
            raise CodeForgeException(
                f"Model {provider.value} timed out",
                {"timeout": timeout_seconds},
            )
        except Exception as e:
            logger.exception("model_generation_failed", provider=provider.value, error=str(e))
            raise

    def _parse_response(self, content: str) -> tuple[str, str]:
        """Parse model response to extract code and reasoning.

        Args:
            content: Raw model response.

        Returns:
            Tuple of (code, reasoning).
        """
        # Look for code blocks
        import re

        code_blocks = re.findall(r"```(?:\w+)?\n(.*?)```", content, re.DOTALL)

        if code_blocks:
            # Take the largest code block
            code = max(code_blocks, key=len).strip()
            # Reasoning is everything outside code blocks
            reasoning = re.sub(r"```.*?```", "", content, flags=re.DOTALL).strip()
        else:
            # No code blocks, assume entire content is code
            code = content.strip()
            reasoning = ""

        return code, reasoning

    def vote_on_outputs(self, outputs: list[ModelOutput]) -> ModelOutput | None:
        """Select best output using simple voting.

        Args:
            outputs: List of model outputs.

        Returns:
            Best output or None if no outputs.
        """
        if not outputs:
            return None

        if len(outputs) == 1:
            return outputs[0]

        # Simple scoring: prefer longer, more complete solutions
        scored = []
        for output in outputs:
            score = len(output.code) * 0.5 + output.confidence * 100
            scored.append((score, output))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]
