## Why

S01 起 LLMError 为临时根，S18 HTTP 局部映射需迁移到 AgentError 统一体系。

## What Changes

- AgentError 基类与 Config/LLM/Tool/Sandbox/Context/Input/SystemDB 子类。
- LLMError、ToolError、SandboxViolation、ContextTooLarge 迁移。
- HTTP 单一 AgentError 处理器与 4xx/5xx 日志级别。
