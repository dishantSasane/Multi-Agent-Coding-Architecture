"""Task Decomposer Service - Break tasks into subtasks."""

import json
from typing import Any

import structlog
from litellm import acompletion

from app.core.exceptions import CodeForgeException
from app.models.models import IntentAnalysis

logger = structlog.get_logger(__name__)


class TaskDecomposerService:
    """Service for decomposing complex tasks into manageable subtasks."""

    def __init__(self) -> None:
        """Initialize task decomposer service."""
        self.prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        """Load the task decomposition prompt template."""
        return """You are an expert software architect. Break down the following coding task into discrete, executable subtasks.

Requirements:
- Each subtask should be independently testable
- Order subtasks logically (dependencies first)
- Estimate complexity for each subtask (low/medium/high)
- Include all necessary steps: setup, implementation, testing, documentation

Task Summary: {summary}
Tech Stack: {tech_stack}
Requirements: {requirements}
Constraints: {constraints}

Output JSON array of subtasks with format:
[
    {{
        "id": "task_1",
        "title": "Brief title",
        "description": "Detailed description",
        "complexity": "low|medium|high",
        "estimated_minutes": 30,
        "dependencies": [],
        "acceptance_criteria": ["criterion 1", "criterion 2"]
    }}
]

Output ONLY valid JSON array."""

    async def decompose_task(self, intent: IntentAnalysis) -> list[dict[str, Any]]:
        """Decompose a task into subtasks.

        Args:
            intent: Parsed intent analysis.

        Returns:
            List of subtask dictionaries.

        Raises:
            CodeForgeException: If decomposition fails.
        """
        logger.info("decomposing_task", task_type=intent.task_type)

        try:
            prompt = self.prompt_template.format(
                summary=intent.summary,
                tech_stack=", ".join(intent.tech_stack),
                requirements="\n".join(f"- {r}" for r in intent.requirements),
                constraints="\n".join(f"- {c}" for c in intent.constraints),
            )

            response = await acompletion(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0.3,
            )

            content = response.choices[0].message.content.strip()

            # Extract JSON from markdown
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()

            subtasks = json.loads(content)

            if not isinstance(subtasks, list):
                raise CodeForgeException(
                    "Invalid decomposition format",
                    {"received_type": type(subtasks).__name__},
                )

            # Validate and enrich subtasks
            validated_subtasks = []
            for i, task in enumerate(subtasks):
                validated_task = {
                    "id": task.get("id", f"task_{i + 1}"),
                    "title": task.get("title", f"Task {i + 1}"),
                    "description": task.get("description", ""),
                    "complexity": task.get("complexity", "medium"),
                    "estimated_minutes": task.get("estimated_minutes", 60),
                    "dependencies": task.get("dependencies", []),
                    "acceptance_criteria": task.get("acceptance_criteria", []),
                }
                validated_subtasks.append(validated_task)

            logger.info(
                "task_decomposed",
                subtask_count=len(validated_subtasks),
                total_estimated_minutes=sum(
                    t["estimated_minutes"] for t in validated_subtasks
                ),
            )

            return validated_subtasks

        except json.JSONDecodeError as e:
            logger.exception("decomposition_json_error", error=str(e))
            # Return a default single task
            return [
                {
                    "id": "task_1",
                    "title": "Implement solution",
                    "description": intent.summary,
                    "complexity": "medium",
                    "estimated_minutes": 120,
                    "dependencies": [],
                    "acceptance_criteria": intent.requirements,
                }
            ]
        except Exception as e:
            logger.exception("decomposition_failed", error=str(e))
            raise CodeForgeException(
                "Failed to decompose task",
                {"error": str(e)},
            )

    def get_execution_order(
        self, subtasks: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Sort subtasks by dependencies for execution order.

        Args:
            subtasks: List of subtasks.

        Returns:
            Sorted list of subtasks.
        """
        # Simple topological sort
        task_map = {t["id"]: t for t in subtasks}
        visited = set()
        result = []

        def visit(task_id: str) -> None:
            if task_id in visited:
                return
            visited.add(task_id)

            task = task_map.get(task_id)
            if task:
                for dep in task.get("dependencies", []):
                    visit(dep)
                result.append(task)

        for task in subtasks:
            visit(task["id"])

        return result
