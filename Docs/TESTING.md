# TESTING <!-- omit in toc -->

> **Agent-mini 测试文档**。规则见 `AGENT.md` §1（文档优先）、§2（TDD）与 §7（需求驱动开发）。
> 测试设计先于实现：本文件的用例清单是实现前必须完成的产物。
> 上位文档：`Docs/REQUIREMENT.md`（FR / NFR / AC）、`Docs/DESIGN.md`（模块与接口）。

| 项目 | 内容 |
| --- | --- |
| 版本 | v0.25（S21 配置与 DI） |
| 日期 | 2026-10-24 |
| 状态 | 执行中（S00–S21 已实现；LIVE 条件未满足） |
| 用例总数 | 设计 79（L1×33、L2×10、L3×15、L4×12、L5×6、LIVE×3）；自动化测试 395（unit 223、contract 64、integration 103、live 3、unmarked 0；默认 8 skip） |

> 本文件同时记录测试设计与执行状态。截至 S21，S00–S21 共收集 395 个用例；Docker+LIVE 全量 394 passed、1 skipped，覆盖率 94.72%；默认 387 passed、8 skipped；Python 3.11 全量 393 passed、2 skipped。；L3–L5 与 LIVE 仍为设计项，未执行不表示通过。S00 工程 smoke 已纳入 unit，不再另计设计 TC。

---

## 1. 测试策略

### 1.1 总体原则

1. **测试先行**：每个阶段先写测试用例（红），再写实现（绿），最后重构；顺序不可颠倒。
2. **风险驱动**：优先级按"出错后果 × 出错概率"排布，沙箱、工具执行、循环收敛为最高风险区，用例密度最高。
3. **分层隔离**：单元测试不碰网络与真实存储；契约测试拦截 HTTP；集成测试才连真实 Redis/Mongo/MySQL（或对应替身）。
4. **可重复**：同一用例在任何机器、任何顺序下结果一致；禁止依赖执行顺序与系统时间（时间通过注入 `Clock` 或固定时区）。
5. **不伪造**：外部依赖不可用时，用例必须**跳过并标记**（`@pytest.mark.integration`），不得用假数据让测试"看起来通过"。
6. **一个用例一个断言主题**：失败时能直接定位问题，不做"大杂烩"断言。

### 1.2 测试类型与占比目标

| 类型 | 目标占比 | 说明 |
| --- | --- | --- |
| 单元测试（L1） | ~70% | 纯函数、算法、校验逻辑 |
| 契约测试（L2） | ~10% | 模型 HTTP 协议适配 |
| 集成测试（L3） | ~12% | Redis、Mongo、MySQL、Runtime + Tool 联合 |
| 端到端（L4） | ~6% | HTTP 全链路 |
| 非功能（L5） | ~2% | 性能、并发、安全、脱敏 |

> 上述占比是后续测试代码数量目标，不是本表设计用例数量的比例；真实 API 验收独立统计。

### 1.3 各阶段与测试的对应

每个开发阶段（见 `Docs/PLAN.md`）都必须：

1. 在本文件中找到对应用例（或新增用例并回写本文件）；
2. 先提交失败的测试；
3. 实现到全绿；
4. 在同一次提交中包含测试与实现（`AGENT.md` §2）。

## 2. TDD 落地方式

### 2.1 红 → 绿 → 重构

| 阶段 | 动作 | 完成标志 |
| --- | --- | --- |
| 红 | 写测试，运行，确认失败 | 失败原因与预期一致（断言失败，而非 import/语法错误） |
| 绿 | 写**最小**实现使测试通过 | 目标用例通过，已有用例不回归 |
| 重构 | 消除重复、改善命名、抽取接口 | 全量测试仍全绿 |

> **红证据规则**：测试必须在执行阶段因目标行为缺失而失败；import/collection/语法/夹具错误不计为 TC 级红。跨阶段 TC 必须在本文档拆出阶段覆盖边界。

### 2.2 测试代码规范

1. **目录镜像**：`agent_mini/tools/sandbox.py` → `tests/unit/tools/test_sandbox.py`。
2. **命名**：`test_<被测行为>_<场景>_<预期>`，例如 `test_resolve_rejects_parent_escape`。
3. **结构**：统一 `given / when / then` 三段，允许注释分隔。
4. **禁止**：mock 被测对象自身；为通过测试放宽断言；提交被 `skip`/`xfail` 掩盖的失败用例（`AGENT.md` §2 第 4 条）。
5. **替身边界**：仅对**外部**依赖打桩（HTTP → `respx`；Redis → `fakeredis`；Mongo → `mongomock`）。
6. **时间**：通过 `clock` 依赖注入固定时间，禁止在断言中写 `datetime.now()`。

### 2.3 缺陷修复流程

发现缺陷 → 先写**复现测试**（必须失败）→ 修复至通过 → 用例保留为回归用例 → 在 `Docs/ISSUE.md` 登记。

## 3. 测试分层

| 层级 | 范围 | 外部依赖 | 运行时间 | 默认执行 | 命令 |
| --- | --- | --- | --- | --- | --- |
| L1 单元 | 单模块纯逻辑：calculator、沙箱、预算裁剪、循环判定、配置校验、异常映射 | 无（全部替身） | < 5s | 是 | `pytest -m unit` |
| L2 契约 | LLM 客户端与 HTTP 协议适配 | `respx` 拦截 + 本地超时测试 | < 60s（含客户端/事件循环开销） | 是 | `pytest -m contract` |
| L3 集成 | Redis / Mongo / MySQL / Runtime+Tool 联合 | fakeredis、mongomock、MySQL 替身；真实服务标记 `@integration` | 5–30s | 是（替身）/ 可选（真实） | `pytest -m integration` |
| L4 端到端 | HTTP 全链路 | 真实进程 + mock 模型服务 | 10–60s | 是 | `pytest -m e2e` |
| L5 非功能 | 性能、并发、安全、脱敏 | 视用例 | 10–120s | 否（`@slow`） | `pytest -m slow` |
| LIVE 真实验收 | DeepSeek 直答、工具闭环、可选思考模式 | 真实 API + 密钥，有限调用次数 | 视模型时延 | 否，显式 opt-in；发布前必验 001/002 | 待实现后写入 README |

