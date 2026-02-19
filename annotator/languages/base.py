"""Abstract base class for language analyzers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class SymbolInfo:
    """Information about a detected symbol (function, class, endpoint)."""

    name: str
    line: int
    type: Literal["function", "class", "endpoint"]
    has_docs: bool
    endpoint_method: str | None = None  # GET, POST, PUT, DELETE, PATCH
    endpoint_path: str | None = None    # /users, /items/{id}
    source_lines: list[str] = field(default_factory=list)  # lines of source for context


class LanguageAnalyzer(ABC):
    """Abstract base class for language-specific code analyzers."""

    @abstractmethod
    def analyze(self, content: str, diff: str = "") -> list[SymbolInfo]:
        """Analyze source code and return detected symbols.

        Args:
            content: Full source file content.
            diff: Optional git diff string for context.

        Returns:
            List of SymbolInfo objects for symbols needing documentation.
        """

    @property
    @abstractmethod
    def language(self) -> str:
        """Return the language name (e.g., 'python', 'typescript')."""

    @property
    @abstractmethod
    def extensions(self) -> set[str]:
        """Return supported file extensions (e.g., {'.py'})."""
