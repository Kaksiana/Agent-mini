# short-term-memory Specification

## Purpose
定义 Redis 短时会话窗口：完整轮次 JSON、按轮 LTRIM、TTL、session_id 注入、响应前同步写回与 memory.degraded 降级。

## Requirements

### Requirement: 完整轮次存储

ShortTermMemory MUST 以单轮为 List 元素，元素含 round_id 与 messages；messages MUST 保留 role/content/tool_calls/tool_call_id/reasoning_content；MUST 用 JSON，禁止 pickle；LTRIM 按整轮保留最近 K（默认 10），TTL 默认 86400s 且每次写入刷新；key 含 session_id。

#### Scenario: 三轮裁剪

- **WHEN** 写入三轮后 get_recent_rounds(2)
- **THEN** 返回后两轮，tool 配对完整

### Requirement: 响应前同步写回

Agent.run MUST 在返回前 await 写回完整轮次；Redis 失败/超时/序列化失败 MUST 记录 memory.degraded 并跳过写回，不阻断对话。

#### Scenario: Redis 失败

- **WHEN** append 抛异常
- **THEN** Agent.run 仍返回结果，日志含 memory.degraded

### Requirement: session_id 兼容

Agent.run MUST 保持单参数调用兼容；session_id 可选并回传 AgentResult.session_id；不传时不写 Redis。

#### Scenario: 旧调用

- **WHEN** Agent.run("hi")
- **THEN** 正常工作，session_id=None
