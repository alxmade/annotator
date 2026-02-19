"""Regex-based analyzer for TypeScript and JavaScript source files."""

from __future__ import annotations

import re

from .base import LanguageAnalyzer, SymbolInfo

# Patterns for function detection
_FUNC_PATTERNS = [
    # function name(
    re.compile(r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(", re.MULTILINE),
    # const name = (async) (args) =>
    re.compile(r"^(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\(", re.MULTILINE),
    # const name = async function(
    re.compile(r"^(?:export\s+)?const\s+(\w+)\s*=\s*async\s+function\s*\(", re.MULTILINE),
]

# Express endpoint patterns: app.get('/path', ...), router.post(
_EXPRESS_RE = re.compile(
    r"(?:app|router|server)\.(get|post|put|delete|patch|head|options)\s*\(\s*['\"`]([^'\"` ]+)['\"`]",
    re.IGNORECASE,
)

# NestJS decorator patterns: @Get('/path'), @Post(), @Controller('/base')
_NESTJS_ENDPOINT_RE = re.compile(
    r"@(Get|Post|Put|Delete|Patch|Head|Options)\s*\(\s*(?:['\"`]([^'\"` ]*)['\"`])?\s*\)",
    re.IGNORECASE,
)
_NESTJS_CONTROLLER_RE = re.compile(
    r"@Controller\s*\(\s*(?:['\"`]([^'\"` ]*)['\"`])?\s*\)",
    re.IGNORECASE,
)

# JSDoc presence: /** ... */ immediately before the line
_JSDOC_RE = re.compile(r"/\*\*[\s\S]*?\*/\s*$")


def _has_jsdoc_before(lines: list[str], func_line_idx: int) -> bool:
    """Return True if there is a JSDoc comment ending just before func_line_idx."""
    if func_line_idx == 0:
        return False
    # Look back up to 20 lines for closing */
    search_start = max(0, func_line_idx - 20)
    block = "\n".join(lines[search_start:func_line_idx])
    return bool(_JSDOC_RE.search(block))


class TypeScriptAnalyzer(LanguageAnalyzer):
    """Regex-based analyzer for TypeScript/JavaScript source files."""

    @property
    def language(self) -> str:
        return "typescript"

    @property
    def extensions(self) -> set[str]:
        return {".ts", ".js"}

    def analyze(self, content: str, diff: str = "") -> list[SymbolInfo]:
        """Analyze TypeScript/JS source and return symbols missing JSDoc.

        Args:
            content: Full source file content.
            diff: Optional git diff string (context only).

        Returns:
            List of SymbolInfo for functions/endpoints that lack JSDoc.
        """
        lines = content.splitlines()
        symbols: list[SymbolInfo] = []
        seen_lines: set[int] = set()

        # Detect NestJS controller base path
        controller_match = _NESTJS_CONTROLLER_RE.search(content)
        controller_base = controller_match.group(1) or "" if controller_match else ""

        # Map line numbers to NestJS endpoint decorators
        nestjs_endpoints: dict[int, tuple[str, str]] = {}
        for m in _NESTJS_ENDPOINT_RE.finditer(content):
            decorator_line = content[: m.start()].count("\n")
            method = m.group(1).upper()
            path_part = m.group(2) or ""
            full_path = f"/{controller_base.strip('/')}/{path_part.strip('/')}".rstrip("/")
            if not full_path.startswith("/"):
                full_path = "/" + full_path
            # The actual function is likely on a nearby line (within 5 lines)
            for offset in range(1, 6):
                nestjs_endpoints[decorator_line + offset] = (method, full_path)

        # Map line numbers to Express endpoints
        express_endpoints: dict[int, tuple[str, str]] = {}
        for m in _EXPRESS_RE.finditer(content):
            line_no = content[: m.start()].count("\n")
            express_endpoints[line_no] = (m.group(1).upper(), m.group(2))

        # Detect functions
        for pattern in _FUNC_PATTERNS:
            for m in pattern.finditer(content):
                line_no = content[: m.start()].count("\n")  # 0-indexed
                if line_no in seen_lines:
                    continue
                seen_lines.add(line_no)

                name = m.group(1)
                # Skip private by convention (_name)
                if name.startswith("_"):
                    continue

                has_docs = _has_jsdoc_before(lines, line_no)

                endpoint_method: str | None = None
                endpoint_path: str | None = None
                symbol_type = "function"

                # Check if this line is an Express endpoint callback
                # Express: app.get('/path', handler) - handler is inline, detect by proximity
                for ep_line, (ep_method, ep_path) in express_endpoints.items():
                    if abs(ep_line - line_no) <= 1:
                        endpoint_method = ep_method
                        endpoint_path = ep_path
                        symbol_type = "endpoint"
                        break

                # Check NestJS
                if symbol_type != "endpoint":
                    for ep_line, (ep_method, ep_path) in nestjs_endpoints.items():
                        if line_no == ep_line:
                            endpoint_method = ep_method
                            endpoint_path = ep_path
                            symbol_type = "endpoint"
                            break

                if not has_docs:
                    start = line_no
                    end = min(len(lines), start + 30)
                    symbols.append(
                        SymbolInfo(
                            name=name,
                            line=line_no + 1,  # 1-indexed for display
                            type=symbol_type,  # type: ignore[arg-type]
                            has_docs=False,
                            endpoint_method=endpoint_method,
                            endpoint_path=endpoint_path,
                            source_lines=lines[start:end],
                        )
                    )

        # Also detect standalone Express endpoints (inline anonymous handlers)
        for ep_line, (ep_method, ep_path) in express_endpoints.items():
            if ep_line not in seen_lines:
                seen_lines.add(ep_line)
                has_docs = _has_jsdoc_before(lines, ep_line)
                if not has_docs:
                    start = ep_line
                    end = min(len(lines), start + 30)
                    symbols.append(
                        SymbolInfo(
                            name=f"{ep_method.lower()}_{ep_path.replace('/', '_').strip('_')}",
                            line=ep_line + 1,
                            type="endpoint",
                            has_docs=False,
                            endpoint_method=ep_method,
                            endpoint_path=ep_path,
                            source_lines=lines[start:end],
                        )
                    )

        symbols.sort(key=lambda s: s.line)
        return symbols