> 测试命令以 `README.md` 记录的真实脚本为准（`AGENT.md` §2）。S01/S02 已实现 L2 契约测试（`pytest -m contract`）；S03 已实现 L1 直答测试（`pytest -m unit`）；L3–L5 与 LIVE 仍待后续阶段。

## 4. 每层测试用例清单

### 4.1 L1 单元测试

| 编号 | 前置条件 | 测试步骤 | 预期结果 |
| --- | --- | --- | --- |
| TC-L1-001 | calculator 已注册 | 调用 `calculator("(2+3)*4")` | 返回 `20`，`ok=True`，无异常 |
| TC-L1-002 | 同上 | 依次调用 `__import__('os').system('x')`、`eval('1')`、`open('a','w')` | 三者均 `ok=False`，`error_code=unsafe_expression`，无任何副作用 |
| TC-L1-003 | 同上 | 调用 `1/0`、`2+`、`"a"+1` | 均返回结构化错误（`division_by_zero` / `syntax_error` / `type_error`），进程不中断 |
| TC-L1-004 | 配置时区为 `Asia/Shanghai` | 调用 `time()` 不传参 | 返回 ISO8601 且偏移为 `+08:00` |
| TC-L1-005 | 同上 | 调用 `time(tz="UTC")`；再调用 `time(tz="Mars/Base")` | 前者返回 `+00:00`；后者 `ok=False`，`error_code=invalid_timezone` |
| TC-L1-006 | todo 存储为内存替身 | 依次 add("a")、add("b")、list()、complete(1)、list() | 第一次 list 返回 2 项；第二次仍返回 2 项，第一项状态为 done |
| TC-L1-007 | 空注册表 | 用 `@tool` 注册一个 `echo` 工具后查询注册表 | `registry.get("echo")` 可查到，且 `registry.schemas()` 含该工具 |
| TC-L1-008 | 已注册 `echo(text: str)` | 调用 `to_json_schema()` | 输出合法 JSON Schema，`type=object`、含 `text` 且 `required` 正确 |
| TC-L1-009 | 已注册名为 `echo` 的工具 | 再次注册同名工具 | 抛 `DuplicateToolError`，注册表内容不变 |
| TC-L1-010 | `Sandbox(root=tmp/ws)` | 解析 `../../etc/passwd`、`a/../../../x` | 均抛 `SandboxViolation`，`error_code=path_escape` |
| TC-L1-011 | 同上；在 root 外创建符号链接 `link→/tmp/outside` | 解析 `link/secret.txt`；解析 `C:\Windows\win.ini` | 两者均被阻断（`path_escape` / `absolute_path`） |
| TC-L1-012 | 沙箱 `max_file_size=1024` | 写 2KB 内容；读 2KB 文件 | 两次均 `ok=False`，`error_code=file_too_large`，目标文件未被创建/修改 |
| TC-L1-013 | 构造 5 轮历史，token 远低于预算，K=10 | 调用 `ContextBuilder.build()` | 5 轮全部保留；system prompt 在首位；`payload.tokens_after` 有值且 > 0；`trim_reason` 为空 |
| TC-L1-014 | 历史 14 轮（含第 3 轮的 calculator 往返），K=10，token 预算充足 | 触发裁剪 | `dropped_rounds=4`、`rounds_after=10`、`trim_reason=rounds`；被丢弃轮次内部消息**成对完整移除**，不残留孤立 `tool` 消息 |
| TC-L1-015 | mock LLM：第 1 次返回 tool_calls，第 2 次返回文本 | 运行 `Agent.run()` | steps=2；messages 中 `assistant(tool_calls)` 与 `tool(call_id)` 成对且顺序正确；最终返回第 2 次文本 |
| TC-L1-015A | mock LLM 返回无 tool_calls 的文本 | 运行 `Agent.run(user_input)` | steps=1；`reply` 等于模型文本；`usage` 与响应同源；不出现工具调用路径 |
| TC-L1-015B | mock LLM 抛出 S01 的 `LLMEmptyResponseError` | 运行 `Agent.run(user_input)` | 同一异常原样传播，Agent 不吞、不转换 |
| TC-L1-015C | mock LLM 抛出 `LLMTimeoutError` 实例 | 运行 `Agent.run(user_input)` | 传播同一异常实例，类型与消息不变，不重试、不包装 |
| TC-L1-016 | `max_steps=3`，mock LLM 永远返回 tool_calls | 运行 `Agent.run()` | 恰好 3 步后停止；`truncated=True`；返回明确提示文案；不抛异常 |
| TC-L1-017 | 无配置文件 / 必填项缺失 | 加载配置 | 抛 `ConfigError` 且消息含缺失字段名；合法配置可正常解析 |
| TC-L1-018 | 已注册 LLM 与 Memory 的假实现 | 从容器解析 `Agent` | 返回实例且其依赖为注入的假实现（同一次解析为同一单例） |
| TC-L1-019 | 构造各类异常 | 调用 `to_error_response()` | LlmAuth→LLM_AUTH/502、Sandbox→SANDBOX_VIOLATION/400、Input→INVALID_INPUT/400、ContextTooLarge→CONTEXT_TOO_LARGE/400、协议/空输出/截断→对应 LLM_* 错误/502、未知→INTERNAL/500 |
| TC-L1-020 | 设置 trace_id 后触发一次工具调用 | 捕获日志输出 | 所有日志行均为合法 JSON，含 `trace_id`、`event`、`duration_ms`，同一次请求内 `trace_id` 一致 |
| TC-L1-021 | search 未配置任何 provider | 调用 `search("今天天气")` | 返回 `ok=False`、`error_code=not_configured`；响应中不含任何伪造的搜索结果 |
| TC-L1-022 | max_context_tokens=16000、max_output=1024、余量 10%、结构开销 256 | 对固定中英文 messages 与实际 tools JSON 调用 count_request；注入 tokenizer 不可用分支 | 预算=13376；总估算=message_tokens+tool_schema_tokens+256；同输入计数一致；messages/tools 均空时为 0；降级路径保留相同 Schema 输入和开销并记 token_counter.degraded |
| TC-L1-023 | 14 轮，K=10，按轮次裁剪后 token 仍超预算 | 触发双触发裁剪 | 先按轮次丢 4 轮，再按 token 继续整轮丢弃至不超预算；`trim_reason=both`；最终 `tokens_after ≤ budget` |
| TC-L1-024 | mock LLM 第 1 步返回 tool_calls，第 2 步返回文本，无 reasoning 字段 | 运行 Agent.run 并检查 trace 与日志 | trace 长度=2；decision 依次为 tool_call/final；thought_source=runtime_summary，reasoning_present=false；第 1 条含 tool_calls[0].tool/observation，第 2 条 tool_calls=[]；thought 不复制最终文本；日志含 react.step |
| TC-L1-025 | 固定 messages、含嵌套 properties/required/enum/$defs 的 tools；禁用一个工具 | 以可注入的确定性计数器比较空 tools、实际 tools、增加长描述/嵌套约束后的请求，并捕获发送体 | tools 的规范 JSON 全量参与计数；工具名称/描述/Schema 任一修改改变对应计数；禁用工具不发送不计数；HTTP tools 与计数快照一致；total 分项无重复；增加 Schema 可触发历史整轮裁剪 |
| TC-L1-026 | 无历史，分别构造超大用户消息、system 或 Schema，使最小请求超预算 | 调用 Context.fit；LLM 为可记录调用次数的替身 | CONTEXT_TOO_LARGE/400；LLM 调用数=0；不删除 tools 或截断当前消息规避校验；日志有 over_budget_after_trim |
| TC-L1-027 | 初次完整请求低于预算，工具返回超大结果，LLM 替身记录每次输入 | 分别构造“删历史后可发送”和“当前轮仍超限”场景运行循环 | 第一种整轮删除旧历史后调用第 2 次 LLM；第二种 LLM 调用数=1，返回 CONTEXT_TOO_LARGE、truncated=true；工具调用与结果保持配对；已有工具不重放 |
| TC-L1-028 | 注册 calculator，LLM 先请求未知工具或缺必填参数，再返回合法调用和最终答案 | 参数化执行各错误场景，记录 handler 副作用次数 | 未知工具为 unknown_tool，Schema 错误为 invalid_arguments；错误结果带原 call_id 回灌；无效调用不执行 handler；后续合法调用可收敛 |
| TC-L1-029 | 可注入单调时钟和 async timeout；工具替身可取消 | 分别模拟工具挂起超过 deadline、相同 name+规范化 args 连续返回 3 次 | 截止时间触发后取消挂起调用且不再请求模型；重复阈值触发停止；均返回明确提示与 truncated=true、steps 等于实际步骤；为未完成 call_id 补齐取消/超时 tool 结果，恢复后协议合法；不依赖长时间 sleep |
| TC-L1-030 | 启用思考工具模式，mock 响应带唯一私有 reasoning 标记；工具参数与结果含假密钥 | 检查公开 HTTP trace、日志、MySQL 事件、公开记忆召回与下一次请求体 | 私有 reasoning 仅在同 session 协议字段中回传；公开输出均不含标记原文或假密钥；thought_source 固定 runtime_summary，reasoning_present=true |

