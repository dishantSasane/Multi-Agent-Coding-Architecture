"""Deterministic extraction of generated project files."""

import re
from pathlib import PurePosixPath

from app.core.exceptions import CodeForgeException

_SEPARATOR_RE = re.compile(
    r"^#\s*={10,}\s+([^\s=]+)\s*={10,}\s*$", re.MULTILINE
)
_FENCE_RE = re.compile(r"```([^\n`]*)\n(.*?)```", re.DOTALL)
# A file body wrapped in its own Markdown fence (models often do this under a separator).
_WRAPPING_FENCE_RE = re.compile(r"\A```[^\n`]*\n(.*)\n```", re.DOTALL)
_FILENAME_RE = re.compile(r"(?:file|filename|path)\s*[:=]\s*([\w./-]+)", re.IGNORECASE)
_FILE_MARKER_RE = re.compile(r"^\s*FILE\s*:\s*(\S+)\s*$", re.IGNORECASE | re.MULTILINE)

MAX_FILES = 100
MAX_FILE_SIZE = 2 * 1024 * 1024
MAX_PROJECT_SIZE = 20 * 1024 * 1024
MAX_PATH_DEPTH = 20
MAX_FILENAME_LENGTH = 255


class CodeExtractionError(CodeForgeException):
    """Raised when generated output looks like a project but cannot be parsed safely."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message, {"error_code": "PROJECT_EXTRACTION_FAILED", **(details or {})})


def normalize_filename(filename: str) -> str:
    """Validate and normalize a generated relative project path."""
    normalized = filename.replace("\\", "/").strip()
    path = PurePosixPath(normalized)
    if (
        not normalized
        or path.is_absolute()
        or re.match(r"^[A-Za-z]:/", normalized)
        or ".." in path.parts
        or "\x00" in normalized
        or any(ord(char) < 32 for char in normalized)
        or len(normalized) > MAX_FILENAME_LENGTH
        or len(path.parts) > MAX_PATH_DEPTH
    ):
        raise CodeExtractionError(f"Unsafe generated file path: {filename!r}")
    if normalized.endswith("/") or any(part in {"", "."} for part in path.parts):
        raise CodeExtractionError(f"Invalid generated file path: {filename!r}")
    return str(path)


def file_metadata(filename: str) -> tuple[str, str]:
    """Return a deterministic language and file-type classification."""
    lower = filename.lower()
    if lower in {"dockerfile", "containerfile"}:
        return "dockerfile", "dockerfile"
    if lower.startswith(".env"):
        return "dotenv", "configuration"
    if lower.endswith((".py", ".pyi")):
        return "python", "source"
    if lower.endswith((".ts", ".tsx")):
        return "typescript", "source"
    if lower.endswith((".js", ".jsx", ".mjs", ".cjs")):
        return "javascript", "source"
    if lower.endswith(".json"):
        return "json", "data"
    if lower.endswith((".yaml", ".yml")):
        return "yaml", "configuration"
    if lower.endswith(".sql"):
        return "sql", "source"
    if lower.endswith(".md"):
        return "markdown", "documentation"
    if lower.endswith(".css"):
        return "css", "source"
    if lower.endswith(".html"):
        return "html", "source"
    if lower.endswith(".sh") or lower == "makefile":
        return "shell", "source"
    if lower == "requirements.txt" or lower.endswith(".lock"):
        return "text", "dependency"
    return "unknown", "text"


def _validate_file(filename: str, content: str) -> dict[str, str]:
    """Validate one extracted file and attach stable metadata."""
    normalized = normalize_filename(filename)
    wrapped = _WRAPPING_FENCE_RE.match(content)
    if wrapped:
        content = wrapped.group(1).strip()
    if not content or len(content.encode("utf-8")) > MAX_FILE_SIZE:
        raise CodeExtractionError(f"Invalid or oversized generated file: {normalized}")
    language, file_type = file_metadata(normalized)
    return {
        "filename": normalized,
        "content": content,
        "language": language,
        "file_type": file_type,
    }


def extract_code_files(content: str) -> list[dict[str, str]] | None:
    """Extract named files from supported LLM output formats.

    ``None`` means the content is a valid single-file response. A project-like
    response with ambiguous or unsafe boundaries raises ``CodeExtractionError``.
    """
    separator_matches = list(_SEPARATOR_RE.finditer(content))
    if separator_matches:
        if len(separator_matches) < 2:
            raise CodeExtractionError("Only one multi-file separator was found")
        files = []
        for index, match in enumerate(separator_matches):
            filename = normalize_filename(match.group(1))
            end = separator_matches[index + 1].start() if index + 1 < len(separator_matches) else len(content)
            file_content = content[match.end():end].strip()
            files.append(_validate_file(filename, file_content))
        return _unique_files(files)

    marker_matches = list(_FILE_MARKER_RE.finditer(content))
    if marker_matches:
        if len(marker_matches) < 2:
            raise CodeExtractionError("Only one FILE marker was found")
        files = []
        for index, match in enumerate(marker_matches):
            end = marker_matches[index + 1].start() if index + 1 < len(marker_matches) else len(content)
            files.append(_validate_file(match.group(1), content[match.end():end].strip()))
        return _unique_files(files)

    fences = list(_FENCE_RE.finditer(content))
    if len(fences) < 2:
        return None

    files = []
    for match in fences:
        header_tokens = match.group(1).strip().split()
        filename = next(
            (
                token
                for token in header_tokens
                if ("." in token and "/" in token) or token.startswith(".")
            ),
            None,
        )
        if not filename:
            filename = next((token for token in header_tokens if "." in token), None)
        if not filename:
            header = content[max(0, content.rfind("\n", 0, match.start()) + 1):match.start()]
            filename_match = _FILENAME_RE.search(header)
            filename = filename_match.group(1) if filename_match else None
        if not filename or "." not in filename:
            raise CodeExtractionError("Multiple code blocks found without reliable file names")
        files.append(_validate_file(filename, match.group(2).strip()))
    return _unique_files(files)


def _unique_files(files: list[dict[str, str]]) -> list[dict[str, str]]:
    """Reject duplicate paths instead of silently overwriting generated files."""
    if len(files) > MAX_FILES or sum(len(item["content"].encode("utf-8")) for item in files) > MAX_PROJECT_SIZE:
        raise CodeExtractionError("Generated project exceeds file or size limits")
    names = [item["filename"] for item in files]
    if len(names) != len(set(names)):
        raise CodeExtractionError("Generated output contains duplicate file paths")
    return files


def looks_like_unparsed_configuration(content: str) -> bool:
    """Identify a configuration-only response that is unsafe to parse as Python."""
    lines = [line.strip() for line in content.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    assignments = [line for line in lines if re.match(r"^[A-Z][A-Z0-9_]*\s*=", line)]
    return bool(lines) and len(assignments) == len(lines)
