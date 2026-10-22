## Why

S02 评估报告判定“有条件通过”：公开 `RetryPolicy` 可突破 3 次上限，重试没有 attempt 可观察记录，timeout 测试未证明配置生效，3xx 被误归为 BadRequest，并存在全局异常根与临时根的无条件 MUST 冲突。

## What Changes

- 将 `RetryPolicy.max_attempts` 限制为 1–3，并做运行时类型/可调用校验。
- 修复退避 cap 后延迟下降的问题，保证非递减。
- 新增 `RetryEvent` 与 `on_retry` 出口，记录 attempt、max_attempts、status_code、delay_seconds。
- 增加使用本地慢服务器的 timeout 上限测试。
- 将 3xx/未知状态映射为 `LLMProtocolError`，4xx 才映射 BadRequest。
- 在全局规范写入 S02–S19 临时 `LLMError` 例外与 S20 到期条件。
- 补具体异常类型/http_status、协议错误不重试与 S01 thinking+tools 组合回归。

## Capabilities

### New Capabilities

- 无。

### Modified Capabilities

- `llm-client`: 重试上界、attempt 事件、timeout 等待上限与 HTTP 状态分类。

## Impact

- 修改 `agent_mini/llm/{client,__init__}.py`、测试、DESIGN/TESTING/ISSUE/PLAN、S02-report。
- 不新增依赖；不实现 Runtime/Tool/Memory。
