"""Anthropic SDK wrapper for generating documentation proposals."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import anthropic

from .languages.base import SymbolInfo

MODEL = "claude-sonnet-4-6"

_PYTHON_SYSTEM = """\
You are a Python documentation expert. Given source code, generate PEP-257 compliant \
docstrings for functions that lack them.

Rules:
- Use triple double quotes.
- First line: concise one-sentence summary ending with a period.
- Include Args, Returns, and Raises sections only when applicable.
- If it is a FastAPI or Flask endpoint, also return an OpenAPI path item object under \
  the "openapi" key (null otherwise).
- Return ONLY valid JSON, no extra prose.
"""

_PYTHON_USER_TMPL = """\
Analyze the following Python source code and generate docstrings for all functions \
listed under "targets". Each target has a name and a 1-based line number.

Source file:
```python
{source}
```

Targets (name → line):
{targets}

Return JSON in this exact shape:
{{
  "proposals": [
    {{
      "symbol": "func_name",
      "line": 12,
      "docstring": "\"\"\"One-sentence summary.\\n\\nArgs:\\n    ...\"\"\"\n",
      "openapi": null
    }}
  ]
}}
"""

_TS_SYSTEM = """\
You are a TypeScript/JavaScript documentation expert. Given source code, generate JSDoc \
comments for functions that lack them.

Rules:
- Use /** */ format.
- Include @param and @returns tags when applicable.
- If it is an Express or NestJS endpoint, also return an OpenAPI path item object under \
  the "openapi" key (null otherwise).
- Return ONLY valid JSON, no extra prose.
"""

_TS_USER_TMPL = """\
Analyze the following TypeScript/JavaScript source code and generate JSDoc comments for \
all functions listed under "targets".

Source file:
```typescript
{source}
```

Targets (name → line):
{targets}

Return JSON in this exact shape:
{{
  "proposals": [
    {{
      "symbol": "funcName",
      "line": 8,
      "jsdoc": "/** One-sentence summary.\\n * @param name - Description\\n * @returns Description\\n */\n",
      "openapi": null
    }}
  ]
}}
"""


@dataclass
class DocProposal:
    """A documentation proposal for a single symbol."""

    symbol_name: str
    line: int
    proposed_doc: str       # docstring (Python) or jsdoc (TS/JS)
    openapi_snippet: dict[str, Any] | None = None
    postman_item: dict[str, Any] | None = None


def _build_targets_str(symbols: list[SymbolInfo]) -> str:
    lines = []
    for s in symbols:
        extra = ""
        if s.endpoint_method and s.endpoint_path:
            extra = f" [{s.endpoint_method} {s.endpoint_path}]"
        lines.append(f"  - {s.name} (line {s.line}){extra}")
    return "\n".join(lines)


def generate_docs(
    symbols: list[SymbolInfo],
    file_content: str,
    language: str,
    api_key: str | None = None,
) -> list[DocProposal]:
    """Call the Claude API to generate documentation for the given symbols.

    Args:
        symbols: List of symbols that need documentation.
        file_content: Full source file content for context.
        language: "python" or "typescript".
        api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.

    Returns:
        List of DocProposal objects with proposed documentation.
    """
    if not symbols:
        return []

    key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    client = anthropic.Anthropic(api_key=key)

    targets_str = _build_targets_str(symbols)

    if language == "python":
        system = _PYTHON_SYSTEM
        user_msg = _PYTHON_USER_TMPL.format(source=file_content, targets=targets_str)
        doc_key = "docstring"
    else:
        system = _TS_SYSTEM
        user_msg = _TS_USER_TMPL.format(source=file_content, targets=targets_str)
        doc_key = "jsdoc"

    message = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user_msg}],
    )

    raw = message.content[0].text.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    data = json.loads(raw)

    proposals: list[DocProposal] = []
    for item in data.get("proposals", []):
        proposals.append(
            DocProposal(
                symbol_name=item["symbol"],
                line=item["line"],
                proposed_doc=item.get(doc_key, ""),
                openapi_snippet=item.get("openapi"),
            )
        )
    return proposals
