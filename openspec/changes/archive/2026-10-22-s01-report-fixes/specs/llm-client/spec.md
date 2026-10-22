## ADDED Requirements

### Requirement: 响应顶层结构硬化

客户端 MUST 在解析响应前确认顶层为 object；数组、字符串、数字或 null 顶层 MUST 抛 `LLMProtocolError`，不得泄漏 `AttributeError`。

#### Scenario: 非 object 顶层

- **WHEN** 上游返回 HTTP 200 且 JSON 顶层为数组、字符串、数字或 null
- **THEN** 客户端抛 `LLMProtocolError`，错误码为 `LLM_PROTOCOL_ERROR`，不返回响应对象

### Requirement: 请求保留字段不可覆盖

客户端 MUST 拒绝调用方覆盖 `model`、`messages`、`thinking`、`tools` 等受控字段；`model`/`thinking` 及非法 `tools` MUST 抛 `ValueError`，`messages` 重复传参由 Python 签名拒绝，拒绝必须发生在发送 HTTP 请求前。

#### Scenario: 尝试覆盖受控字段

- **WHEN** 调用方传入 `model`、`messages`、`thinking` 或 `tools` 作为额外参数
- **THEN** 调用被拒绝（`ValueError` 或签名 `TypeError`），且不发送请求

### Requirement: reasoning 仅限 assistant

`Message` MUST 只允许 assistant 角色携带 `reasoning_content`；user、system、tool 角色传入该字段 MUST 被模型校验拒绝。

#### Scenario: 非 assistant 携带 reasoning

- **WHEN** 构造 `role=user/system/tool` 且带 `reasoning_content` 的消息
- **THEN** 模型校验失败，消息不能被序列化到请求
