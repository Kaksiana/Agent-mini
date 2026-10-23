# context-builder Specification

## Purpose
定义 Context 拼接与 token 预算：system→工具摘要→中期摘要→StoredRound 历史→当前 user、tools_snapshot 复用、规范 JSON 计数、10% 余量与 tiktoken 降级。

## Requirements

### Requirement: 上下文拼接与预算

ContextBuilder MUST 按 system prompt → 工具摘要（若发送）→ 中期摘要 → 短时历史（时间正序）→ 当前用户消息拼接；MUST 读取 StoredRound，不得解析 Redis/Mongo 原始 JSON；MUST 复用调用方传入的 tools_snapshot 同一引用。

#### Scenario: 五轮历史

- **WHEN** 历史 5 轮且预算充足
- **THEN** 全部保留，system 首位，current 末位，不裁剪

### Requirement: 计数与降级

TokenCounter MUST 对 messages 的 role/content/tool_calls/tool_call_id/reasoning 与完整 tools Schema 做规范 JSON 计数；estimated_input_tokens=message_tokens+tool_schema_tokens+protocol_overhead_tokens；budget=max_context-max_output-10%*max_context；tiktoken 不可用时字符比例降级但仍统计 Schema 并记录 token_counter.degraded。

#### Scenario: 预算公式

- **WHEN** max_context=16000、max_output=1024
- **THEN** budget=13376

#### Scenario: 降级

- **WHEN** tiktoken 加载失败
- **THEN** Schema 计数非 0，日志 token_counter.degraded

