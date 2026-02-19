"""Postman Collection JSON updater."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any


def find_postman_file(search_root: Path) -> Path | None:
    """Search for a Postman collection file in common locations.

    Args:
        search_root: Directory to start searching from.

    Returns:
        Path to the first found collection file, or None.
    """
    # Check root and common subdirs
    candidates = list(search_root.glob("*.postman_collection.json"))
    if candidates:
        return candidates[0]
    for subdir in ["postman", "collections", "api"]:
        candidates = list((search_root / subdir).glob("*.json"))
        for c in candidates:
            if "postman" in c.name.lower() or "collection" in c.name.lower():
                return c
    return None


def _load_collection(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _save_collection(path: Path, data: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def _find_item(items: list[dict], name: str, method: str, url_path: str) -> dict | None:
    """Recursively search for a request item by name/method/URL."""
    for item in items:
        if "item" in item:
            result = _find_item(item["item"], name, method, url_path)
            if result:
                return result
        if "request" in item:
            req = item["request"]
            req_method = req.get("method", "").upper()
            raw_url = ""
            url = req.get("url", {})
            if isinstance(url, str):
                raw_url = url
            elif isinstance(url, dict):
                raw_url = url.get("raw", "")
            if req_method == method.upper() and url_path in raw_url:
                return item
    return None


def _build_postman_item(
    name: str,
    method: str,
    path: str,
    description: str | None = None,
) -> dict[str, Any]:
    """Build a minimal Postman request item."""
    path_segments = [p for p in path.split("/") if p]
    return {
        "name": name,
        "request": {
            "method": method.upper(),
            "header": [],
            "url": {
                "raw": f"{{{{base_url}}}}{path}",
                "host": ["{{base_url}}"],
                "path": path_segments,
            },
            "description": description or "",
        },
        "response": [],
    }


def update_request(
    collection_path: Path,
    name: str,
    http_method: str,
    endpoint_path: str,
    postman_item: dict[str, Any] | None = None,
    description: str | None = None,
) -> bool:
    """Add or update a request in a Postman collection.

    Args:
        collection_path: Path to the .postman_collection.json file.
        name: Name for the request item.
        http_method: HTTP method (GET, POST, etc.).
        endpoint_path: API endpoint path.
        postman_item: Full Postman item dict to use (overrides auto-build).
        description: Description to set if building a new item.

    Returns:
        True if the collection was modified and saved.
    """
    data = _load_collection(collection_path)
    items: list[dict] = data.get("item", [])

    existing = _find_item(items, name, http_method, endpoint_path)

    if existing:
        # Update description if provided
        if description and "request" in existing:
            existing["request"]["description"] = description
        if postman_item:
            existing.update(postman_item)
    else:
        # Add new item
        new_item = postman_item or _build_postman_item(name, http_method, endpoint_path, description)
        if "id" not in new_item:
            new_item["id"] = str(uuid.uuid4())
        items.append(new_item)
        data["item"] = items

    _save_collection(collection_path, data)
    return True
