## Why

S00 已提供可安装、可测试的包骨架，但尚未有任何模型调用能力。S01 需要以 OpenAI Chat Completions 协议打通单轮请求与响应归一，为 S02 错误重试和 S03 Runtime 提供可替换的 LLM 客户端。

## What Changes

- 新增 `agent_mini.llm` 的模型、错误与 httpx 异步客户端实现。
- 支持单轮 `chat()` 请求、文本/工具调用响应归一、usage 与 finish_reason 解析。
- 严格解析工具参数 JSON，并将非法参数保留为结构化 `ToolCall.error_code`。
- 默认显式发送 `thinking.disabled`；启用时保留并按协议回传历史 reasoning。
- 新增 L2 契约测试，覆盖 TC-L2-001、002、003、007、008、009、010 的 S01 覆盖部分。
- 声明并安装 `httpx`、`pydantic`、`respx`、`pytest-asyncio`。

## Capabilities

### New Capabilities

- `llm-client`: OpenAI 兼容的单轮模型调用、响应归一、工具参数解析与判别。

### Modified Capabilities

- 无。

## Impact

- 修改 `agent_mini/llm/{models,errors,client}.py`，新增 `tests/contract/`。
- 运行时依赖新增 `httpx`、`pydantic`；dev 依赖新增 `respx`、`pytest-asyncio`。
- 不实现 Runtime 循环、工具执行、真实 API 验收或错误重试。
