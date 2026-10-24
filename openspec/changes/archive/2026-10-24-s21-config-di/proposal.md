## Why

S03–S20 的配置读取散落在 HTTP，缺少统一配置模型与顶层装配。

## What Changes

- 四类冻结配置（Model/Tool/Prompt/SystemDB）+ AppConfig。
- YAML 非敏感 + 环境变量覆盖；缺必填抛 ConfigError。
- 手写 Container（singleton/transient/override），装配 LLM/Agent/HTTP app。
- ISSUE-025 采用运行依赖 minor 上界。
