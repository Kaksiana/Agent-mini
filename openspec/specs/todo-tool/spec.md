# todo-tool Specification

## Purpose
定义 todo 工具契约：ToolContext 会话注入、进程内 MemoryTodoStore、1-based 稳定 id、会话隔离与结构化错误。

## Requirements

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

### Requirement: Registry 类型与完整 Schema

todo 完整 Schema MUST NOT 含 session_id；非法 action MUST 在 Registry 路径返回 invalid_action；index MUST 只接受严格 integer，字符串/浮点/bool MUST 返回 invalid_arguments。

#### Scenario: 完整 Schema

- **WHEN** 序列化 todo Schema
- **THEN** 不含 session_id

#### Scenario: 非法 action

- **WHEN** Registry 收到 action=bogus
- **THEN** invalid_action

#### Scenario: 严格 index

- **WHEN** Registry 收到 index="1"/1.5/True
- **THEN** invalid_arguments

### Requirement: 隔离与快照

A/B 完成互不影响；伪造 session_id MUST 无副作用；Store 返回的元素 MUST 是快照，外部修改不得改变存储。

#### Scenario: 跨会话 complete

- **WHEN** A complete 后查 B
- **THEN** B 仍 open

#### Scenario: 伪造无副作用

- **WHEN** 带 session_id 参数调用被拒后 list
- **THEN** 原会话列表不变
