# MEMORY <!-- omit in toc -->

## 2026-10-22 — S00 工程基线

- S00 完成：`pyproject.toml`、`agent_mini/__init__.py` + `agent_mini/version.py`（0.1.0）、`tests/unit/test_smoke.py`、README 安装/测试命令。
- 2026-10-22 修正：按 `DESIGN.md` §2.2 补齐 10 个子包与 23 个占位模块/文件，新增 `tests/unit/test_package_skeleton.py`；详见 ISSUE-017。
- 2026-10-22 打包修正：`systemdb/schema.sql` 通过 `package-data` 进入 wheel；wheel 含 35/35 个 `agent_mini/` 文件；新增 `tests/unit/test_packaging_config.py` 与结构/占位测试；详见 ISSUE-018。
- 验收：`pip install -e .` 成功；`pytest` 7 passed；`ruff check .` 零告警；`ruff format --check .` 37 files already formatted；`mypy agent_mini` 34 source files 无错误；`openspec validate --all --strict` 通过。
- 环境修复：Python 3.13 Scripts 下 `pytest.exe` 曾静默退出 1，已用同版本 force-reinstall 重建；`python -m pytest` 一直可用。详见 ISSUE-016。
- 未实现任何 Agent 业务模块；S01–S21 仍未开始。

## 2026-10-21 — 文档评审修订

- 截至 2026-10-21，仅有需求/设计/测试/计划文档，S00–S21 未开始；不得将测试设计或真实 API 计划表述为已通过。
- LLM 分别解析 content、可选 reasoning_content、tool_calls；公开 thought 是带 runtime_summary 来源标记的决策摘要。思考工具模式必要的 reasoning 只在同 session 私有协议字段回传，不进入公开 trace、日志或 MySQL。
- 每次 LLM 出站前，统一计数实际 messages、完整 tools Schema 与协议开销；计数/发送复用 tools_snapshot。保留最多 K 个历史完整轮次，最小集合仍超预算时本地 CONTEXT_TOO_LARGE/400，不继续请求模型。
- Redis 按完整轮次保留；todo 的 session_id 由可信执行上下文注入，模型不能覆盖。新增双窗口、工具追问和真实 API 验收用例，功能用例共 75 个，另有 1 个工程 smoke。
- 真实 API 001/002 是交付门禁；启用思考模式时还需 003。密钥只从 DEEPSEEK_API_KEY 读取，文档仅保留脱敏占位；本轮未保存或验证用户提供的密钥。
