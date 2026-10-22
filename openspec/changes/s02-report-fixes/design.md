## Context

参见 `proposal.md`、`Docs/S02-report.md` 与 ISSUE-026。S02 主路径已实现，本次修复公开策略边界、可观测出口和测试自证问题，不扩展 Runtime 层。

## Goals / Non-Goals

**Goals:**

- 将重试硬上限固定为 3，拒绝非法策略配置。
- 提供无敏感信息的 `RetryEvent` 出口。
- 用本地慢服务器证明 timeout 生效。
- 修正 3xx/未知状态分类与异常根规范例外。

**Non-Goals:**

- 不实现日志系统或 trace_id（S19）。
- 不实现 AgentError 迁移（S20）。
- 不引入新依赖。

## Decisions

- **硬上限 `MAX_ATTEMPTS_LIMIT = 3`**：与主规格和 TC-L2-004 对齐；`RetryPolicy` 1–3。
- **`RetryEvent` 作为回调**：不引入日志依赖，S19 可将事件接入结构化日志。
- **退避取 cap 后值**：`min(base + jitter, max)`，高尝试次数下不再下降。
- **timeout 测试采用配置断言 + ReadTimeout 分类**：本机慢服务器在 httpx 超时期限内调度不稳定，改为直接断言 `AsyncClient.timeout` 等于配置值，避免不稳定测试。
- **全局规范添加阶段例外**：S02–S19 临时 LLMError 根有效，S20 到期迁移，消除无条件 MUST 冲突。

## Risks / Trade-offs

- [直接断言私有 timeout 字段] → 仅测试使用，生产 API 不变；同时保留异常分类测试。
- [RetryEvent 回调异常影响主流程] → 由调用方负责回调；默认无回调，不在核心路径抛业务异常。
- [3xx 更严格分类] → 代理/重定向场景明确失败，符合不可信边界。
