## Why

S03 需要建立 Runtime 的第一个稳定接口：无工具单轮直答，以及会被 S04/S05/S13/S18 依赖的 `AgentResult`。现有文档缺少 S03 直答 TC、字段表和正式签名，已通过 ISSUE-028 确认方向 A。

## What Changes

- Phase 1：补 DESIGN §3.2 的 `Agent.run` 签名、`AgentResult` 字段表、session_id 延后、异常契约；TESTING 增加 TC-L1-015A/B/C、S03 覆盖边界与 `mypy agent_mini tests` 准出条款；PLAN 更新 S03 测试项与接口。
- Phase 2：TDD 实现 `Agent`（构造器注入 `LLMClient`）与冻结 `AgentResult(reply, steps, usage)`；不实现工具循环、trace、truncated、session_id 或 Memory。
- `Agent.run(user_input)` 发送单条 user 消息；`LLMError` 原样传播；意外 tool_calls 抛 `LLMProtocolError`。

## Capabilities

### New Capabilities

- `runtime`: S03 单轮直答接口与结果契约。

### Modified Capabilities

- 无。

## Impact

- 修改 `agent_mini/runtime/{agent,result}.py`；新增 `tests/unit/test_agent.py`。
- 更新 DESIGN/TESTING/PLAN/ISSUE/MEMORY/PROMPT/README。
- 不新增依赖；不修改 `llm/` 或其他子包。