### 4.2 L2 契约测试（LLM HTTP）

| 编号 | 前置条件 | 测试步骤 | 预期结果 |
| --- | --- | --- | --- |
| TC-L2-001 | `respx` 拦截 `POST /chat/completions` | 发起 `chat(messages, tools=[echo])` | 请求体含 `model`、`messages`、`tools[].function.name/parameters`；Header 含 `Authorization: Bearer ***`；路径与 base_url 拼接正确 |
| TC-L2-002 | 桩响应含 `tool_calls=[{id, function:{name, arguments}}]` | 调用 `chat()` | 解析出 1 个 `ToolCall`，`arguments` 已反序列化为 dict，`finish_reason=tool_calls` |
| TC-L2-003 | 桩响应为普通文本 + `usage` | 调用 `chat()` | `content` 正确；`tool_calls` 为空；`usage.prompt/completion/total` 与响应一致 |
| TC-L2-004 | 桩先返回 429、再返回 500、最后返回 200（`retry=3`） | 调用 `chat()` | 共 3 次请求；最终成功返回；退避间隔单调递增 |
| TC-L2-005 | 桩延迟超过 `timeout` | 调用 `chat()` | 抛 `LLMTimeoutError`，不无限等待，错误消息含超时秒数 |
| TC-L2-006 | 桩返回 400 与 401 | 分别调用 `chat()` | 抛 `LLMBadRequestError` / `LLMAuthError`，且**不重试**（断言请求次数为 1） |
| TC-L2-007 | 参数化桩：reasoning_content 为缺失/null/字符串，content 与 tool_calls 合法 | 归一化响应；启用 thinking 且 tools 非空时发起下一次请求，再以新用户消息开始下一轮 | reasoning/content 独立提取，缺失/null 不补造；保留完整历史轮次的 reasoning 原字段在每次后续请求回传，包括无工具调用的 assistant；裁掉的轮次不回传；默认模式请求显式 thinking.disabled |
| TC-L2-008 | 参数化桩：无 choices、空列表、非法 message、重复/空调用 ID、非法调用结构、空答案、仅 reasoning、length/content_filter/未知终止原因 | 调用解析器，记录工具 handler 次数 | 结构错误/终止矛盾为 LLM_PROTOCOL_ERROR；无有效答案为 LLM_EMPTY_RESPONSE；截断为 LLM_OUTPUT_TRUNCATED；过滤为 LLM_OUTPUT_REJECTED；均 502、无工具执行、无无限重试 |
| TC-L2-009 | 合法调用结构，arguments 分别为破损 JSON、数组、字符串、重复键或 NaN | 解析后交 Runtime 回灌；模型下一步修正为合法 JSON object | 各无效调用返回 invalid_arguments 与原 call_id，不执行 handler，不使用 eval；修正后可正常执行；trace 记录失败与恢复 |
| TC-L2-010 | 桩第 1 步 content 与 2 个 tool_calls 共存，第 2 步返回最终文本 | 完成两步循环并捕获 messages、trace | 第 1 步不提前返回 content；先写 1 条 assistant，再按原顺序写 2 条有匹配 ID 的 tool；trace 长度=2，第 1 条工具列表长度=2；tool_calls 总次数=2 |

