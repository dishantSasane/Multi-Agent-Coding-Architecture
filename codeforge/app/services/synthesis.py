"""Synthesis Service - Merge multiple solutions into one."""

import re
from typing import Any

import structlog

from app.models.models import DebateResult, ModelOutput

logger = structlog.get_logger(__name__)


class SynthesisService:
    """Service for synthesizing best parts from multiple solutions."""

    def __init__(self) -> None:
        """Initialize synthesis service."""
        pass

    async def synthesize(
        self,
        outputs: list[ModelOutput],
        debate_result: DebateResult,
    ) -> dict[str, Any]:
        """Synthesize final solution from multiple outputs.

        Args:
            outputs: List of model outputs.
            debate_result: Results from the debate engine.

        Returns:
            Dictionary with synthesized code and metadata.
        """
        logger.info("synthesizing_solution", output_count=len(outputs))

        if not outputs:
            return {
                "code": "",
                "reasoning": "No outputs available for synthesis",
                "known_limitations": [],
            }

        # If we have a clear winner, use their solution
        if debate_result.winner_provider and debate_result.consensus_reached:
            winner_output = next(
                (o for o in outputs if o.provider == debate_result.winner_provider),
                None,
            )
            if winner_output:
                logger.info("using_winner_solution", provider=debate_result.winner_provider)
                compatibility_code = self._compatibility_code(winner_output.files)
                return {
                    "code": compatibility_code or winner_output.code,
                    "files": winner_output.files,
                    "reasoning": winner_output.reasoning,
                    "known_limitations": self._extract_limitations(
                        compatibility_code or winner_output.code
                    ),
                }

        # Keep a complete structured project intact when no consensus winner
        # exists; merging source strings would discard file boundaries.
        structured_outputs = [output for output in outputs if output.files]
        if structured_outputs:
            selected = max(
                structured_outputs,
                key=lambda output: (
                    len(output.files),
                    sum(len(file.content) for file in output.files),
                    len(output.code or ""),
                ),
            )
            compatibility_code = self._compatibility_code(selected.files)
            return {
                "code": compatibility_code or selected.code,
                "files": selected.files,
                "reasoning": selected.reasoning,
                "known_limitations": self._extract_limitations(
                    compatibility_code or selected.code
                ),
            }

        # Otherwise, merge best parts
        merged_code = self._merge_solutions(outputs, debate_result)

        # Generate unified reasoning
        reasoning = self._generate_reasoning(outputs, debate_result)

        return {
            "code": merged_code,
            "files": None,
            "reasoning": reasoning,
            "known_limitations": self._extract_limitations(merged_code),
        }

    @staticmethod
    def _compatibility_code(files: list[Any] | None) -> str:
        """Derive the legacy scalar code field from structured files."""
        if not files:
            return ""

        file_data = [
            file.model_dump() if hasattr(file, "model_dump") else file
            for file in files
        ]
        python_files = [
            file
            for file in file_data
            if str(file.get("filename", "")).endswith(".py")
            and file.get("content", "").strip()
        ]
        candidates = python_files or [
            file for file in file_data if file.get("content", "").strip()
        ]
        main_file = next(
            (file for file in candidates if file.get("filename") == "main.py"),
            candidates[0] if candidates else None,
        )
        return str(main_file.get("content", "")) if main_file else ""

    def _merge_solutions(
        self,
        outputs: list[ModelOutput],
        debate_result: DebateResult,
    ) -> str:
        """Merge multiple solutions into one.

        Args:
            outputs: List of model outputs.
            debate_result: Debate results.

        Returns:
            Merged code string.
        """
        if len(outputs) == 1:
            return outputs[0].code

        # Simple strategy: use the longest complete solution
        # In production, this would do AST-based merging
        sorted_outputs = sorted(outputs, key=lambda o: len(o.code), reverse=True)

        best_code = sorted_outputs[0].code

        # Look for useful additions in other solutions
        for output in sorted_outputs[1:]:
            additions = self._find_unique_additions(best_code, output.code)
            if additions:
                best_code += "\n\n" + additions

        return best_code

    def _find_unique_additions(self, base_code: str, candidate_code: str) -> str:
        """Find unique useful additions in candidate code.

        Args:
            base_code: Base code to compare against.
            candidate_code: Candidate code with potential additions.

        Returns:
            Unique additions or empty string.
        """
        # Extract function/class definitions
        import ast

        try:
            base_tree = ast.parse(base_code)
            candidate_tree = ast.parse(candidate_code)

            base_names = {
                node.name
                for node in ast.walk(base_tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            }

            unique_parts = []
            for node in ast.walk(candidate_tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if node.name not in base_names:
                        unique_parts.append(ast.unparse(node))

            return "\n\n".join(unique_parts) if unique_parts else ""

        except SyntaxError:
            return ""

    def _generate_reasoning(
        self,
        outputs: list[ModelOutput],
        debate_result: DebateResult,
    ) -> str:
        """Generate unified reasoning document.

        Args:
            outputs: List of model outputs.
            debate_result: Debate results.

        Returns:
            Unified reasoning text.
        """
        lines = [
            "# Solution Synthesis Report",
            "",
            "## Sources",
            f"- Number of solutions considered: {len(outputs)}",
            f"- Providers: {', '.join(o.provider for o in outputs)}",
            "",
            "## Debate Summary",
            f"- Winner: {debate_result.winner_provider}",
            f"- Consensus reached: {debate_result.consensus_reached}",
            "",
            "## Key Decisions",
        ]

        # Add insights from each output
        for output in outputs:
            if output.reasoning:
                lines.append(f"\n### {output.provider}")
                lines.append(output.reasoning[:500])  # Truncate for brevity

        return "\n".join(lines)

    def _extract_limitations(self, code: str) -> list[str]:
        """Extract known limitations from code.

        Args:
            code: Code to analyze.

        Returns:
            List of known limitations.
        """
        limitations = []

        # Look for TODO comments
        todos = re.findall(r"#\s*TODO[:\s]*(.+)", code, re.IGNORECASE)
        limitations.extend([f"TODO: {t.strip()}" for t in todos[:5]])

        # Look for FIXME comments
        fixes = re.findall(r"#\s*FIXME[:\s]*(.+)", code, re.IGNORECASE)
        limitations.extend([f"FIXME: {f.strip()}" for f in fixes[:5]])

        # Look for NotImplementedError
        if "NotImplementedError" in code:
            limitations.append("Contains unimplemented sections")

        return limitations if limitations else ["No known limitations identified"]
