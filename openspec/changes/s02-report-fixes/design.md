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
- **timeout 测试使用本机 `asyncio.start_server` 慢响应**：真实验证传输层超时，不依赖 respx 直接抛异常。
- **全局规范添加阶段例外**：S02–S19 临时 LLMError 根有效，S20 到期迁移，消除无条件 MUST 冲突。

## Risks / Trade-offs

- [本地慢服务器增加测试复杂度] → 使用 0.05s timeout 与短延迟，确保快速稳定。
- [RetryEvent 回调异常影响主流程] → 由调用方负责回调；默认无回调，不在核心路径抛业务异常。
- [3xx 更严格分类] → 代理/重定向场景明确失败，符合不可信边界。
