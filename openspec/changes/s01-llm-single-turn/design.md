## Context

参见 `proposal.md`、`Docs/DESIGN.md` §3.1 与 ISSUE-020。S00 仅提供占位文件；S01 只实现 LLM 协议层，不实现 Runtime、Tool 执行、记忆或配置层。

## Goals / Non-Goals

**Goals:**

- 用 pydantic 定义消息、工具 Schema、工具调用、Usage 与 LLMResponse。
- 用 httpx.AsyncClient 完成单轮请求与响应解析。
- 用显式异常实现响应判别，用结构化 ToolCall 表示非法参数。
- 用 respx 覆盖 L2 契约，不访问真实 API。

**Non-Goals:**

- 不实现重试、鉴权错误分类、超时策略（S02）。
- 不实现 Runtime 循环、工具执行、ToolResult 映射（S03/S04/S06）。
- 不实现配置加载、DI、日志或真实 API 验收（S18/S19/S21）。
- 不读取 `DEEPSEEK_API_KEY`，不发起真实网络请求。

## Decisions

- **`ModelConfig` 临时放在 `llm/models.py`**：S01 需要 base_url/model/timeout；S21 配置层落地时迁移或复用，避免提前实现 config。
- **`LLMClient` 为 Protocol，`HttpLLMClient` 为具体实现**：便于 S03/S04 注入测试替身。
- **非法工具参数不抛出解析异常**：响应本身合法时，以 `ToolCall.error_code` 保留 call_id，供后续 Runtime 回灌；协议/终止错误仍抛异常。
- **默认 thinking 显式 disabled**：请求体固定带 `thinking`，避免供应商默认行为不确定。
- **依赖最小化**：运行时仅 httpx/pydantic；测试仅 respx/pytest-asyncio。

## Risks / Trade-offs

- [S01 临时 ModelConfig 与 S21 配置层重复] → ISSUE-020 记录迁移边界，S21 统一收口。
- [严格 JSON 解析与真实响应差异] → 契约测试覆盖重复键、NaN、数组、字符串等边界。
- [reasoning 回传范围在 S01 只验证客户端序列化] → 轮次裁剪由 S15/S16 测试覆盖。
