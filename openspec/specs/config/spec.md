# config Specification

## Purpose
定义 config.yaml 与环境变量分层、四类冻结配置、SecretStr 隔离与轻量 DI 容器契约。

## Requirements

### Requirement: 配置加载与启动校验

配置 MUST 由 config.yaml 与环境变量合并，必填项缺失/类型或枚举非法时抛 ConfigError。

#### Scenario: 缺 Key 启动

- **WHEN** DEEPSEEK_API_KEY 缺失
- **THEN** 启动抛 ConfigError，消息含字段名

### Requirement: 轻量 DI 容器

容器 MUST 支持工厂、singleton/transient 与 override；不得使用模块级全局容器。

#### Scenario: 测试替换

- **WHEN** 覆盖 LLM 工厂
- **THEN** 解析 Agent 使用替身，无需改业务代码
