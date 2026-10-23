## Context

S13 P1-02/P1-04/P1-05 与 P2 需要闭合。测试分层：Redis/Runtime 联合用例放 integration。

## Decisions

- bind_request 只覆盖 session_id/trace_id，保留 sandbox 字段。
- Memory 参数校验 ValueError；坏记录 logging 后跳过；写回超时构造参数 memory_timeout。
- StoredRound 模型仍为后续（当前元数据 JSON 字段已保存）。
- S13 测试 moved tests/integration；M2 demo integration；unmarked=0。
