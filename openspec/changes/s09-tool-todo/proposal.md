## Why

S09 需要会话级 todo；S06 已预留 `ToolContext` 但尚未注入 handler。必须实现可信 session_id 边界，且不把 session_id 暴露给模型。

## What Changes

- 新增 `todo.py`：`TodoArgs(action, content, index)`、`@tool("todo")`、`ToolContext` 注入。
- `ToolRegistry` 仅在 handler 显式声明 `context` 时注入 `ToolContext`；模型 Schema 不含 session_id。
- 选择最小 `TodoStore` Protocol + 进程内 `MemoryTodoStore`；1-based 稳定 id，删除不重排；重启丢失、非线程安全，S13 替换。
- 错误码：`missing_context`、`invalid_index`、`todo_not_found`、`empty_content`、`invalid_action`。
- 不实现 Runtime/沙箱/Memory/HTTP；TC-L4-009/010 留 S18。

## Capabilities

### New Capabilities

- `todo-tool`: 会话隔离待办增删改查。

## Impact

- `todo.py`、`registry.py` 最小上下文注入、测试、文档、OpenSpec；无依赖。
