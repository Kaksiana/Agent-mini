## Context

S06 提供 `@tool`/ToolResult。Calculator 由 pydantic 参数模型注册到默认 registry，handler 只做纯计算，不访问外部状态。

## Decisions

- **AST 白名单**：`Expression`、`BinOp`、`UnaryOp`、`Constant`，运算符 `Add/Sub/Mult/Div`、`UAdd/USub`。
- **拒绝**：Call/Attribute/Subscript/Name/Lambda/ListComp/SetComp/DictComp/GeneratorExp/Compare/BoolOp/BitOp/Pow 等一律 `unsafe_expression`。
- **数值**：仅 int/float，bool 拒绝为 `type_error`；`/` 保持 Python 浮点语义。
- **阈值**：`MAX_EXPRESSION_CHARS=200`、`MAX_AST_DEPTH=20`、`MAX_ABS_VALUE=1e12`；超限分别 `expression_too_long`、`expression_too_deep`、`number_overflow`。
- **错误码**：集中常量，不散落字符串；除零、语法、类型分别固定。
- **注册**：模块导入时 `@tool` 注册；S08+ 保持同样模式。

## Risks / Trade-offs

- [大整数解析] → 解析后立即检查绝对值，避免继续运算。
- [嵌套递归] → 深度参数限制，避免 RecursionError 穿透。
