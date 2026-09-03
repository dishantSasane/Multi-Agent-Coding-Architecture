"""Debate Engine Service - Adversarial review between models."""

import asyncio
from typing import Any

import structlog
from litellm import acompletion

from app.models.models import DebateResult, ModelOutput
from app.services.model_router import ModelRouterService
from app.models.enums import ModelProvider

logger = structlog.get_logger(__name__)


class DebateEngineService:
    """Service for adversarial code review between models."""

    def __init__(self) -> None:
        """Initialize debate engine service."""
        self.router = ModelRouterService()
        self.debate_prompt = self._load_debate_prompt()

    def _load_debate_prompt(self) -> str:
        """Load the debate prompt template."""
        return """You are a senior code reviewer conducting an adversarial review.

Review the following code critically:

```python
{code}
```

Evaluate on these dimensions (score 1-10):
- Correctness: Does it work correctly?
- Security: Are there vulnerabilities?
- Performance: Is it efficient?
- Maintainability: Is it well-structured?

Identify specific issues:
- Bugs or logical errors
- Security vulnerabilities
- Missing edge cases
- Performance problems
- Style/maintainability issues

Output JSON:
{{
    "scores": {{
        "correctness": 8,
        "security": 7,
        "performance": 8,
        "maintainability": 9
    }},
    "issues": ["issue 1", "issue 2"],
    "recommendations": ["recommendation 1", "recommendation 2"],
    "overall_assessment": "brief summary"
}}

Be specific and actionable. Output ONLY valid JSON."""

    async def run_debate(
        self,
        outputs: list[ModelOutput],
        num_reviewers: int = 2,
    ) -> DebateResult:
        """Run adversarial debate on model outputs.

        Args:
            outputs: List of model outputs to debate.
            num_reviewers: Number of models to use as reviewers.

        Returns:
            DebateResult with scores and critiques.
        """
        logger.info("running_debate", output_count=len(outputs))

        if len(outputs) < 1:
            return DebateResult(
                winner_provider="none",
                scores={},
                critiques=[],
                consensus_reached=False,
                synthesis_required=True,
            )

        # Select top 2 outputs for debate
        candidates = outputs[:min(len(outputs), 2)]

        # Run reviews in parallel
        review_tasks = [
            self._review_solution(candidate.code, candidate.provider)
            for candidate in candidates
        ]

        reviews = await asyncio.gather(*review_tasks, return_exceptions=True)

        # Process reviews
        all_scores: dict[str, dict[str, float]] = {}
        all_critiques: list[str] = []

        for i, review in enumerate(reviews):
            if isinstance(review, Exception):
                logger.warning("review_failed", error=str(review))
                continue

            provider = candidates[i].provider if i < len(candidates) else "unknown"
            all_scores[provider] = review.get("scores", {})

            critique = f"**{provider}'s solution:**\n"
            critique += f"Assessment: {review.get('overall_assessment', 'N/A')}\n"
            critique += f"Issues: {', '.join(review.get('issues', [])[:5])}\n"
            all_critiques.append(critique)

        # Determine winner based on average scores
        winner = self._determine_winner(all_scores)

        # Check for consensus (all scores within 2 points)
        consensus = self._check_consensus(all_scores)

        logger.info(
            "debate_complete",
            winner=winner,
            consensus=consensus,
        )

        return DebateResult(
            winner_provider=winner,
            scores=all_scores,
            critiques=all_critiques,
            consensus_reached=consensus,
            synthesis_required=not consensus,
        )

    async def _review_solution(
        self,
        code: str,
        provider: str,
    ) -> dict[str, Any]:
        """Review a single solution.

        Args:
            code: Code to review.
            provider: Provider that generated the code.

        Returns:
            Review results dictionary.
        """
        prompt = self.debate_prompt.format(code=code)

        try:
            result = await self.router.execute_with_model(
                provider=ModelProvider.ANTHROPIC,  # Use Claude for reviewing
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
                temperature=0.3,
            )

            content = result["content"]

            # Parse JSON from response
            import json
            import re

            json_match = re.search(r"\{.*?\}", content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())

            return {
                "scores": {"correctness": 5, "security": 5, "performance": 5, "maintainability": 5},
                "issues": ["Could not parse review"],
                "recommendations": [],
                "overall_assessment": "Review parsing failed",
            }

        except Exception as e:
            logger.exception("review_error", provider=provider, error=str(e))
            return {
                "scores": {"correctness": 5, "security": 5, "performance": 5, "maintainability": 5},
                "issues": [f"Review failed: {str(e)}"],
                "recommendations": [],
                "overall_assessment": "Review error",
            }

    def _determine_winner(self, scores: dict[str, dict[str, float]]) -> str:
        """Determine the winning solution based on scores.

        Args:
            scores: Scores per provider.

        Returns:
            Winner provider name.
        """
        if not scores:
            return "none"

        best_score = -1
        winner = "none"

        for provider, provider_scores in scores.items():
            avg_score = sum(provider_scores.values()) / max(1, len(provider_scores))
            if avg_score > best_score:
                best_score = avg_score
                winner = provider

        return winner

    def _check_consensus(self, scores: dict[str, dict[str, float]]) -> bool:
        """Check if reviewers reached consensus.

        Args:
            scores: Scores per provider.

        Returns:
            True if consensus reached.
        """
        if len(scores) < 2:
            return True

        # Check if all average scores are within 2 points
        averages = []
        for provider_scores in scores.values():
            avg = sum(provider_scores.values()) / max(1, len(provider_scores))
            averages.append(avg)

        if not averages:
            return True

        return max(averages) - min(averages) <= 2.0
