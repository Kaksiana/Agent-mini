## Context

依据 `Docs/DESIGN.md` §3.2、`Docs/TESTING.md` TC-L1-015A/B/C 与 ISSUE-028 的用户决策。Phase 1 必须先通过 OpenSpec 校验，Phase 2 才能开始 TDD。

## Goals / Non-Goals

**Goals:**

- Phase 1：文档补全 `AgentResult`、`Agent.run`、TC 与 mypy 门禁。
- Phase 2：实现构造器注入的 `Agent` 与冻结 `AgentResult`。
- 仅单轮直答；异常原样传播。

**Non-Goals:**

- 不实现 S04 工具循环、消息配对、trace。
- 不实现 S05 安全阀/truncated。
- 不实现 S13 session_id/Memory。
- 不实现 S18 HTTP 响应。

## Decisions

- **签名**：`async def run(self, user_input: str) -> AgentResult`；session_id S13。
- **AgentResult**：pydantic `ConfigDict(frozen=True)`；字段 `reply: str`、`steps: int`、`usage: Usage`。
- **成功路径**：`chat([user])` 一次；意外 tool_calls 抛 `LLMProtocolError`；content 为空抛 `LLMEmptyResponseError`。
- **异常**：不捕获 `LLMError`，让原实例传播。
- **Phase 门禁**：tasks 分 Phase 1/2；Phase 1 完成并 strict validate 后才进入 Phase 2。

## Risks / Trade-offs

- [pydantic 冻结模型仍有嵌套 usage 可变] → S03 不修改 usage；下游按只读使用。
- [S04 会扩展 AgentResult] → 字段表显式列为延后，S04 通过新字段扩展而非改 reply 语义。
