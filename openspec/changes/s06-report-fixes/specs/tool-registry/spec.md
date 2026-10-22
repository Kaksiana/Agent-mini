## ADDED Requirements

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