#### 4.2.1 S01 覆盖边界

| TC | S01 已覆盖 | 留待后续阶段 |
| --- | --- | --- |
| TC-L2-001 | 路径、Authorization、model/messages/tools/thinking 请求契约 | 真实 API 由 S18 LIVE-001/002 覆盖 |
| TC-L2-002 | tool_call ID/name/arguments/finish_reason 归一 | 工具执行由 S04/S06 覆盖 |
| TC-L2-003 | content、空 tool_calls、usage 三项 | 无 |
| TC-L2-007 | reasoning 缺失/null/字符串、默认 disabled、enabled 回传、assistant 角色校验 | Memory 恢复与裁剪由 S13/S16 覆盖 |
| TC-L2-008 | 结构错误、空答案、length/content_filter、非 object 顶层 | HTTP 502 映射、handler 次数与重试由 S02/S04 覆盖 |
| TC-L2-009 | 严格 JSON、非法参数 `invalid_arguments`、call_id 保留 | Runtime 回灌、ToolResult、trace 由 S04/S06 覆盖 |
| TC-L2-010 | content + 多 tool_calls 解析与顺序 | 两步循环、消息配对、trace 由 S04 覆盖 |

#### 4.2.2 S02 覆盖边界

| TC | S02 已覆盖 | 留待后续阶段 |
| --- | --- | --- |
| TC-L2-004 | 429/500/200 三次请求、两次退避、间隔单调递增、重试耗尽映射；`RetryPolicy` 1–3 上界与 `RetryEvent` attempt 记录 | 真实限流行为由 S18 LIVE 覆盖 |
| TC-L2-005 | `httpx.ReadTimeout` → `LLMTimeoutError`、单次请求、消息含超时秒数；底层 `httpx.AsyncClient.timeout` 与配置一致 | 真实网络超时由 S18 覆盖 |
| TC-L2-006 | 400/401/403 分类且仅 1 次请求；3xx/未知状态归协议错误；连接错误分类且不重试 | 对外 HTTP 状态映射由 S18 覆盖 |

#### 4.2.3 S03 覆盖边界

| TC | S03 已覆盖 | 留待后续阶段 |
| --- | --- | --- |
| TC-L1-015A | 单条 user 消息、一步直答、reply/steps/usage、无工具路径 | 会话、Memory、Context 由 S07/S13 覆盖 |
| TC-L1-015B | `LLMEmptyResponseError` 原样传播；None/空字符串/纯空白统一拒绝 | HTTP 错误映射由 S18 覆盖 |
| TC-L1-015C | `LLMTimeoutError` 原样传播、不重试/不包装 | Runtime 安全阀由 S05 覆盖；真实超时由 S18 覆盖 |

#### 4.2.4 S04 覆盖边界

| TC | S04 已覆盖 | 留待后续阶段 |
| --- | --- | --- |
| TC-L1-015 | 两步循环、assistant/tool 配对、最终 reply | S05 安全阀、S13 会话 |
| TC-L1-024 | ThoughtStep 字段、runtime_summary、reasoning_present、tool 列表 | `react.step` 日志由 S19 覆盖 |
| TC-L1-028 | 测试替身 unknown_tool/invalid_arguments 回灌、修正收敛 | 真实注册表/Schema 由 S06 覆盖 |
| TC-L1-030 | reasoning 仅随 assistant 消息回传、公开 trace 脱敏 | MySQL/日志由 S17/S19 覆盖 |
| TC-L2-009 | invalid_arguments 保留 call_id、不执行 handler、可修正 | 真实工具由 S06 覆盖 |
| TC-L2-010 | content+多 tool_calls 调用优先、顺序配对、总次数 | 真实 provider 由 S18 覆盖 |
| TC-L3-006 | 测试替身执行与 tool_traces | 真实 calculator/注册表由 S06/S18 覆盖 |
| TC-L4-010/011 | 不覆盖 | S18 真实 API/HTTP 回填 |

#### 4.2.5 S05 覆盖边界

| TC | S05 已覆盖 | 留待后续阶段 |
| --- | --- | --- |
| TC-L1-016 | max_steps=3 精确三步停止、truncated/termination_reason/固定文案 | HTTP 200 映射由 S18 覆盖 |
| TC-L1-029 | deadline 取消挂起工具、补齐同 call_id tool 消息、重复 3 次停止、可控时钟/短等待 | 真实网络取消与 S18 集成由 S18 覆盖 |
| TC-L4-008 | 不覆盖 | S18 HTTP 回填 |

