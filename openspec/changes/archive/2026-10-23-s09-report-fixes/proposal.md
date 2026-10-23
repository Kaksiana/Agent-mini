## Why

S09 报告发现完整 Schema 仍含 session_id、Registry 把非法 action 改判 invalid_arguments、宽松 int 接受 Schema 外类型、TC 计数/隔离断言不足，Store 返回可变共享对象。S09 需闭环后进入 S10。

## What Changes

- TodoArgs 文档去 session_id；action 改为 str 交给 handler 返回 invalid_action；index 严格 int。
- 补完整 Schema、Registry 非法 action、严格 index、跨会话 complete、伪造无副作用、快照测试。
- TodoItem 冻结；Store 返回快照；增加 configure_todo_store 注入点。
- 修正 TC-L1-006 文档口径为 complete 后仍 2 项、第一项 done。

## Capabilities

### Modified Capabilities

- `todo-tool`: Schema/Registry 类型边界、快照与可注入 Store。

## Impact

- `todo.py`、测试、TESTING/DESIGN/ISSUE/MEMORY/PROMPT；无依赖。
