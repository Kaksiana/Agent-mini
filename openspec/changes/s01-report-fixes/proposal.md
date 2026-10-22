## Why

`Docs/S01-report.md` 判定 S01 暂不宜进入 S02：非 object JSON 顶层会泄漏 `AttributeError`，调用参数可覆盖 `model/thinking/tools` 等受控字段，`reasoning_content` 未限制为 assistant 私有状态；同时存在依赖下界、文档与归档顺序问题。

## What Changes

- 响应顶层非 object 统一抛 `LLMProtocolError`，不再泄漏 `AttributeError`。
- 拒绝 `model/messages/thinking/tools` 等保留请求字段被 `**params` 覆盖。
- `Message` 跨字段校验：只有 assistant 可携带 `reasoning_content`。
- 将 `ruff`、`mypy`、`pytest-asyncio`、`respx` pin 到 minor 兼容范围，并补充 `pytest-cov`。
- 同步 PLAN/TESTING/DESIGN/README/MEMORY/ISSUE 与 S01 报告修复记录。

## Capabilities

### New Capabilities

- 无。

### Modified Capabilities

- `llm-client`: 新增响应顶层结构、请求保留字段与 reasoning 角色约束。

## Impact

- 修改 `agent_mini/llm/{client,models}.py`、`pyproject.toml` 与契约测试。
- 不改变正常运行路径；新增的是拒绝非法输入与文档/依赖约束。