#### 4.2.6 S06 覆盖边界

| 范围 | S06 已覆盖 | 留待后续阶段 |
| --- | --- | --- |
| TC-L1-007/008/009 | 注册/查找、pydantic Schema、重复注册拒绝 | 内置工具 S07–S12 |
| FR-TOOL-01 启停 | enabled_key 过滤 schemas/execute、禁用错误 | 配置加载/DI S21 |
| 执行边界 | 额外参数、unknown_tool、非 ToolResult、handler 异常、同步 to_thread | 具体工具错误语义 S07–S12 |
| 集成回填 | RegistryExecutor 驱动 Agent，call_id 配对保持 | 真实工具闭环 S07–S12 |

#### 4.2.7 S07 覆盖边界

| TC | S07 已覆盖 | 留待后续阶段 |
| --- | --- | --- |
| TC-L1-001 | `(2+3)*4=20`、`1+2*3`、`-3+2`、除法/浮点精度 | 真实模型触发 AC-02 由 S18 验收 |
| TC-L1-002 | Call/Name/Attribute/Subscript/Lambda/推导式/Compare/BoolOp/BitOp/Pow 均 unsafe_expression | 沙箱 S10 |
| TC-L1-003 | `1/0`/`2+`/`"a"+1` 结构化错误；bool/超长/过深/溢出 | 进程级无副作用由集成验证 |
| 注册 | `@tool("calculator")`、Schema required、Registry 执行 | 启停配置 S21 |

#### 4.2.8 S08 覆盖边界

| TC | S08 已覆盖 | 留待后续阶段 |
| --- | --- | --- |
| TC-L1-004 | 默认 Asia/Shanghai、固定 now_provider、+08:00 | 配置时区来源 S21 |
| TC-L1-005 | `tz="UTC"` +00:00；`Mars/Base`/空串/`utc`/非字符串 invalid_timezone | 真实系统时钟由集成验证 |
| 参数/Schema | 只公开 `timezone`；`tz` 为 handler 兼容别名 | 无 |
| 确定性 | now_provider 注入不进入 Schema | 无 |

#### 4.2.9 S09 覆盖边界

| TC | S09 已覆盖 | 留待后续阶段 |
| --- | --- | --- |
| TC-L1-006 | add a/b、list=2、complete(1)、list 第一项 done | 无 |
| TC-L3-013 | A/B 会话隔离；ToolContext 注入；伪造 session_id 被 Registry 拒绝；Schema 无 session_id | HTTP/真实 API 由 S18 回填 |
| TC-L4-009/010 | 不覆盖 | **S18** |
| 序号/空列表 | 1-based 稳定 id；删除不重排；空 items | 无 |

#### 4.2.10 S10 覆盖边界

| TC | S10 已覆盖 | 留待后续阶段 |
| --- | --- | --- |
| TC-L1-010 | `../../etc/passwd`、`a/../../../x.txt` → path_escape | 无 |
| TC-L1-011 | POSIX/Windows 绝对路径 → absolute_path；目录 junction/symlink 逃逸 → path_escape | 无 |
| TC-L1-012 | 2KB 文件 + max_file_size=1024 → file_too_large | write_file 由 S11 |
| TC-L5-003 | `..`、绝对路径、junction、超长路径、NTFS 流、大小写扩展名、隐藏路径 | 真实文件系统竞态由后续评估 |
| read_file | 空文件、元信息、二进制、解码失败、非法编码、缺失根、文件不存在 | S11 复用沙箱 |

#### 4.2.11 S11 覆盖边界

| TC | S11 已覆盖 | 留待后续阶段 |
| --- | --- | --- |
| TC-L1-012 写分支 | 2KB content + limit=1024 → file_too_large，目标未创建、无临时残留 | 无 |
| TC-L4-002 | 仅覆盖 calculator HTTP，不覆盖文件读写 | 文件 E2E 待 S18 新增 |
| 覆盖/原子 | 默认 file_exists；overwrite=true 替换；os.replace 失败清理 | 并发写 CAS 未承诺 |
| 往返 | write→read 空内容/换行一致 | 无 |
| 安全 | `../`、绝对路径、隐藏、symlink 目标逃逸、父目录缺失、编码错误 | Windows 设备名复用 S10 |

#### 4.2.12 S12 覆盖边界

| TC | S12 已覆盖 | 留待后续阶段 |
| --- | --- | --- |
| TC-L1-021 | NullProvider → not_configured；响应无伪造 URL/摘要 | 真实搜索 provider 待配置阶段 |
| TC-L3-006 | **实际定义是 calculator 集成，不覆盖 search**；已登记 ISSUE-039 | 独立 search E2E 待后续新增 |
| Provider | fake 透传、空结果成功、异常/timeout/畸形结构化 | 真实网络 provider 未实现 |
| 截断 | 结果超 limit、摘要超 500 → truncated=true | 无 |

#### 4.2.13 S13 覆盖边界

| TC | S13 已覆盖 | 留待后续阶段 |
| --- | --- | --- |
| TC-L3-001 | 3 轮写入、get_recent_rounds(2)、整轮 LTRIM、时间正序 | 无 |
| TC-L3-002 | ttl_seconds=1，过期后空集合 | 无 |
| TC-L3-005 | Redis 连接失败，Agent 正常返回，日志 memory.degraded | S17/S18 全链路 |
| TC-L3-014 | 工具配对、reasoning、跨会话隔离；Mongo/Context 部分 | **S14/S16** |
| TC-L3-011/012 | 不覆盖 | **S17/S18** |
| session_id | Agent.run 可选参数；AgentResult.session_id；不传不写 | HTTP S18 |

