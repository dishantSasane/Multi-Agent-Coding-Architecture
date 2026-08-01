"""Intent Parser Service - Parse and clarify user intent."""

import json
from typing import Any

import structlog
from litellm import acompletion

from app.config import get_settings
from app.core.exceptions import IntentParsingError
from app.models.models import IntentAnalysis

logger = structlog.get_logger(__name__)


class IntentParserService:
    """Service for parsing user intent from coding queries."""

    def __init__(self) -> None:
        """Initialize intent parser service."""
        self.settings = get_settings()
        self.prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        """Load the intent analysis prompt template."""
        try:
            with open("app/prompts/intent_analysis.txt", "r") as f:
                return f.read()
        except FileNotFoundError:
            # Fallback inline template
            return """You are an expert software requirements analyst. Analyze the user's coding request.
Extract structured information. If unclear, ask clarifying questions.
Be concise. Output valid JSON matching the IntentAnalysis schema.

Schema:
{
    "summary": "Brief summary of the request",
    "tech_stack": ["list", "of", "technologies"],
    "requirements": ["list", "of", "requirements"],
    "constraints": ["list", "of", "constraints"],
    "edge_cases": ["list", "of", "edge cases to handle"],
    "security_concerns": ["list", "of", "security considerations"],
    "clarifying_questions": ["list", "of", "questions if confidence < 0.8"],
    "confidence_score": 0.0-1.0,
    "task_type": "architecture|implementation|algorithm|documentation|analysis|debugging|testing"
}

User Query: {query}
Context: {context}

Output ONLY valid JSON, no markdown or explanations."""

    async def parse_intent(
        self,
        query: str,
        context: dict[str, Any] | None = None,
    ) -> IntentAnalysis:
        """Parse user intent from a coding query.

        Args:
            query: The user's coding query.
            context: Optional additional context.

        Returns:
            IntentAnalysis object with parsed information.

        Raises:
            IntentParsingError: If parsing fails.
        """
        logger.info("parsing_intent", query_length=len(query))

        try:
            # Prepare the prompt
            prompt = self.prompt_template.format(
                query=query,
                context=json.dumps(context or {}),
            )

            # Call LLM
            response = await acompletion(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.3,
            )

            # Parse response
            content = response.choices[0].message.content.strip()

            # Extract JSON from response (handle markdown code blocks)
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()

            # Parse JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error("failed_to_parse_json", error=str(e), content=content[:500])
                raise IntentParsingError(
                    "Failed to parse intent analysis JSON",
                    {"parse_error": str(e)},
                )

            # Create IntentAnalysis object
            intent = IntentAnalysis(
                summary=data.get("summary", ""),
                tech_stack=data.get("tech_stack", []),
                requirements=data.get("requirements", []),
                constraints=data.get("constraints", []),
                edge_cases=data.get("edge_cases", []),
                security_concerns=data.get("security_concerns", []),
                clarifying_questions=data.get("clarifying_questions", []),
                confidence_score=float(data.get("confidence_score", 0.5)),
                task_type=data.get("task_type", "implementation"),
            )

            logger.info(
                "intent_parsed",
                confidence=intent.confidence_score,
                task_type=intent.task_type,
                questions_count=len(intent.clarifying_questions),
            )

            return intent

        except IntentParsingError:
            raise
        except Exception as e:
            logger.exception("intent_parsing_failed", error=str(e))
            raise IntentParsingError(
                "Failed to parse user intent",
                {"error": str(e), "error_type": type(e).__name__},
            )

    def needs_clarification(self, intent: IntentAnalysis) -> bool:
        """Check if intent requires user clarification.

        Args:
            intent: Parsed intent analysis.

        Returns:
            True if clarification is needed.
        """
        return intent.confidence_score < 0.8 or len(intent.clarifying_questions) > 0

    def get_summary(self, intent: IntentAnalysis) -> str:
        """Generate a human-readable summary of the intent.

        Args:
            intent: Parsed intent analysis.

        Returns:
            Summary string for user confirmation.
        """
        lines = [
            f"**Summary:** {intent.summary}",
            f"**Task Type:** {intent.task_type}",
            f"**Tech Stack:** {', '.join(intent.tech_stack) or 'Not specified'}",
            f"**Requirements:** {len(intent.requirements)} identified",
            f"**Edge Cases:** {len(intent.edge_cases)} identified",
            f"**Security Concerns:** {len(intent.security_concerns)} identified",
        ]

        if intent.clarifying_questions:
            lines.append("\n**Clarifying Questions:**")
            for i, q in enumerate(intent.clarifying_questions, 1):
                lines.append(f"{i}. {q}")

        return "\n".join(lines)
