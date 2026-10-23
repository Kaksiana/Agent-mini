## Context

S09 报告 P1-01..05 与 P2-01/02。修复只涉及 todo 模型/store/测试与文档。

## Decisions

- **Schema**：TodoArgs docstring 不再提 session_id；完整 Schema 断言字符串不含该词。
- **action**：模型用 str，handler 统一返回 invalid_action；避免 pydantic 抢先 invalid_arguments。
- **index**：`Field(strict=True)`，只接受 int；bool 也拒绝。
- **快照**：TodoItem frozen；Store 返回 `replace` 副本；complete 替换副本。
- **注入**：`configure_todo_store(store)` 提供 S13/测试注入点。
- **TC 口径**：complete 后 list 仍 2 项，第一项 done，第二项 open；文档同步。
