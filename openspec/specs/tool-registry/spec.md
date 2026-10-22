# tool-registry Specification

## Purpose

定义工具注册与执行契约：`ToolSpec`/`ToolRegistry`/`@tool`、由 pydantic 模型生成的 OpenAI tools Schema、参数校验、唯一 `ToolResult` 与 Runtime 适配器。

## Requirements

### Requirement: 工具注册与查找

`ToolRegistry` MUST 支持以唯一名称注册 `ToolSpec`，按名称 `get`，`schemas()` 返回 OpenAI `ToolSchema` 列表；同名注册 MUST 抛 `DuplicateToolError` 且不覆盖原项。`@tool` MUST 将装饰函数注册到指定/默认注册表。

#### Scenario: 注册后查找

- **WHEN** 注册 `echo` 后查询
- **THEN** `get("echo")` 返回同一 ToolSpec，schemas 含 echo

#### Scenario: 重复注册

- **WHEN** 同名再次注册
- **THEN** 抛 DuplicateToolError，原 ToolSpec 不变

### Requirement: pydantic Schema

`ToolSpec.to_json_schema()` MUST 由 `params_model.model_json_schema()` 生成 `{name, description, parameters}`，parameters 为 JSON Schema object，required 与模型一致；不得手写并行 Schema。

#### Scenario: echo(text: str)

- **WHEN** params_model 有必填 text
- **THEN** schema parameters.type=object，properties 含 text，required 含 text

### Requirement: 参数校验与执行结果

`ToolRegistry.execute(name, arguments, context=None)` MUST 用 params_model 校验参数；无效参数返回 `ToolResult(ok=False,error_code="invalid_arguments")` 且不执行 handler；未知工具返回 `unknown_tool`；handler 异常 MUST 被捕获为 `tool_execution_error`，不得向上抛。`ToolResult` MUST 拒绝 `ok=True+error_code` 与 `ok=False` 无 error_code。

#### Scenario: 参数错误

- **WHEN** 缺少必填 text
- **THEN** 返回 invalid_arguments，handler 未执行

#### Scenario: handler 异常

- **WHEN** handler 抛 RuntimeError
- **THEN** 返回 tool_execution_error，原 call_id 由 Runtime 适配保留

### Requirement: Runtime 适配

`RegistryExecutor` MUST 实现 S04 `ToolExecutor`：`schemas()` 透传注册表，`execute(ToolCall)` 调用注册表并保留 call 绑定；不得把注册实现放入 runtime，不得引入具体内置工具。

#### Scenario: 注册表驱动循环

- **WHEN** 注册 echo 并以 RegistryExecutor 运行 Agent
- **THEN** Runtime 发送 schema、执行并收敛，无需改 Runtime 代码

### Requirement: 工具启停

`ToolRegistry` MUST 接受 `enabled` 映射；带 `enabled_key` 且配置为 false 的工具 MUST 不出现在 `schemas()`，`execute` MUST 返回 `tool_disabled`；配置为 true/未配置时启用。启停只影响下一请求快照，不修改已注册 ToolSpec。

#### Scenario: 禁用工具

- **WHEN** enabled_key 为 false
- **THEN** schemas 不含该工具，execute 返回 ok=False/error_code=tool_disabled

### Requirement: 异步与阻塞隔离

同步 handler MUST 通过 `asyncio.to_thread` 执行；async handler MUST 直接 await。同步 sleep 不得阻塞事件循环，外层 deadline/wait_for 必须可生效。

#### Scenario: 同步挂起

- **WHEN** 同步 handler sleep 50ms，外层 wait_for 10ms
- **THEN** 外层超时，不同步阻塞事件循环

### Requirement: 严格参数与返回值

execute MUST 仅接受 pydantic 模型声明的顶层字段，额外字段返回 `invalid_arguments`；handler MUST 返回 ToolResult，其他类型返回 `invalid_tool_result`。ToolSpec 注册 MUST 校验名称、描述、params_model、handler、enabled_key 非空/可调用。ToolResult 失败时 MUST 有可读非空 content。

#### Scenario: 伪造 session_id

- **WHEN** 参数含未声明的 session_id
- **THEN** 返回 invalid_arguments，handler 不执行

#### Scenario: 返回 None

- **WHEN** handler 返回 None
- **THEN** 返回 invalid_tool_result，不得包装为成功

### Requirement: 深层只读参数

`ToolCallTrace.args` MUST 递归只读（嵌套 dict/list 不可原地修改），同时可被 `model_dump`/JSON 序列化。

#### Scenario: 修改嵌套参数

- **WHEN** trace.args 含嵌套 dict 并尝试改值
- **THEN** 抛 TypeError
