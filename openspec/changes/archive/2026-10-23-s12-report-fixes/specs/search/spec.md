## ADDED Requirements

### Requirement: M2 显式装载与严格 provider

导入 `agent_mini.tools.builtin` MUST 恰好注册六工具；干净进程 MUST 可见六 Schema。Provider name 与 SearchResult 四字段 MUST 为 str，否则 `provider_result_invalid`。

#### Scenario: 干净进程

- **WHEN** 新解释器只导入 builtin 与 registry
- **THEN** schemas 名称集合为六工具

#### Scenario: 畸形字段

- **WHEN** provider 返回非 str 字段或 name
- **THEN** provider_result_invalid
