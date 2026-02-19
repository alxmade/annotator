"""Tests for the OpenAPI updater."""

import json
import tempfile
from pathlib import Path

import pytest

from annotator.api_docs.openapi import (
    find_openapi_file,
    get_operation_diff,
    update_operation,
)


@pytest.fixture
def yaml_spec(tmp_path: Path) -> Path:
    spec = tmp_path / "openapi.yaml"
    spec.write_text(
        "openapi: '3.0.0'\ninfo:\n  title: Test API\n  version: '1.0.0'\npaths: {}\n"
    )
    return spec


@pytest.fixture
def json_spec(tmp_path: Path) -> Path:
    spec = tmp_path / "openapi.json"
    spec.write_text(
        json.dumps({"openapi": "3.0.0", "info": {"title": "Test", "version": "1.0.0"}, "paths": {}})
    )
    return spec


def test_find_openapi_yaml(tmp_path: Path) -> None:
    f = tmp_path / "openapi.yaml"
    f.write_text("openapi: '3.0.0'\n")
    found = find_openapi_file(tmp_path)
    assert found == f


def test_find_openapi_in_docs_subdir(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    f = docs / "openapi.yaml"
    f.write_text("openapi: '3.0.0'\n")
    found = find_openapi_file(tmp_path)
    assert found == f


def test_find_returns_none_when_missing(tmp_path: Path) -> None:
    assert find_openapi_file(tmp_path) is None


def test_update_operation_yaml_creates_path(yaml_spec: Path) -> None:
    operation = {"summary": "List users", "responses": {"200": {"description": "OK"}}}
    result = update_operation(yaml_spec, "GET", "/users", operation)
    assert result is True

    content = yaml_spec.read_text()
    assert "/users" in content
    assert "List users" in content


def test_update_operation_json(json_spec: Path) -> None:
    operation = {"summary": "Create user", "responses": {"201": {"description": "Created"}}}
    update_operation(json_spec, "POST", "/users", operation)

    data = json.loads(json_spec.read_text())
    assert "/users" in data["paths"]
    assert "post" in data["paths"]["/users"]
    assert data["paths"]["/users"]["post"]["summary"] == "Create user"


def test_update_operation_merges_existing(json_spec: Path) -> None:
    # First write
    update_operation(json_spec, "GET", "/users", {"summary": "List", "deprecated": False})
    # Second write adds a new field without removing existing
    update_operation(json_spec, "GET", "/users", {"description": "Fetch all users"})

    data = json.loads(json_spec.read_text())
    op = data["paths"]["/users"]["get"]
    assert op["summary"] == "List"
    assert op["description"] == "Fetch all users"


def test_get_operation_diff(json_spec: Path) -> None:
    diff = get_operation_diff(json_spec, "GET", "/users", {"summary": "List users"})
    # Should return a non-empty diff string
    assert "List users" in diff


def test_update_adds_leading_slash(json_spec: Path) -> None:
    update_operation(json_spec, "GET", "items", {"summary": "List items"})
    data = json.loads(json_spec.read_text())
    assert "/items" in data["paths"]
