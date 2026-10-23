"""TC-L1-001/002/003：calculator 安全求值。"""

import ast
from pathlib import Path
from typing import cast

import pytest

import agent_mini.tools.builtin.calculator as calculator_module
from agent_mini.tools.builtin.calculator import calculate
from agent_mini.tools.registry import DEFAULT_REGISTRY

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("(2+3)*4", "20"),
        ("1+2*3", "7"),
        ("5-2", "3"),
        ("-3+2", "-1"),
        ("+3", "3"),
        ("7/2", "3.5"),
        ("2.5*4", "10.0"),
    ],
)
def test_calculator_evaluates_four_operations(expression: str, expected: str) -> None:
    result = calculate(expression)

    assert result.ok is True
    assert result.content == expected


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os').system('x')",
        "eval('1')",
        "open('a','w')",
        "a.b",
        "x[0]",
        "lambda: 1",
        "[x for x in [1]]",
        "1<2",
        "True and False",
        "1|2",
        "2**3",
        "~1",
        "not 1",
    ],
)
def test_calculator_rejects_dangerous_expressions(expression: str) -> None:
    result = calculate(expression)

    assert result.ok is False
    assert result.error_code == "unsafe_expression"


@pytest.mark.parametrize(
    ("expression", "error_code"),
    [
        ("1/0", "division_by_zero"),
        ("2+", "syntax_error"),
        ('"a"+1', "type_error"),
        ("True", "type_error"),
    ],
)
def test_calculator_returns_structured_errors(expression: str, error_code: str) -> None:
    result = calculate(expression)

    assert result.ok is False
    assert result.error_code == error_code


def test_dangerous_open_has_no_side_effect(tmp_path: Path) -> None:
    target = str(tmp_path) + "/created.txt"
    result = calculate(f"open({target!r}, 'w')")

    assert result.error_code == "unsafe_expression"
    assert not (tmp_path / "created.txt").exists()


async def test_registry_preserves_too_long_error() -> None:
    result = await DEFAULT_REGISTRY.execute(
        "calculator",
        {"expression": "1+" * 100 + "1"},
    )

    assert result.error_code == "expression_too_long"


def test_calculator_is_registered_with_schema() -> None:
    spec = DEFAULT_REGISTRY.get("calculator")
    schema = spec.to_json_schema()
    parameters = cast(dict[str, object], schema["parameters"])

    assert parameters["type"] == "object"
    assert parameters["required"] == ["expression"]


async def test_registry_executes_calculator() -> None:
    result = await DEFAULT_REGISTRY.execute("calculator", {"expression": "2+3*4"})

    assert result.ok is True
    assert result.content == "14"


def test_calculator_converts_unexpected_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(expression: str) -> object:
        raise RuntimeError("boom")

    monkeypatch.setattr(calculator_module, "_evaluate_expression", boom)
    result = calculate("1")

    assert result.error_code == "evaluation_error"


def test_calculator_converts_parse_recursion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(expression: str, mode: str) -> object:
        raise RecursionError

    monkeypatch.setattr("agent_mini.tools.builtin.calculator.ast.parse", boom)
    result = calculate("1")

    assert result.error_code == "expression_too_deep"


def test_calculator_rejects_non_number_operation_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(calculator_module._BINARY_OPS, ast.Add, lambda a, b: "x")
    result = calculate("1+1")

    assert result.error_code == "type_error"


def test_calculator_rejects_too_long_expression() -> None:
    result = calculate("1+" * 100 + "1")

    assert result.error_code == "expression_too_long"


def test_calculator_rejects_too_deep_expression() -> None:
    result = calculate("1+" * 25 + "1")

    assert result.error_code == "expression_too_deep"


@pytest.mark.parametrize("expression", ["9" * 100, "1e309"])
def test_calculator_rejects_overflow(expression: str) -> None:
    result = calculate(expression)

    assert result.error_code == "number_overflow"
