# calculator Specification

## Purpose
定义 calculator 的安全求值契约：ast 白名单四则/括号/取负、危险表达式拒绝、阈值与结构化错误码。

## Requirements

### Requirement: 安全四则求值

calculator MUST 用 `ast.parse(mode="eval")` 解析表达式，仅允许 Expression/BinOp/UnaryOp/Constant 与 `+ - * /`、取负/取正；MUST 支持括号与 int/float 精度；MUST NOT 使用 `eval`/`exec`/`compile` 执行用户代码。

#### Scenario: 四则与括号

- **WHEN** 输入 `(2+3)*4`
- **THEN** 返回 ok=True，content 为 `20`

#### Scenario: 取负

- **WHEN** 输入 `-3+2`
- **THEN** 返回 `-1`

### Requirement: 拒绝危险表达式

调用、属性、下标、Name、Lambda、推导式、比较、布尔、位运算、幂等节点 MUST 返回 `unsafe_expression`，不得产生副作用。

#### Scenario: 代码执行

- **WHEN** 输入 `__import__('os').system('x')`
- **THEN** 返回 unsafe_expression，无副作用

### Requirement: 结构化错误与边界

语法错误、除零、字符串/布尔类型、超长、嵌套过深、数值溢出 MUST 返回 ToolResult(ok=False) 对应 error_code，不得抛异常；阈值 MUST 为具名常量：200 字符、20 层、1e12。

#### Scenario: 除零

- **WHEN** 输入 `1/0`
- **THEN** 返回 division_by_zero

#### Scenario: 语法错误

- **WHEN** 输入 `2+`
- **THEN** 返回 syntax_error

#### Scenario: 类型错误

- **WHEN** 输入 `"a"+1`
- **THEN** 返回 type_error

### Requirement: Registry 超长一致性

calculator 的模型 Schema MUST NOT 在 Registry 校验阶段把超长表达式改判为 `invalid_arguments`；超长 MUST 由 handler 统一返回 `expression_too_long`。

#### Scenario: Registry 超长

- **WHEN** 通过 Registry 传入超过 200 字符的表达式
- **THEN** 返回 expression_too_long