### 4.3 L3 集成测试

| 编号 | 前置条件 | 测试步骤 | 预期结果 |
| --- | --- | --- | --- |
| TC-L3-001 | fakeredis（或真实 Redis），每个 List 元素为完整轮次 | append 三轮 → get_recent_rounds(2) 并展开消息 | 返回后两轮，时间正序，轮内内容/调用 ID 完整且无孤立 tool 消息 |
| TC-L3-002 | 同上，TTL 设为 1s | 写入后等待 TTL 过期再读 | 返回空集合，且不抛异常 |
| TC-L3-003 | mongomock（或真实 Mongo） | 写入 1 个含 3 条消息的完整轮次后查询集合 | 集合内 1 个文档，字段 `session_id/round_id/messages/truncated/termination_reason/created_at` 完整 |
| TC-L3-004 | 会话 A 有 5 条、会话 B 有 2 条 | 按 session A + 关键词过滤检索 | 只返回 A 中命中关键词的记录，`created_at` 倒序 |
| TC-L3-005 | 短时存储抛连接异常 | 运行一次完整对话 | 对话成功返回；日志含 `memory.degraded` 告警；进程未退出 |
| TC-L3-006 | mock LLM 返回 calculator 的 tool_call | 运行 `Agent.run()` | 真实执行 calculator；第 2 步 LLM 收到工具结果；`AgentResult.tool_traces` 有 1 条记录 |
| TC-L3-007 | 预置历史消息于 Memory | 调用 Context 组装 | 输出 messages = system + 历史片段 + 当前消息，顺序正确且无重复 |
| TC-L3-008 | 两个会话并发运行 | 并发执行 10 次请求 | 两个会话的消息窗口互不污染；各自结果与串行执行一致 |
| TC-L3-009 | 真实或替身 MySQL；启动时已登记 2 个模型、6 个工具 | 完成一次带工具调用的会话后查询五张表 | `models`=2 条、`tools`=6 条且 `enabled` 正确；`sessions` 1 条且 `status / last_active_at / message_count` 正确；`tool_invocations`、`request_metrics` 各有对应 trace_id 记录 |
| TC-L3-010 | MySQL 连接不可用 | 运行一次完整对话 | 对话正常返回；日志含 `systemdb.degraded`；系统信息未写入但进程未退出 |
| TC-L3-011 | 正常链路，记录各写回调用时序 | 发起一次请求并观察调用顺序 | Redis 同步写入完成后才返回响应；Mongo/MySQL 后台写入不阻塞响应；Redis 等待在配置超时内，不能断言其完全不阻塞 |
| TC-L3-012 | Mongo 与 MySQL 均抛连接异常 | 发起一次请求 | 响应正常返回 200；日志含 `memory.degraded` / `systemdb.degraded`；进程未退出 |
| TC-L3-013 | 两个 session 各有独立 todo；工具执行上下文由服务端注入 session_id | A/B 分别 add/list/complete；构造模型参数试图把 A 的 session_id 改为 B | A 操作不影响 B；越权 session_id 参数被 Schema 拒绝；B 的待办与历史均不泄漏给 A |
| TC-L3-014 | Redis/Mongo 存在含多批工具往返与私有 reasoning 的完整轮次，窗口 K=2 | 写入 3 轮并按原 session 恢复；运行 Context 裁剪和公共关键词检索 | 仅最旧完整轮被移除；消息保留 tool_call_id 与必需 reasoning；无孤立 tool；公开检索不返回私有 reasoning；B session 无法读取 A 状态 |
| TC-L3-015 | 未配置 search provider；Agent 注入 RegistryExecutor | Agent.run 触发 search tool_call 后进入最终回复 | tool_traces 含 1 条 search、error_code=not_configured；无伪造结果；TC-L3-006 仍为 calculator |

### 4.4 L4 端到端测试

| 编号 | 前置条件 | 测试步骤 | 预期结果 |
| --- | --- | --- | --- |
| TC-L4-001 | 启动 HTTP 服务，mock 模型返回纯文本 | `POST /chat {"message":"你好"}` | 200；响应 `reply` 非空；`steps=1`；无 traceback |
| TC-L4-002 | 同上，模型返回 calculator 调用 | `POST /chat {"message":"算下 2+2"}` | 200；`tool_calls` 记录 1 次；回复含结果 4 |
| TC-L4-003 | 启动 HTTP 服务 | POST /chat、GET /healthz，并构造 400/500 场景 | /chat 返回 200，含 session_id/reply/steps/tool_calls/usage/trace/trace_id/truncated；tool_calls 为整数；未传 ID 自动生成；trace 符合 DESIGN §3.2.3 且不含原始 reasoning；健康检查不含密钥；错误码正确 |
| TC-L4-004 | 同一 session_id 连续两次请求 | 第 1 轮说"我叫小明"，第 2 轮问"我叫什么" | 第 2 轮回复包含"小明"；两轮 trace_id 不同、session_id 相同 |
| TC-L4-005 | 预置 14 轮历史（窗口 10，token 预算较小） | 发起新问题 | 触发裁剪（日志 `context.trimmed`，`trim_reason` 为 rounds / tokens / both）；回复正常；最终 token 不超预算；无孤立 `tool` 消息 |
| TC-L4-006 | 配置文件缺失必填项 | 启动 HTTP 服务 | 进程启动失败；错误信息指出缺失字段；不产生堆栈噪声 |
| TC-L4-007 | mock 工具抛异常 | 发起请求 | 返回可读说明；进程存活；错误被分类记录 |
| TC-L4-008 | `max_steps=2`，模型持续要求工具 | 发起请求 | 返回"达到最大步数"类明确提示；HTTP 200 且标记 `truncated=true`；无死循环 |
| TC-L4-009 | 同一用户两个窗口；mock LLM、search 测试 provider 返回明确标注的天气夹具；真实 todo | 窗口 A 新建 session 查天气并记“带伞”；B 新建另一 session 写周报并记“提交周报”；交替携原 ID 追问天气/周报并列出待办 | 两次新建 ID 不同；A 只恢复天气及带伞，B 只恢复周报及提交周报；A 完成待办不影响 B；保留逐次 trace_id；服务端不按用户合并 session |
| TC-L4-010 | 同一 session、mock LLM 决策、真实 calculator/todo | 分别执行“算 2+2”→“再乘 3”；“记待办提交周报”→“完成刚才那条” | 第二轮实际调用工具；calculator 得 12；todo 完成原条目；断言工具参数、状态变化和消息上下文，不能只断言回复措辞 |
| TC-L4-011 | mock LLM 按轮返回 calculator、todo、最终文本 | 用户要求“计算 2+2 并记入待办”，运行 HTTP 全链路 | 恰好 3 次 LLM 调用；calculator=4；todo 存在结果 4；每次 LLM 可见前次工具结果；trace 3 条且 decision=tool_call/tool_call/final |
| TC-L4-012 | 实际 tools Schema 占满预算，LLM 替身有计数器 | POST /chat 提交消息并收集错误响应/日志 | HTTP 400、code=CONTEXT_TOO_LARGE、trace_id 非空；LLM 请求次数=0；不把大 Schema 静默删除或降级为仅摘要发送 |

