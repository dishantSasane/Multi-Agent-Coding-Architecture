"""Security utilities for input sanitization and prompt injection guard."""

import re
from typing import Any

from app.core.exceptions import SecurityViolationError


class InputSanitizer:
    """Sanitize user inputs to prevent prompt injection attacks."""

    # Patterns that might indicate prompt injection attempts
    DANGEROUS_PATTERNS: list[re.Pattern] = [
        re.compile(r"ignore\s+(previous|above|all)", re.IGNORECASE),
        re.compile(r"(override|bypass|skip)\s+(rules|instructions|constraints)", re.IGNORECASE),
        re.compile(r"system\s*(prompt|instruction)", re.IGNORECASE),
        re.compile(r"<\|.*?\|>", re.IGNORECASE),  # Special tokens
        re.compile(r"```.*?```", re.DOTALL),  # Code blocks in prompts
        re.compile(r"print\s*\(\s*['\"].*?['\"]\s*\)", re.IGNORECASE),  # Print statements
        re.compile(r"os\.(system|popen|exec)", re.IGNORECASE),  # System calls
        re.compile(r"subprocess\.", re.IGNORECASE),  # Subprocess calls
        re.compile(r"eval\s*\(", re.IGNORECASE),  # Eval calls
        re.compile(r"exec\s*\(", re.IGNORECASE),  # Exec calls
        re.compile(r"__import__", re.IGNORECASE),  # Dynamic imports
        re.compile(r"importlib", re.IGNORECASE),  # Import lib
        re.compile(r"base64", re.IGNORECASE),  # Base64 encoding (often used to hide malicious code)
        re.compile(r"pickle", re.IGNORECASE),  # Pickle (unsafe deserialization)
    ]

    # Maximum lengths
    MAX_QUERY_LENGTH = 10000
    MAX_CONTEXT_LENGTH = 50000

    @classmethod
    def sanitize_query(cls, query: str) -> str:
        """Sanitize a user query.

        Args:
            query: The raw user query.

        Returns:
            Sanitized query string.

        Raises:
            SecurityViolationError: If dangerous patterns are detected.
        """
        if not query or not query.strip():
            raise SecurityViolationError("empty_query", {"reason": "Query cannot be empty"})

        # Truncate if too long
        if len(query) > cls.MAX_QUERY_LENGTH:
            query = query[: cls.MAX_QUERY_LENGTH]

        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if pattern.search(query):
                raise SecurityViolationError(
                    "prompt_injection_attempt",
                    {"pattern": pattern.pattern, "query_preview": query[:200]},
                )

        # Strip whitespace and normalize
        return query.strip()

    @classmethod
    def sanitize_context(cls, context: dict[str, Any]) -> dict[str, Any]:
        """Sanitize context dictionary.

        Args:
            context: The raw context dictionary.

        Returns:
            Sanitized context dictionary.
        """
        sanitized: dict[str, Any] = {}

        for key, value in context.items():
            # Sanitize key
            key = str(key).strip()[:100]

            # Sanitize value based on type
            if isinstance(value, str):
                if len(value) > cls.MAX_CONTEXT_LENGTH:
                    value = value[: cls.MAX_CONTEXT_LENGTH]
                value = value.strip()
            elif isinstance(value, dict):
                value = cls.sanitize_context(value)
            elif isinstance(value, list):
                value = [str(v)[:1000].strip() if isinstance(v, str) else v for v in value[:100]]
            elif value is None:
                continue

            sanitized[key] = value

        return sanitized

    @classmethod
    def contains_code_injection(cls, code: str) -> bool:
        """Check if code contains potential injection attacks.

        Args:
            code: Code to check.

        Returns:
            True if injection is detected, False otherwise.
        """
        dangerous_calls = [
            "__import__",
            "eval(",
            "exec(",
            "os.system",
            "os.popen",
            "subprocess",
            "pickle.loads",
            "marshal.loads",
        ]

        for call in dangerous_calls:
            if call in code:
                return True

        return False

    @classmethod
    def strip_markdown(cls, text: str) -> str:
        """Strip markdown code blocks from text.

        Args:
            text: Text potentially containing markdown.

        Returns:
            Text with markdown removed.
        """
        # Remove code blocks
        text = re.sub(r"```[\w]*\n?(.*?)```", r"\1", text, flags=re.DOTALL)
        # Remove inline code
        text = re.sub(r"`([^`]+)`", r"\1", text)
        return text.strip()

    @classmethod
    def extract_code_from_response(cls, response: str, language: str | None = None) -> str:
        """Extract code from LLM response.

        Args:
            response: Raw LLM response.
            language: Optional language hint for code block.

        Returns:
            Extracted code.
        """
        # Try to find code blocks
        pattern = r"```(?:\w+)?\n(.*?)```" if language is None else f"```{language}\\n(.*?)```"
        matches = re.findall(pattern, response, re.DOTALL)

        if matches:
            # Return the largest code block
            return max(matches, key=len).strip()

        # If no code blocks, return the response as-is
        return response.strip()
