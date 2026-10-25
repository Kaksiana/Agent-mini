# AIPROMPT — AI 执行记录索引

本文件是 AI Agent 执行 Prompt 的索引入口；逐阶段原文/摘要保存在 [PROMPT.md](PROMPT.md)。

## 使用方式

- 需要追溯某阶段“实际让 AI 做什么”时，先看 [PROMPT.md](PROMPT.md) 对应时间戳。
- 需要对照验收/修复项时，结合 [PLAN.md](PLAN.md)、[TESTING.md](TESTING.md)、[ISSUE.md](ISSUE.md) 阅读。
- 敏感信息（`DEEPSEEK_API_KEY`、DSN 密码、Bearer）不得写入本文件或任何 Prompt 记录。

## 阶段索引

| 阶段 | 主题 | 记录位置 |
| --- | --- | --- |
| S00–S05 | 基线、LLM、ReAct、安全阀 | `PROMPT.md` 对应时间戳 |
| S06–S12 | 工具、沙箱、Context | 同上 |
| S13–S16 | Redis/Mongo 记忆、窗口裁剪 | 同上 |
| S17 | MySQL 系统库 | 同上 |
| S18 | HTTP API | 同上 |
| S19 | 结构化日志/脱敏 | 同上 |
| S20 | 统一异常 | 同上 |
| S21 | 配置与 DI、M4 收尾 | 同上 |
| Demo | 真机测试用例/结果 | [test-report.md](test-report.md)、[test-result.md](test-result.md) |

## 当前门禁摘要

- 真机 Docker+LIVE：395 passed、1 skipped（2026-10-25）。
- 默认套件：388 passed、8 skipped。
- M3 五文件：54 passed。
- Python 3.11：394 passed、2 skipped。
- 覆盖率：94.95%。
- search 仅 mock；LIVE 需 `.env` Key。

> 本文件不复制完整 Prompt，避免与 [PROMPT.md](PROMPT.md) 产生双份漂移。
