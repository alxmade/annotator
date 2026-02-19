"""Tests for the TypeScript/JS regex-based analyzer."""

from pathlib import Path

import pytest

from annotator.languages.typescript_analyzer import TypeScriptAnalyzer

FIXTURE = Path(__file__).parent / "fixtures" / "typescript" / "sample_express.ts"


@pytest.fixture
def analyzer() -> TypeScriptAnalyzer:
    return TypeScriptAnalyzer()


@pytest.fixture
def fixture_content() -> str:
    return FIXTURE.read_text()


def test_language(analyzer: TypeScriptAnalyzer) -> None:
    assert analyzer.language == "typescript"


def test_extensions(analyzer: TypeScriptAnalyzer) -> None:
    assert ".ts" in analyzer.extensions
    assert ".js" in analyzer.extensions


def test_detects_undocumented_function(analyzer: TypeScriptAnalyzer, fixture_content: str) -> None:
    symbols = analyzer.analyze(fixture_content)
    names = [s.name for s in symbols]
    assert "multiply" in names


def test_skips_jsdoc_function(analyzer: TypeScriptAnalyzer, fixture_content: str) -> None:
    symbols = analyzer.analyze(fixture_content)
    names = [s.name for s in symbols]
    assert "add" not in names


def test_detects_const_arrow_function(analyzer: TypeScriptAnalyzer, fixture_content: str) -> None:
    symbols = analyzer.analyze(fixture_content)
    names = [s.name for s in symbols]
    assert "getUserById" in names


def test_all_symbols_missing_docs(analyzer: TypeScriptAnalyzer, fixture_content: str) -> None:
    symbols = analyzer.analyze(fixture_content)
    assert all(not s.has_docs for s in symbols)


def test_empty_source(analyzer: TypeScriptAnalyzer) -> None:
    assert analyzer.analyze("") == []


def test_simple_function_detected() -> None:
    analyzer = TypeScriptAnalyzer()
    code = "function greet(name: string): string {\n  return `Hello ${name}`;\n}\n"
    symbols = analyzer.analyze(code)
    assert len(symbols) == 1
    assert symbols[0].name == "greet"
    assert symbols[0].line == 1


def test_async_function_detected() -> None:
    analyzer = TypeScriptAnalyzer()
    code = "async function fetchData(url: string) {\n  return fetch(url);\n}\n"
    symbols = analyzer.analyze(code)
    assert any(s.name == "fetchData" for s in symbols)


def test_exported_function_detected() -> None:
    analyzer = TypeScriptAnalyzer()
    code = "export function compute(n: number): number {\n  return n * 2;\n}\n"
    symbols = analyzer.analyze(code)
    assert any(s.name == "compute" for s in symbols)
