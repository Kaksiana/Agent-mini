"""TC-L1-001/002/003：calculator 安全求值。"""

from typing import cast

import pytest

from agent_mini.tools.builtin.calculator import calculate
from agent_mini.tools.registry import DEFAULT_REGISTRY

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("(2+3)*4", "20"),
        ("1+2*3", "7"),
        ("-3+2", "-1"),
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


def test_calculator_rejects_too_long_expression() -> None:
    result = calculate("1+" * 100 + "1")

    assert result.error_code == "expression_too_long"


def test_calculator_rejects_too_deep_expression() -> None:
    result = calculate("1+" * 25 + "1")

    assert result.error_code == "expression_too_deep"


def test_calculator_rejects_overflow() -> None:
    result = calculate("9" * 100)

    assert result.error_code == "number_overflow"
