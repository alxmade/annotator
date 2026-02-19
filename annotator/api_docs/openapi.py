"""OpenAPI/Swagger YAML and JSON updater using ruamel.yaml for comment preservation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

_YAML = YAML()
_YAML.preserve_quotes = True
_YAML.default_flow_style = False

# Common locations to search for OpenAPI spec files
_CANDIDATE_NAMES = [
    "openapi.yaml",
    "openapi.yml",
    "openapi.json",
    "swagger.yaml",
    "swagger.yml",
    "swagger.json",
]
_CANDIDATE_DIRS = [".", "docs", "api", "spec", "specs", "schema"]


def find_openapi_file(search_root: Path) -> Path | None:
    """Search for an OpenAPI/Swagger spec file in common locations.

    Args:
        search_root: Directory to start searching from.

    Returns:
        Path to the first found spec file, or None.
    """
    for directory in _CANDIDATE_DIRS:
        for name in _CANDIDATE_NAMES:
            candidate = search_root / directory / name
            if candidate.exists():
                return candidate
    return None


def _load_spec(path: Path) -> tuple[Any, str]:
    """Load an OpenAPI spec file, returning (data, format) where format is 'yaml' or 'json'."""
    if path.suffix == ".json":
        with path.open(encoding="utf-8") as f:
            return json.load(f), "json"
    with path.open(encoding="utf-8") as f:
        return _YAML.load(f), "yaml"


def _save_spec(path: Path, data: Any, fmt: str) -> None:
    """Save an OpenAPI spec file, preserving format."""
    if fmt == "json":
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
    else:
        with path.open("w", encoding="utf-8") as f:
            _YAML.dump(data, f)


def update_operation(
    spec_path: Path,
    http_method: str,
    endpoint_path: str,
    operation: dict[str, Any],
) -> bool:
    """Merge or replace an operation object in an OpenAPI spec.

    Args:
        spec_path: Path to the OpenAPI YAML or JSON file.
        http_method: HTTP method (GET, POST, etc.) in uppercase.
        endpoint_path: API path (e.g., /users/{id}).
        operation: OpenAPI operation object to merge.

    Returns:
        True if the spec was modified and saved, False otherwise.
    """
    data, fmt = _load_spec(spec_path)

    if "paths" not in data:
        data["paths"] = {}

    path_key = endpoint_path if endpoint_path.startswith("/") else f"/{endpoint_path}"
    method_key = http_method.lower()

    if path_key not in data["paths"]:
        data["paths"][path_key] = {}

    existing = data["paths"][path_key].get(method_key, {})

    # Merge: new values override existing, but keep existing keys not in new
    merged = {**existing, **operation}
    data["paths"][path_key][method_key] = merged

    _save_spec(spec_path, data, fmt)
    return True


def get_operation_diff(
    spec_path: Path,
    http_method: str,
    endpoint_path: str,
    proposed: dict[str, Any],
) -> str:
    """Return a human-readable diff string for a proposed operation update.

    Args:
        spec_path: Path to the OpenAPI spec file.
        http_method: HTTP method in uppercase.
        endpoint_path: API endpoint path.
        proposed: Proposed operation object.

    Returns:
        Diff string showing current vs proposed.
    """
    import difflib

    data, fmt = _load_spec(spec_path)
    path_key = endpoint_path if endpoint_path.startswith("/") else f"/{endpoint_path}"
    method_key = http_method.lower()

    current = {}
    if "paths" in data and path_key in data["paths"]:
        current = dict(data["paths"][path_key].get(method_key, {}))

    current_str = json.dumps(current, indent=2).splitlines(keepends=True)
    proposed_str = json.dumps({**current, **proposed}, indent=2).splitlines(keepends=True)

    diff = difflib.unified_diff(
        current_str,
        proposed_str,
        fromfile=f"current {method_key.upper()} {path_key}",
        tofile=f"proposed {method_key.upper()} {path_key}",
        lineterm="",
    )
    return "".join(diff)
