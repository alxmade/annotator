"""Tests for the Python AST-based analyzer."""

from pathlib import Path

import pytest

from annotator.languages.python_analyzer import PythonAnalyzer

FIXTURE = Path(__file__).parent / "fixtures" / "python" / "sample_fastapi.py"


@pytest.fixture
def analyzer() -> PythonAnalyzer:
    return PythonAnalyzer()


@pytest.fixture
def fixture_content() -> str:
    return FIXTURE.read_text()


def test_language(analyzer: PythonAnalyzer) -> None:
    assert analyzer.language == "python"


def test_extensions(analyzer: PythonAnalyzer) -> None:
    assert ".py" in analyzer.extensions


def test_detects_undocumented_function(analyzer: PythonAnalyzer, fixture_content: str) -> None:
    symbols = analyzer.analyze(fixture_content)
    names = [s.name for s in symbols]
    assert "add" in names


def test_skips_documented_function(analyzer: PythonAnalyzer, fixture_content: str) -> None:
    symbols = analyzer.analyze(fixture_content)
    names = [s.name for s in symbols]
    assert "documented_func" not in names


def test_detects_fastapi_endpoint(analyzer: PythonAnalyzer, fixture_content: str) -> None:
    symbols = analyzer.analyze(fixture_content)
    endpoints = [s for s in symbols if s.type == "endpoint"]
    assert len(endpoints) >= 1

    get_users = next((s for s in endpoints if s.name == "get_users"), None)
    assert get_users is not None
    assert get_users.endpoint_method == "GET"
    assert get_users.endpoint_path == "/users"


def test_detects_post_endpoint(analyzer: PythonAnalyzer, fixture_content: str) -> None:
    symbols = analyzer.analyze(fixture_content)
    create_user = next((s for s in symbols if s.name == "create_user"), None)
    assert create_user is not None
    assert create_user.endpoint_method == "POST"
    assert create_user.endpoint_path == "/users"


def test_detects_path_param_endpoint(analyzer: PythonAnalyzer, fixture_content: str) -> None:
    symbols = analyzer.analyze(fixture_content)
    get_user = next((s for s in symbols if s.name == "get_user"), None)
    assert get_user is not None
    assert get_user.endpoint_path == "/users/{user_id}"


def test_all_symbols_missing_docs(analyzer: PythonAnalyzer, fixture_content: str) -> None:
    symbols = analyzer.analyze(fixture_content)
    assert all(not s.has_docs for s in symbols)


def test_class_methods_detected(analyzer: PythonAnalyzer, fixture_content: str) -> None:
    symbols = analyzer.analyze(fixture_content)
    names = [s.name for s in symbols]
    assert "get_by_id" in names
    assert "create" in names


def test_empty_source(analyzer: PythonAnalyzer) -> None:
    assert analyzer.analyze("") == []


def test_syntax_error_returns_empty(analyzer: PythonAnalyzer) -> None:
    assert analyzer.analyze("def foo(:\n    pass") == []


def test_source_lines_captured(analyzer: PythonAnalyzer, fixture_content: str) -> None:
    symbols = analyzer.analyze(fixture_content)
    for s in symbols:
        assert len(s.source_lines) > 0