### 4.5 L5 非功能测试

| 编号 | 前置条件 | 测试步骤 | 预期结果 |
| --- | --- | --- | --- |
| TC-L5-001 | mock 模型固定 50ms 返回 | 串行 100 次单轮问答，统计分位 | p95 ≤ 500ms（不含模型真实时延） |
| TC-L5-002 | 20 个独立会话 | 并发发起请求 | 成功率 100%；无跨会话内容串扰；内存无明显增长 |
| TC-L5-003 | 沙箱已就绪 | 跑安全用例集：`..`、绝对路径、符号链接、超长文件名、NTFS 流、大小写变体 | 全部被阻断；无一个越界成功 |
| TC-L5-004 | 配置、模型响应与工具结果含唯一假密钥/私有 reasoning 标记 | 执行请求并扫描日志、响应、MySQL 审计及版本控制文件 | 无完整假密钥或私有 reasoning 原文泄漏；允许 api_key 字段名与 *** 占位符，不因字段名本身误报；真实 API Key 不进入测试夹具 |
| TC-L5-005 | 全量测试可运行 | 执行带覆盖率统计的测试命令 | 新增代码行覆盖率 ≥ 80%；未覆盖行有说明 |
| TC-L5-006 | `max_steps` 较大 | 运行 200 次请求 | 无文件句柄/连接泄漏（`ResourceWarning` 为 0） |

### 4.6 LIVE 真实 DeepSeek 验收

| 编号 | 前置条件 | 测试步骤 | 预期结果 |
| --- | --- | --- | --- |
| TC-LIVE-001 | 已实现客户端与 HTTP；显式 live 开关；DEEPSEEK_API_KEY 环境变量；配置实际可用模型 | 关闭工具，使用真实 API 发起“只回复 验收通过”，记录脱敏结果 | 非 mock 响应非空、steps=1、工具数=0，记录时间/模型/usage/trace_id 和断言结果；不得以桩响应代替 |
| TC-LIVE-002 | 同上，工具已注册，thinking 显式 disabled，tool_choice=auto | 自然语言请求用 calculator 计算 (17+25)*3，捕获真实请求与工具执行 trace | 模型自主给出合法 tool_call，真实 calculator 得 126，结果回灌后获得最终答案；至少 2 次真实 LLM 调用；记录 usage 与 trace_id |
| TC-LIVE-003 | 已实现思考模式；所选模型支持 thinking+tools；显式启用该模式 | 第 1 轮使用 calculator，第 2 轮带原 session 追问；检查每次出站协议字段和公开 trace | 若供应商返回 reasoning，则按官方要求回传保留历史并计入预算；公开输出无推理原文；模型不返回 reasoning 时记录“不提供该字段”，不能伪造；协议行为与契约测试一致 |

LIVE-001/002 为最终交付必验项；LIVE-003 仅在启用思考模式时必验。缺密钥/网络/可用模型时记录“未执行”及原因，整体真实 API 验收不得标记通过。默认测试运行不得自动联网或产生调用费用；显式执行有次数上限（每例最多 8 次模型请求，含重试）与总超时，失败保存脱敏错误，不保存 Authorization、原始响应或 reasoning 正文。

### 4.7 工程 smoke 检查（不计入 78 个功能用例）

| 编号 | 前置条件 | 测试步骤 | 预期结果 |
| --- | --- | --- | --- |
| TC-SMOKE-001 | S00 工程包已安装 | 导入 agent_mini 并读取版本 | 导入成功、版本非空；无网络与存储访问 |

## 5. 测试环境与工具

### 5.1 运行环境

| 项目 | 要求 |
| --- | --- |
| Python | ≥ 3.11 |
| 操作系统 | Windows 10+ / Linux（CI 以 Linux 为准） |
| Redis | ≥ 7（仅 L3 真实服务用例需要） |
| MongoDB | ≥ 6（同上） |
| 模型 | L1–L5 使用 mock；LIVE 显式连接真实 DeepSeek，模型名和密钥均由运行环境提供 |

### 5.2 工具与职责

