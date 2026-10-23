# MEMORY <!-- omit in toc -->

## 2026-10-23 — S13 Redis 短时窗口

- ShortTermMemory：完整轮次 JSON List、LTRIM 最近 10 轮、TTL 86400s，key 含 session_id。
- Agent.run 增量 session_id；AgentResult.session_id；loop 后、返回前 await 写回；Redis/序列化失败 memory.degraded 跳过。
- redis>=7.4,<8 运行依赖；fakeredis>=2.23,<3 dev。
- 验收：279 passed、覆盖率 95.76%；unit 198、contract 64、integration 17、unmarked 0；mypy 65 files 0 errors。

## 2026-10-23 — S12 search 与 M2

- 新增 SearchProvider Protocol/SearchResult/NullProvider；默认 NullProvider，模块级 configure_search_provider 注入。
- 未配置 not_configured，绝不伪造结果；5s 超时；异常/超时/畸形结构化；结果/摘要截断。
- M2（S06–S12）收口；验收 263 passed、覆盖率 97.04%；unit 198、contract 64、integration 17、unmarked 0；mypy 63 files 0 errors。
- ISSUE-039：TC-L3-006 实际为 calculator 集成，search 独立 E2E 留后续。

## 2026-10-23 — S11 write_file

- 复用 S10 Sandbox；父目录必须存在，默认不覆盖，overwrite=true 才替换。
- 同目录临时文件 + flush/fsync + os.replace；失败清理；内容超限/编码错误在临时文件前返回。
- 空内容合法；write→read 往返保留换行；错误码 file_exists/file_too_large/invalid_encoding/file_write_error 等。
- 验收：247 passed、覆盖率 97.06%；unit 183、contract 64；mypy 61 files 0 errors。

## 2026-10-23 — S10 沙箱与 read_file

- 新增 `Sandbox` 四步校验：绝对路径、空/`.`、NTFS 流、隐藏、超长、扩展名、resolve 越界。
- `ToolContext` 增量 `sandbox_root/max_file_size`；read_file 返回 JSON content/size/encoding；空文件正常、二进制/超限/解码失败结构化。
- 默认 1 MiB、扩展名白名单、路径 ≤240、禁止隐藏；TOCTOU 为 resolve 后 open，不宣称强原子性。
- 验收：224 passed、覆盖率 96.76%；unit 160、contract 64；mypy 59 files 0 errors。

## 2026-10-23 — S09 todo

- 新增 `TodoArgs`/`@tool("todo")`、`TodoStore` Protocol、进程内 `MemoryTodoStore`；S13 替换为 Memory。
- `ToolRegistry._invoke` 仅对声明 `context` 的 handler 注入 `ToolContext`；session_id 不在 Schema，伪造参数被 Registry 白名单拒绝。
- add/list/complete/delete；1-based 稳定 id，删除不重排；空列表返回空 items；错误码 missing_context/invalid_index/todo_not_found/empty_content/invalid_action。
- 验收：192 passed、覆盖率 96.34%；unit 128、contract 64；mypy 57 files 0 errors。

## 2026-10-23 — S08 time

- 新增 `TimeArgs(timezone)` 与 `@tool("time")`；默认 `DEFAULT_TIMEZONE="Asia/Shanghai"`。
- handler 兼容 `tz` 别名、`timezone` 优先；支持 `now_provider` 注入，不进入 Schema。
- 非法/空/大小写错误时区返回 `invalid_timezone`；输出 ISO8601 + 时区名。
- 验收：192 passed、覆盖率 96.34%；unit 128、contract 64；mypy 55 files 0 errors。
- ISSUE-034：timezone/tz 参数名冲突已用兼容设计闭环。

## 2026-10-23 — S07 calculator

- 新增 `CalculatorArgs` 与 `@tool("calculator")`；`ast.parse(mode="eval")` 白名单 Expression/BinOp/UnaryOp/Constant。
- 仅 `+ - * /`、取负/取正、括号；拒绝调用/属性/下标/Name/Lambda/推导式/比较/布尔/位运算/幂。
- 错误码：unsafe_expression、syntax_error、division_by_zero、type_error、expression_too_long、expression_too_deep、number_overflow。
- 阈值：200 字符、20 层 AST、1e12；bool 拒绝。
- 验收：164 passed、覆盖率 95.81%；unit 100、contract 64；mypy 53 files 0 errors。

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



















## 2026-10-23 — S13 收尾

- POSIX write_file 改为 dir_fd/O_DIRECTORY/O_NOFOLLOW/linkat/renameat；Windows 目录句柄锁定保留；POSIX 用例当前 Windows skip（ISSUE-040）。
- 新增冻结 StoredRound；Redis 读写经模型。
- 新增 TC-L3-015（Agent→Registry→search），关闭 ISSUE-039；TC-L3-006 保留 calculator。
- 279 passed、unit 198、contract 64、integration 17、unmarked 0；覆盖率 95.76%（ISSUE-041）。
- 提交噪声 21780eb 已登记 ISSUE-042，未改写历史。

## 2026-10-23 — S14 MongoDB 中期存储

- MidTermMemory：`conversation_rounds`，StoredRound + session_id/created_at；索引 `session_created_desc` 幂等。
- 检索强制 session、时间倒序、content 关键词；公开结果剥离 reasoning，include_private 保留。
- Agent 响应后 asyncio task 写 Mongo，失败/超时 memory.degraded。
- 依赖 pymongo>=4.9,<5；mongomock>=4.3,<5 dev。
- 验收：294 passed、1 skipped；unit 198、contract 64、integration 32；覆盖率 95.79%。


## 2026-10-23 — S15 Context 拼接与预算

- ContextPayload：messages/tools_snapshot/message_tokens/tool_schema_tokens/protocol_overhead_tokens/estimated_input_tokens/budget。
- TokenCounter：cl100k_base、规范 JSON、256 协议开销、10% 余量、字符降级并保留 Schema。
- ContextBuilder：system→工具摘要→中期摘要→StoredRound 历史→当前 user；不做裁剪。
- 依赖 tiktoken>=0.12,<0.13；测试注入假 encoder，不依赖在线下载。
- 验收：305 passed、1 skipped；unit 198、contract 64、integration 43；覆盖率 95.93%。

## 2026-10-23 — S16 双触发整轮裁剪

- window.fit_rounds：轮次 >10 或 token > 预算，整轮丢最旧并重计；trim_reason rounds/tokens/both。
- ContextPayload 增加 rounds_before/after、tokens_before/after、dropped_rounds、trim_reason。
- Agent/loop 每次 chat 前 fit；ContextTooLarge 不发请求。
- 验收：316 passed、1 skipped；unit 198、contract 64、integration 54；覆盖率 95.94%。

## 2026-10-24 — S17 MySQL 系统数据库

- 五表 schema.sql 幂等；SystemDBRepository upsert models/tools（不覆盖 enabled）、sessions、tool_invocations、request_metrics。
- Agent `with_system_db` 响应后异步 record_turn，`drain` 限时；失败 systemdb.degraded。
- 测试：SQLite 异步仓储 + MySQL schema 静态；真实 MySQL 环境缺失（ISSUE-043）。
- 验收：323 passed、1 skipped；unit 198、contract 64、integration 61；覆盖率 94.66%。

## 2026-10-24 — S18 HTTP API

- FastAPI /chat 字段、session UUID、/healthz 依赖状态；错误映射 400/408/429/502/500；脱敏。
- Agent trace_id 贯穿 ToolContext/SystemDB；LIVE Key 缺失未运行。
- 验收：344 passed、2 skipped；unit 198、contract 64、integration 82；覆盖率 94.96%。
