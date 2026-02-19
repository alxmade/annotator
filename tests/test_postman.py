"""Tests for the Postman collection updater."""

import json
import uuid
from pathlib import Path

import pytest

from annotator.api_docs.postman import find_postman_file, update_request


def _make_collection(tmp_path: Path, name: str = "Test API") -> Path:
    col = tmp_path / f"{name}.postman_collection.json"
    col.write_text(
        json.dumps(
            {
                "info": {"name": name, "_postman_id": str(uuid.uuid4()), "schema": ""},
                "item": [],
            }
        )
    )
    return col


def test_find_postman_file(tmp_path: Path) -> None:
    col = _make_collection(tmp_path)
    found = find_postman_file(tmp_path)
    assert found == col


def test_find_returns_none_when_missing(tmp_path: Path) -> None:
    assert find_postman_file(tmp_path) is None


def test_update_request_adds_new_item(tmp_path: Path) -> None:
    col = _make_collection(tmp_path)
    update_request(col, "List Users", "GET", "/users")

    data = json.loads(col.read_text())
    assert len(data["item"]) == 1
    item = data["item"][0]
    assert item["name"] == "List Users"
    assert item["request"]["method"] == "GET"


def test_update_request_multiple_items(tmp_path: Path) -> None:
    col = _make_collection(tmp_path)
    update_request(col, "List Users", "GET", "/users")
    update_request(col, "Create User", "POST", "/users")

    data = json.loads(col.read_text())
    assert len(data["item"]) == 2


def test_update_request_with_custom_item(tmp_path: Path) -> None:
    col = _make_collection(tmp_path)
    custom = {
        "name": "Custom",
        "request": {
            "method": "PUT",
            "header": [{"key": "Content-Type", "value": "application/json"}],
            "url": {"raw": "{{base_url}}/items/1", "host": ["{{base_url}}"], "path": ["items", "1"]},
        },
        "response": [],
    }
    update_request(col, "Custom", "PUT", "/items/1", postman_item=custom)

    data = json.loads(col.read_text())
    assert data["item"][0]["name"] == "Custom"
    assert data["item"][0]["request"]["method"] == "PUT"


def test_update_request_url_contains_path(tmp_path: Path) -> None:
    col = _make_collection(tmp_path)
    update_request(col, "Get Item", "GET", "/items/{id}")

    data = json.loads(col.read_text())
    raw_url = data["item"][0]["request"]["url"]["raw"]
    assert "/items/{id}" in raw_url