| 工具 | 用途 |
| --- | --- |
| `pytest` | 用例执行、夹具、参数化 |
| `pytest-asyncio` | 异步用例 |
| `respx` | 拦截 `httpx` 请求，构造 LLM 各类响应 |
| `fakeredis` | 无依赖的 Redis 替身 |
| `mongomock` | 无依赖的 Mongo 替身 |
| `pytest-cov` | 覆盖率统计与阈值门禁 |
| `hypothesis` | calculator 表达式、沙箱路径的属性测试 |
| `tiktoken` | 完整请求的本地 token 估算；缺失分支必须测试字符比例降级，不得 skip 掩盖 |
| `ruff` | 静态检查（先于测试运行） |
| `mypy` | 类型检查（CI 阶段） |
| `docker compose` | 本地拉起真实 Redis/Mongo（可选） |

### 5.3 标记与命令（暂定）

| 标记 | 含义 | 说明 |
| --- | --- | --- |
| `unit` | 单元测试 | 默认执行 |
| `contract` | 契约测试 | 默认执行 |
| `integration` | 集成测试 | 无真实服务时用替身；连接真实服务的子集需显式 `--integration-real` |
| `e2e` | 端到端 | 默认执行 |
| `slow` | 非功能/耗时 | 默认跳过，CI 夜间跑 |
| `live` | 真实 API 验收 | 默认不选中；需显式开关与 DEEPSEEK_API_KEY，最终验收必须有 001/002 的实际通过记录 |

> L3–L5 与 LIVE 的标记、命令和 live 开关尚待实现；S18 落地时应把真实可执行命令与前置条件写入 README，当前缺口见 ISSUE-008。本轮未执行真实 API，也未持久化用户提供的密钥。

### 5.4 测试数据管理

1. 固定夹具放 `tests/fixtures/`（LLM 响应样本、超长对话样本）。
2. 敏感数据一律使用明显的假值（如 `sk-test-not-a-real-key`）。
3. 临时文件写入 `tmp_path`，测试结束自动清理，不污染仓库。
4. 禁止在测试中读写仓库外的真实路径（沙箱破坏类用例须在 `tmp_path` 内构造）。

## 6. 测试准入与准出标准

### 6.1 准入标准（开始编码前必须满足）

- [ ] 对应的需求条目（FR 编号）已在 `Docs/REQUIREMENT.md` 中存在且已评审
- [ ] 对应的设计要点（`Docs/DESIGN.md`）已明确接口与数据流
- [ ] 本文件中对应层级的测试用例已列出（编号、前置、步骤、预期齐全）
- [ ] 需要的夹具/替身已具备（respx 路由、fakeredis、tmp 沙箱）
- [ ] 失败测试已提交（红）

### 6.2 准出标准（合并/推送前必须满足）

- [ ] 全量测试通过（`pytest`），无失败、无 error
- [ ] wheel 构建成功，且 wheel 内 `agent_mini/` 与 `DESIGN.md` §2.2 清单一致（含 `schema.sql` 等 package-data）
- [ ] P0 与 P1 用例 100% 通过
- [ ] 新增代码覆盖率 ≥ 80%（NFR-TEST-01、AC-16）
- [ ] 沙箱安全用例集（TC-L5-003）全通过
- [ ] 日志脱敏用例（TC-L5-004）通过
- [ ] 最终交付时 LIVE-001/002 真实 API 验收通过；开启思考模式时 LIVE-003 也通过；缺少外部条件不能算验收成功
- [ ] `ruff` 零告警、`mypy agent_mini tests` 0 errors（S03 起正式门禁）
- [ ] 无 P0/P1 未解决缺陷
- [ ] `Docs/REQUIREMENT.md`、`Docs/DESIGN.md`、本文件与实现保持一致
- [ ] `Docs/ISSUE.md` 已记录本次新增/关闭的问题
- [ ] 提交信息符合 `AGENT.md` §5.2

### 6.3 缺陷分级

| 级别 | 定义 | 处理要求 |
| --- | --- | --- |
| P0 | 数据损坏、沙箱越界、密钥泄露、进程崩溃 | 立即修，阻塞发布 |
| P1 | 核心链路不可用（无法对话 / 工具不可调用 / 循环不收敛） | 本阶段内修复 |
| P2 | 非核心功能异常、错误提示不清晰 | 可延至下阶段，需登记 |
| P3 | 体验、文案、日志细节 | 记录待办 |

### 6.4 用例与验收标准映射

| 验收标准 | 测试用例 |
| --- | --- |
| AC-01 | TC-L4-003 |
| AC-02 | TC-L1-001、TC-L4-002 |
| AC-03 | TC-L1-002 |
| AC-04 | TC-L1-010、TC-L1-011、TC-L5-003 |
| AC-05 | TC-L1-007、TC-L1-008 |
| AC-06 | TC-L4-004、TC-L3-013、TC-L4-009、TC-L4-010 |
| AC-07 | TC-L3-005 |
| AC-08 | TC-L1-014、TC-L1-026、TC-L4-005、TC-L4-012 |
| AC-09 | TC-L4-007 |
| AC-10 | TC-L1-016、TC-L1-029、TC-L4-008 |
| AC-11 | TC-L4-003、TC-L4-004 |
| AC-12 | TC-L1-020 |
| AC-13 | TC-L4-006 |
| AC-14 | TC-L5-004 |
| AC-15 | TC-L1-007 |
| AC-16 | TC-L5-005 |
| AC-17 | TC-L5-002 |
| AC-18 | 依赖清单评审（非自动化） |
| AC-19 | TC-L3-009、TC-L3-010 |
| AC-20 | TC-L1-022、TC-L1-023、TC-L1-025、TC-L1-026、TC-L1-027、TC-L4-005、TC-L4-012 |
| AC-21 | TC-L3-011、TC-L3-012 |
| AC-22 | TC-L1-024、TC-L1-030、TC-L2-007、TC-L2-010、TC-L3-014、TC-LIVE-003 |
| AC-23 | TC-LIVE-001、TC-LIVE-002 |
