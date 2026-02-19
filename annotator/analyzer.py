"""Main orchestrator: file collection, analysis, and proposal generation."""

from __future__ import annotations

from pathlib import Path

from . import git
from .client import DocProposal, generate_docs
from .languages.base import LanguageAnalyzer, SymbolInfo
from .languages.python_analyzer import PythonAnalyzer
from .languages.typescript_analyzer import TypeScriptAnalyzer

_ANALYZERS: list[LanguageAnalyzer] = [PythonAnalyzer(), TypeScriptAnalyzer()]

_EXT_TO_ANALYZER: dict[str, LanguageAnalyzer] = {
    ext: analyzer for analyzer in _ANALYZERS for ext in analyzer.extensions
}

SUPPORTED_EXTENSIONS = set(_EXT_TO_ANALYZER.keys())


def collect_files(target: Path, staged_only: bool = False) -> list[Path]:
    """Collect source files to analyze.

    Args:
        target: File or directory path to analyze.
        staged_only: If True, only return git-staged files.

    Returns:
        List of supported source file paths.
    """
    if staged_only:
        repo_root = git.get_repo_root(target if target.is_dir() else target.parent)
        if repo_root is None:
            return []
        return git.get_staged_files(repo_root)

    if target.is_file():
        if target.suffix in SUPPORTED_EXTENSIONS:
            return [target]
        return []

    files: list[Path] = []
    for ext in SUPPORTED_EXTENSIONS:
        files.extend(target.rglob(f"*{ext}"))

    # Exclude common noise directories
    excluded = {"node_modules", ".venv", "venv", "__pycache__", ".git", "dist", "build"}
    files = [f for f in files if not any(part in excluded for part in f.parts)]
    files.sort()
    return files


def analyze_file(
    file_path: Path,
    staged_only: bool = False,
    api_key: str | None = None,
) -> list[DocProposal]:
    """Analyze a single file and return documentation proposals.

    Args:
        file_path: Path to the source file.
        staged_only: Whether analysis is in staged-only mode (for diff context).
        api_key: Anthropic API key.

    Returns:
        List of documentation proposals.
    """
    analyzer = _EXT_TO_ANALYZER.get(file_path.suffix)
    if analyzer is None:
        return []

    content = file_path.read_text(encoding="utf-8", errors="replace")
    diff = git.get_diff(file_path, cached=staged_only)

    symbols = analyzer.analyze(content, diff)
    if not symbols:
        return []

    proposals = generate_docs(
        symbols=symbols,
        file_content=content,
        language=analyzer.language,
        api_key=api_key,
    )
    return proposals


def apply_proposals(
    file_path: Path,
    proposals: list[DocProposal],
    language: str,
) -> None:
    """Write accepted proposals back to the source file.

    Args:
        file_path: Path to the source file.
        proposals: Accepted documentation proposals.
        language: "python" or "typescript".
    """
    from .ui.diff_viewer import _apply_proposals_to_source

    if not proposals:
        return

    source = file_path.read_text(encoding="utf-8", errors="replace")
    modified = _apply_proposals_to_source(source, proposals, language)
    file_path.write_text(modified, encoding="utf-8")


def get_language(file_path: Path) -> str:
    """Return the language string for a given file path."""
    analyzer = _EXT_TO_ANALYZER.get(file_path.suffix)
    return analyzer.language if analyzer else "unknown"
