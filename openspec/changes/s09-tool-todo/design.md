## Context

S06 `ToolContext` 已定义但未注入；S07/S08 handler 无 context。S09 只扩展注入，不改 Runtime。

## Decisions

- **上下文注入**：`ToolRegistry.execute(..., context=...)` 传入 `_invoke`；仅当 `inspect.signature(handler)` 含 `context` 参数时注入，避免影响 calculator/time。模型 Schema 仍只来自 `TodoArgs`。
- **存储**：`TodoStore` Protocol + `MemoryTodoStore`（进程内 dict[session_id, list[TodoItem]]）；重启丢失、非线程安全；S13 用 Memory KV 替换。测试通过 `reset_todo_store()` 隔离。
- **序号**：items 使用稳定自增 id（1-based）；complete/delete 按 id；删除不重排，不存在的 id 返回 `todo_not_found`；id<=0 返回 `invalid_index`。
- **行为**：action 为 add/list/complete/delete；add 需要非空 content；list 不需要；complete/delete 需要 index。
- **错误码**：`missing_context`、`invalid_action`、`invalid_index`、`todo_not_found`、`empty_content`。
- **伪造拒绝**：TodoArgs 无 session_id；Registry 白名单先拒绝，handler 不会被调用。

## Risks / Trade-offs

- 进程内存储重启丢失，S13 替换；非线程安全为当前假设。
- `ToolContext` 注入仅对声明 context 的 handler 生效，保持 S07/S08 零回归。
