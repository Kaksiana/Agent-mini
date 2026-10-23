# MEMORY <!-- omit in toc -->

## 2026-10-23 — S07 calculator

- 新增 `CalculatorArgs` 与 `@tool("calculator")`；`ast.parse(mode="eval")` 白名单 Expression/BinOp/UnaryOp/Constant。
- 仅 `+ - * /`、取负/取正、括号；拒绝调用/属性/下标/Name/Lambda/推导式/比较/布尔/位运算/幂。
- 错误码：unsafe_expression、syntax_error、division_by_zero、type_error、expression_too_long、expression_too_deep、number_overflow。
- 阈值：200 字符、20 层 AST、1e12；bool 拒绝。
- 验收：154 passed、覆盖率 94.02%；unit 90、contract 64；mypy 53 files 0 errors。

## 2026-10-22 — S06 工具注册与 Schema

- 实现 `ToolResult`（ok/error 不变量）、`ToolContext` 预留、`ToolSpec`、`ToolRegistry`、`@tool`；Schema 由 pydantic 生成。
- 参数校验失败 `invalid_arguments`、未知 `unknown_tool`、handler 异常 `tool_execution_error`；同名 `DuplicateToolError`。
- `RegistryExecutor` 将注册表适配为 S04 `ToolExecutor`；Runtime 不导入具体工具；`ToolCallTrace.args` 改为只读映射。
- 验收：129 passed、覆盖率 95.25%；unit 65、contract 64；mypy 51 files 0 errors；ruff/format/openspec 通过。
- 边界：内置工具 S07–S12、沙箱 S10、会话注入 S09、Memory/Context S13–S18 未实现。

## 2026-10-22 — S05 循环安全阀

- 前置 `1a9bdb3`：`LoopPolicy` 参数化，默认不限制，S04 行为不变。
- 实现：`max_steps=8`、`deadline=120s`、`repeat_threshold=3`；`truncated`/`termination_reason` 与三条固定文案；deadline 使用 `asyncio.wait_for` 取消；重复按连续 `name+规范化 args`；中断时补齐同 call_id 的 tool 消息。
- 验收：112 passed、覆盖率 95.72%；unit 48、contract 64；`mypy agent_mini tests` 49 files 0 errors；ruff/format/openspec 通过。
- M1（S00–S05）已收口；S06 真实注册表、S13–S18 后续。

## 2026-10-22 — S04 ReAct 工具循环

- S04 完成：`Agent(llm_client, tool_executor)` 的 ReAct 循环；`ToolExecutor`/`ToolOutcome` Protocol；assistant/tool 按 call_id 顺序配对；未知工具/参数/Schema 错误回灌；S05 安全阀未实现。
- `AgentResult` 增量：`trace`、`tool_calls`、`tool_traces`；`ThoughtStep/ToolCallTrace` 冻结，`thought_source=runtime_summary`，reasoning 只在 assistant messages，公开 trace 脱敏并截断 200 字符。
- 验收：99 passed、覆盖率 96.17%；unit 35、contract 64；`mypy agent_mini tests` 48 files 0 errors；ruff/format/openspec 通过。
- 边界：S05 安全阀、S06 真实注册表、S13–S16 Memory/Context、S18 真实 API/HTTP 留后续。

## 2026-10-22 — S03 单轮直答

- S02 已完成：72 passed、覆盖率 95.69%；`LLMError` 临时根沿用至 S19，S20 迁移（ISSUE-024）；运行依赖下界债务 ISSUE-025，不阻塞 S03。
- Phase 1：方向 A 补 TC-L1-015A/B/C、DESIGN §3.2 字段表与 `Agent.run(user_input)` 签名；session_id 延后 S13；ISSUE-028 Resolved。
- Phase 2：`Agent(llm_client)` 构造器注入；`async run(user_input)` 发送单条 user 消息；冻结 `AgentResult(reply, steps, usage)`；`LLMError` 原样传播，意外 tool_calls 抛 `LLMProtocolError`。
- 验收：88 passed、覆盖率 96.03%；unit 24、contract 64；`mypy agent_mini tests` 47 files 0 errors；ruff/format/openspec 通过。
- 边界：不含工具循环（S04）、trace/truncated（S04/S05）、session_id/Memory（S13）、真实 API（S18）。

## 2026-10-22 — S02 错误处理与重试

