## ADDED Requirements

### Requirement: Registry 超长一致性

calculator 的模型 Schema MUST NOT 在 Registry 校验阶段把超长表达式改判为 `invalid_arguments`；超长 MUST 由 handler 统一返回 `expression_too_long`。

#### Scenario: Registry 超长

- **WHEN** 通过 Registry 传入超过 200 字符的表达式
- **THEN** 返回 expression_too_long
