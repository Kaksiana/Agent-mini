## ADDED Requirements

### Requirement: 会话级待办

todo MUST 通过 `ToolContext.session_id` 分区；同会话 add/list/complete/delete 一致，空列表返回空 items；不同 session 不共享。序号 1-based、删除不重排；存储为进程内 MemoryTodoStore，重启丢失且不保证并发安全，S13 替换。

#### Scenario: 同会话增查改

- **WHEN** add("a")、add("b")、list、complete(1)、list
- **THEN** 第一次 items=2，第二次第一项 done

#### Scenario: 跨会话隔离

- **WHEN** A/B 各自 add
- **THEN** 各自 list 只看自己的 items

### Requirement: 可信上下文注入

session_id MUST 只来自 `ToolContext`；模型 Schema MUST NOT 含 session_id；伪造 session_id MUST 作为额外字段拒绝（invalid_arguments）。

#### Scenario: 伪造 session_id

- **WHEN** Registry 参数含 session_id
- **THEN** invalid_arguments，不执行 todo

### Requirement: 结构化错误

缺失 context、非法 action/index、内容为空、序号不存在 MUST 返回 ToolResult(ok=False,error_code=...)，不抛异常。

#### Scenario: 缺失上下文

- **WHEN** execute 未传 context
- **THEN** missing_context