- S02 完成：`llm/errors.py` 扩展鉴权/请求/超时/限流/服务端/连接错误；`llm/client.py` 支持 429/5xx 最多 3 次总请求、`0.5 * 2^(attempt-1)` 秒退避 + 0..0.1s 抖动；4xx、超时、协议错误不重试。
- 2026-10-22 评估修复：`RetryPolicy` 限制 1–3；`RetryEvent` 记录 attempt/status/delay；cap 后非递减；3xx/未知归协议错误；timeout 配置断言；S01 thinking+tools 回归。
- 2026-10-22 复验修复：默认路径始终写入 `retry_events`（`on_retry` 仅外部订阅）；异常测试使用具体类；thinking+tools 第二请求携带 assistant reasoning/tool_calls；README 门禁改为 `mypy agent_mini tests`，46 files 0 errors。
- 验收：全量 72 passed、覆盖率 95.69%；contract 64 passed、31.0s（目标 <60s）；`mypy agent_mini tests` 46 files 0 errors；ruff/format/openspec 通过。
- 边界：临时 `LLMError` 根继续使用至 S19，S20 迁移 `AgentError`（ISSUE-024/026/027）；真实 API 留 S18。

## 2026-10-22 — S01 模型接入

- S01 完成：`agent_mini/llm/{models,errors,client}.py`，支持 OpenAI Chat Completions 单轮请求、响应归一、工具参数严格解析与 thinking/reasoning 回传。
- 依赖：运行时 `httpx>=0.27`、`pydantic>=2.6`；dev `pytest-asyncio>=1.3,<1.4`、`pytest-cov>=7.1,<7.2`、`respx>=0.23,<0.24`、`ruff>=0.17,<0.18`、`mypy>=2.4,<2.5`。未调用真实 API，未读取 `DEEPSEEK_API_KEY`。
- 验收：L2 契约测试 29 个、全量 36 passed；ruff/format/mypy/openspec 通过。
- 2026-10-22 评估修复：非 object 顶层统一 `LLMProtocolError`；拒绝 `model/thinking` 覆盖与非法 tools；reasoning 仅 assistant；全量 50 passed、覆盖率 93%；dev 工具 pin 到 minor（ISSUE-021/022）。
- 2026-10-22 真实 API 测试：从被忽略的 `.env` 载入密钥并成功调用 `deepseek-chat`；返回 `OK`，usage 8/1/9，耗时约 1519ms；未记录密钥。正式 TC-LIVE-001 仍待 S18/S19（trace_id）。
- 边界：`ModelConfig` 为 S01 临时模型；非法工具参数以 `ToolCall.error_code=invalid_arguments` 返回；Runtime/ToolResult 与循环留 S04/S06，错误分类/重试留 S02（ISSUE-020）。

## 2026-10-22 — S00 工程基线

- S00 完成：`pyproject.toml`、`agent_mini/__init__.py` + `agent_mini/version.py`（0.1.0）、`tests/unit/test_smoke.py`、README 安装/测试命令。
- 2026-10-22 修正：按 `DESIGN.md` §2.2 补齐 10 个子包与 23 个占位模块/文件，新增 `tests/unit/test_package_skeleton.py`；详见 ISSUE-017。
- 2026-10-22 打包修正：`systemdb/schema.sql` 通过 `package-data` 进入 wheel；wheel 含 35/35 个 `agent_mini/` 文件；新增 `tests/unit/test_packaging_config.py` 与结构/占位测试；详见 ISSUE-018。
- 验收：`pip install -e .` 成功；`pytest` 7 passed；`ruff check .` 零告警；`ruff format --check .` 37 files already formatted；`mypy agent_mini` 34 source files 无错误；`openspec validate --all --strict` 通过。
- 环境修复：Python 3.13 Scripts 下 `pytest.exe` 曾静默退出 1，已用同版本 force-reinstall 重建；`python -m pytest` 一直可用。详见 ISSUE-016。
- S00 时未实现任何 Agent 业务模块；S01 起按阶段推进。

## 2026-10-21 — 文档评审修订

- 截至 2026-10-21，仅有需求/设计/测试/计划文档，S00–S21 未开始；不得将测试设计或真实 API 计划表述为已通过。
- LLM 分别解析 content、可选 reasoning_content、tool_calls；公开 thought 是带 runtime_summary 来源标记的决策摘要。思考工具模式必要的 reasoning 只在同 session 私有协议字段回传，不进入公开 trace、日志或 MySQL。
- 每次 LLM 出站前，统一计数实际 messages、完整 tools Schema 与协议开销；计数/发送复用 tools_snapshot。保留最多 K 个历史完整轮次，最小集合仍超预算时本地 CONTEXT_TOO_LARGE/400，不继续请求模型。
- Redis 按完整轮次保留；todo 的 session_id 由可信执行上下文注入，模型不能覆盖。新增双窗口、工具追问和真实 API 验收用例，功能用例共 75 个，另有 1 个工程 smoke。
- 真实 API 001/002 是交付门禁；启用思考模式时还需 003。密钥只从 DEEPSEEK_API_KEY 读取，文档仅保留脱敏占位；本轮未保存或验证用户提供的密钥。



