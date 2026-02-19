"""Python AST-based analyzer for detecting functions and API endpoints."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from .base import LanguageAnalyzer, SymbolInfo

# Decorator patterns for FastAPI and Flask endpoint detection
_FASTAPI_DECORATOR_RE = re.compile(
    r"^(?:app|router|api)\.(get|post|put|delete|patch|head|options)\b",
    re.IGNORECASE,
)
_FLASK_ROUTE_RE = re.compile(
    r"^(?:app|blueprint|\w+)\.(route)\b",
    re.IGNORECASE,
)
_FLASK_METHOD_RE = re.compile(r"""methods\s*=\s*\[['"](\w+)['"]""")


def _decorator_to_endpoint(decorator: ast.expr) -> tuple[str, str] | None:
    """Extract (method, path) from a FastAPI/Flask decorator node, or None."""
    if isinstance(decorator, ast.Call):
        func = decorator.func
        # @app.get("/path") or @router.post("/path")
        if isinstance(func, ast.Attribute):
            method_name = func.attr.upper()
            if method_name in {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}:
                # Extract path from first positional arg
                if decorator.args and isinstance(decorator.args[0], ast.Constant):
                    return method_name, str(decorator.args[0].value)
            # Flask: @app.route("/path", methods=["POST"])
            if method_name == "ROUTE":
                path = None
                if decorator.args and isinstance(decorator.args[0], ast.Constant):
                    path = str(decorator.args[0].value)
                if path is None:
                    return None
                # Try to find methods kwarg
                for kw in decorator.keywords:
                    if kw.arg == "methods" and isinstance(kw.value, ast.List):
                        for elt in kw.value.elts:
                            if isinstance(elt, ast.Constant):
                                return str(elt.value).upper(), path
                return "GET", path  # Flask default
    return None


def _has_docstring(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return True if the function node has a docstring as its first statement."""
    if node.body:
        first = node.body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
            return isinstance(first.value.value, str)
    return False


class PythonAnalyzer(LanguageAnalyzer):
    """AST-based analyzer for Python source files."""

    @property
    def language(self) -> str:
        return "python"

    @property
    def extensions(self) -> set[str]:
        return {".py"}

    def analyze(self, content: str, diff: str = "") -> list[SymbolInfo]:
        """Analyze Python source and return symbols missing documentation.

        Args:
            content: Full Python source file content.
            diff: Optional git diff string (used for context, not filtering).

        Returns:
            List of SymbolInfo for functions/endpoints that lack docstrings.
        """
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return []

        lines = content.splitlines()
        symbols: list[SymbolInfo] = []

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            # Skip private/dunder methods except __init__
            if node.name.startswith("__") and node.name != "__init__":
                continue

            has_docs = _has_docstring(node)
            endpoint_method: str | None = None
            endpoint_path: str | None = None
            symbol_type: str = "function"

            # Check decorators for endpoint patterns
            for decorator in node.decorator_list:
                result = _decorator_to_endpoint(decorator)
                if result:
                    endpoint_method, endpoint_path = result
                    symbol_type = "endpoint"
                    break

            if not has_docs:
                # Gather source lines for context (up to 30 lines)
                start = node.lineno - 1
                end = min(node.end_lineno, start + 30) if hasattr(node, "end_lineno") else start + 10
                source_lines = lines[start:end]

                symbols.append(
                    SymbolInfo(
                        name=node.name,
                        line=node.lineno,
                        type=symbol_type,  # type: ignore[arg-type]
                        has_docs=False,
                        endpoint_method=endpoint_method,
                        endpoint_path=endpoint_path,
                        source_lines=source_lines,
                    )
                )

        return symbols
