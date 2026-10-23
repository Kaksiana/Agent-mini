## ADDED Requirements

### Requirement: 双触发整轮裁剪

fit_rounds MUST 在轮次 > K（默认 10）或 estimated_input_tokens > budget 时丢弃最旧完整 StoredRound，并在每次丢弃后重计；MUST 保留 system、实际 tools 与当前轮；trim_reason MUST 为 rounds/tokens/both。

#### Scenario: 轮次裁剪

- **WHEN** 12 轮且预算充足
- **THEN** 保留最近 10 轮，trim_reason=rounds

#### Scenario: 最小集合超限

- **WHEN** system+current+tools 超预算
- **THEN** 抛 ContextTooLarge，不调用 LLM

### Requirement: 出站前复核

Agent/loop MUST 在每次 LLM chat 前调用 ContextBuilder.fit；ContextPayload 分项与 context.trimmed 日志一致。

#### Scenario: 工具回灌

- **WHEN** 工具结果加入 messages
- **THEN** 下一次 chat 前重新 fit
