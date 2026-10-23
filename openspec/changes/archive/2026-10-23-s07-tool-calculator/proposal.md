## Why

S06 已有注册表与 ToolResult，但 calculator 仍缺失。S07 需要安全四则/括号求值，并拒绝任意代码执行。

## What Changes

- 新增 `tools/builtin/calculator.py`：pydantic `CalculatorArgs`、`@tool` 注册、`ast` 白名单求值。
- 支持 Expression/BinOp/UnaryOp/Constant、`+ - * /`、取负/取正、括号；拒绝调用、属性、下标、Name、Lambda、推导式、比较、布尔、位运算、幂。
- 错误码：`unsafe_expression`、`syntax_error`、`division_by_zero`、`type_error`、`expression_too_long`、`expression_too_deep`、`number_overflow`。
- 阈值：200 字符、20 层 AST、绝对值 1e12；bool 不算数值。
- 不实现其他工具/沙箱/Runtime 改动。

## Capabilities

### New Capabilities

- `calculator`: 安全四则表达式工具。

## Impact

- 新增 calculator 与测试；更新 PLAN/DESIGN/TESTING/ISSUE/MEMORY/PROMPT/README 与 OpenSpec。
- 无依赖新增。
