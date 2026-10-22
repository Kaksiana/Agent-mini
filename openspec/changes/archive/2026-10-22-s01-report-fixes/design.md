## Context

参见 `proposal.md`、`Docs/S01-report.md` 与 ISSUE-022。S01 主路径已实现，本次只做协议硬化、依赖约束与文档补全，不扩展 Runtime/Tool/Memory 功能。

## Goals / Non-Goals

**Goals:**

- 关闭 P0-01 与 P1-01/P1-09 的行为缺口。
- 补齐 S01 报告指出的文档、依赖与流程闭环。
- 保持 36 个既有测试通过。

**Non-Goals:**

- 不实现 S02 的 HTTP 状态分类/重试。
- 不实现 S04 的循环、消息配对与 trace。
- 不实现 S20 的 `AgentError` 统一异常基类；S01 采用临时 `LLMError` 根并记录迁移点。

## Decisions

- **顶层类型检查放在 `LLMResponse.from_openai` 入口**：直接解析与 HTTP 路径共用同一保护。
- **保留字段用集合拒绝**：在合并 `params` 前抛 `ValueError`，避免静默覆盖配置或协议字段。
- **reasoning 角色校验放在 pydantic 模型验证器**：任何构造路径都受约束，而不只依赖解析器。
- **dev 工具按 minor pin**：`ruff 0.17.x`、`mypy 2.4.x`、`pytest-asyncio 1.3.x`、`respx 0.23.x`、`pytest-cov 7.1.x`；避免解析漂移。
- **异常基类暂不迁移**：S01 保留 `LLMError` 临时根，S20 引入 `AgentError` 后统一继承，设计与 ISSUE 记录。

## Risks / Trade-offs

- [保留字段拒绝可能影响未来供应商参数] → 白名单后续在 S02 扩展并补测试。
- [minor pin 需要定期升级] → 在 ISSUE-021/依赖审计中记录升级流程。
- [角色校验可能影响历史数据] → S13/S16 恢复消息时必须遵守 assistant-only 规则。
