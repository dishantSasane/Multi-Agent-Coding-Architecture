"""Ensemble Service - Parallel dispatch to multiple LLMs."""

import asyncio
import random
import re

import structlog

from app.config import get_settings
from app.core.exceptions import CodeForgeException
from app.models.models import CodeFile, ModelOutput
from app.services.model_router import ModelRouterService
from app.models.enums import ModelProvider
from app.services.code_extractor import extract_code_files

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
            # One call per provider that has a key, run in parallel (no fallback).
            # OpenRouter is pinned to its free router in PROVIDER_MODELS.
            keyed = self.settings.get_enabled_providers()
            providers = [
                p for p in (ModelProvider.GROQ, ModelProvider.OPENROUTER, ModelProvider.GEMINI)
                if p.value in keyed
            ][: max(1, self.ensemble_size)]

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
        if provider == ModelProvider.OPENROUTER:
            # Walking the free pool (retries + up to 4 models) needs more than 60s.
            timeout_seconds = max(timeout_seconds, 120)
        if provider != ModelProvider.GROQ:
            # Jitter so the free-tier gateways don't see three simultaneous requests.
            await asyncio.sleep(random.uniform(0, 1))
        try:
            result = await asyncio.wait_for(
                self.router.execute_with_model(
                    provider=provider,
                    messages=messages,
                    temperature=0.7,
                ),
                timeout=timeout_seconds,
            )

            # Parse the response to extract code and reasoning
            content = result["content"]
            files = extract_code_files(content)
            code, reasoning = self._parse_response(content, files)

            return ModelOutput(
                provider=provider.value,
                model_name=result["model"],
                code=code,
                reasoning=reasoning,
                confidence=0.85,  # Default confidence
                estimated_complexity="medium",
                latency_ms=result["latency_ms"],
                success=True,
                files=[CodeFile(**file) for file in files] if files else None,
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

    def _parse_response(
        self,
        content: str,
        files: list[dict[str, str]] | None = None,
    ) -> tuple[str, str]:
        """Parse model response to extract code and reasoning.

        Args:
            content: Raw model response.
            files: Optional structured project manifest, which is authoritative.

        Returns:
            Tuple of (code, reasoning).
        """
        reasoning = re.sub(r"```.*?```", "", content, flags=re.DOTALL).strip()

        if files:
            python_files = [file for file in files if file["filename"].endswith(".py")]
            entry_file = next(
                (file for file in python_files if file["filename"] == "main.py"),
                python_files[0] if python_files else files[0],
            )
            return entry_file["content"], reasoning

        # Look for code blocks
        code_blocks = re.findall(r"```(?:\w+)?\n(.*?)```", content, re.DOTALL)

        if code_blocks:
            # Take the largest code block
            code = max(code_blocks, key=len).strip()
        else:
            # No code blocks, assume entire content is code
            code = content.strip()

        if not code and not reasoning:
            reasoning = ""

        return code, reasoning
