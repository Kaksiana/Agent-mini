## Context

S04 定义 `ToolExecutor`/`ToolOutcome`；S06 的 Tool 层不得依赖 Runtime/LLM，因此注册表使用 `name+arguments+context`，Runtime 适配器负责 ToolCall 绑定。

## Decisions

- **唯一结果结构**：`tools.registry.ToolResult` 取代 Runtime 的重复 `ToolOutcome` 定义；Runtime 通过导入/别名复用，Tool 不反向依赖 Runtime。
- **ToolContext**：定义 `ToolContext(session_id, trace_id)` 预留，`execute(..., context=None)` 接受；S06 不注入/实现会话状态，S09 落实。
- **ToolSpec**：冻结 dataclass，字段 name/description/params_model/handler/enabled_key；schema 来自 pydantic。
- **装饰器**：`@tool(...)` 注册到指定 registry（默认全局），返回原函数。
- **错误**：`ToolError` 根，`ToolRegistrationError`/`DuplicateToolError`；执行错误码 `unknown_tool`/`invalid_arguments`/`tool_execution_error`。
- **P2-04**：ToolResult `__post_init__` 保持 ok/error_code 一致；ToolCallTrace.args 采用只读映射/防御副本。
- **集成**：`runtime/registry_adapter.py` 实现 `ToolExecutor`，不改循环语义。

## Risks / Trade-offs

- [Tool 层不能导入 LLM] → 注册表使用普通 dict/str；Runtime adapter 转换 ToolCall。
- [ToolContext 暂不注入] → 预留参数，S09 再定义 handler 注入方式。
