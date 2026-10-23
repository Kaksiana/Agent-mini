"""S07 calculator：ast 白名单四则求值。"""

import ast
import math
from collections.abc import Callable
from typing import TypeAlias

from pydantic import BaseModel, Field

from agent_mini.tools.registry import ToolResult, tool

MAX_EXPRESSION_CHARS = 200
MAX_AST_DEPTH = 20
MAX_ABS_VALUE = 10**12
ERROR_UNSAFE = "unsafe_expression"
ERROR_SYNTAX = "syntax_error"
ERROR_DIVISION_BY_ZERO = "division_by_zero"
ERROR_TYPE = "type_error"
ERROR_TOO_LONG = "expression_too_long"
ERROR_TOO_DEEP = "expression_too_deep"
ERROR_OVERFLOW = "number_overflow"
ERROR_EVALUATION = "evaluation_error"

Number: TypeAlias = int | float
BinaryOperation: TypeAlias = Callable[[Number, Number], Number]
UnaryOperation: TypeAlias = Callable[[Number], Number]


def _add(left: Number, right: Number) -> Number:
    return left + right


def _sub(left: Number, right: Number) -> Number:
    return left - right


def _mul(left: Number, right: Number) -> Number:
    return left * right


def _div(left: Number, right: Number) -> Number:
    return left / right


def _positive(value: Number) -> Number:
    return +value


def _negative(value: Number) -> Number:
    return -value


_BINARY_OPS: dict[type[ast.operator], BinaryOperation] = {
    ast.Add: _add,
    ast.Sub: _sub,
    ast.Mult: _mul,
    ast.Div: _div,
}
_UNARY_OPS: dict[type[ast.unaryop], UnaryOperation] = {
    ast.UAdd: _positive,
    ast.USub: _negative,
}


class CalculatorArgs(BaseModel):
    """calculator 的唯一参数。"""

    expression: str = Field(min_length=1)


class CalculatorError(Exception):
    """求值中途的结构化错误。"""

    def __init__(self, error_code: str) -> None:
        super().__init__(error_code)
        self.error_code = error_code


@tool(
    "calculator",
    "安全计算四则与括号表达式，仅支持数字与 + - * /。",
    CalculatorArgs,
)
def calculate(expression: str) -> ToolResult:
    """安全求值并返回 ToolResult；任何失败都不向上抛。"""
    if len(expression) > MAX_EXPRESSION_CHARS:
        return ToolResult(False, "表达式过长", ERROR_TOO_LONG)
    try:
        value = _evaluate_expression(expression)
    except CalculatorError as exc:
        return ToolResult(False, _MESSAGES.get(exc.error_code, "计算失败"), exc.error_code)
    except Exception:
        return ToolResult(False, "计算失败", ERROR_EVALUATION)
    return ToolResult(True, str(value))


def _evaluate_expression(expression: str) -> Number:
    try:
        tree = ast.parse(expression, mode="eval")
    except (SyntaxError, ValueError) as exc:
        raise CalculatorError(ERROR_SYNTAX) from exc
    except RecursionError as exc:
        raise CalculatorError(ERROR_TOO_DEEP) from exc
    return _eval(tree.body, 1)


def _eval(node: ast.AST, depth: int) -> Number:
    if depth > MAX_AST_DEPTH:
        raise CalculatorError(ERROR_TOO_DEEP)
    if isinstance(node, ast.Constant):
        return _constant(node.value)
    if isinstance(node, ast.BinOp):
        return _binary(node, depth)
    if isinstance(node, ast.UnaryOp):
        return _unary(node, depth)
    raise CalculatorError(ERROR_UNSAFE)


def _constant(value: object) -> Number:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CalculatorError(ERROR_TYPE)
    return _checked(value)


def _binary(node: ast.BinOp, depth: int) -> Number:
    operation = _BINARY_OPS.get(type(node.op))
    if operation is None:
        raise CalculatorError(ERROR_UNSAFE)
    left = _eval(node.left, depth + 1)
    right = _eval(node.right, depth + 1)
    if isinstance(node.op, ast.Div) and right == 0:
        raise CalculatorError(ERROR_DIVISION_BY_ZERO)
    return _checked(operation(left, right))


def _unary(node: ast.UnaryOp, depth: int) -> Number:
    operation = _UNARY_OPS.get(type(node.op))
    if operation is None:
        raise CalculatorError(ERROR_UNSAFE)
    return _checked(operation(_eval(node.operand, depth + 1)))


def _checked(value: Number) -> Number:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CalculatorError(ERROR_TYPE)
    if isinstance(value, float) and not math.isfinite(value):
        raise CalculatorError(ERROR_OVERFLOW)
    if abs(value) > MAX_ABS_VALUE:
        raise CalculatorError(ERROR_OVERFLOW)
    return value


_MESSAGES = {
    ERROR_UNSAFE: "表达式包含不支持的语法",
    ERROR_TYPE: "表达式只能包含数字",
    ERROR_TOO_LONG: "表达式过长",
    ERROR_TOO_DEEP: "表达式嵌套过深",
    ERROR_OVERFLOW: "计算结果超出范围",
    ERROR_DIVISION_BY_ZERO: "除数不能为零",
    ERROR_SYNTAX: "表达式语法错误",
    ERROR_EVALUATION: "计算失败",
}
