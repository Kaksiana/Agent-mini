# TESTING

> **Agent-mini 测试文档**。规则见 `AGENT.md` §1（文档优先）、§2（TDD）与 §7（需求驱动开发）。
> 测试设计先于实现：本文件的用例清单是实现前必须完成的产物。
> 上位文档：`Docs/REQUIREMENT.md`（FR / NFR / AC）、`Docs/DESIGN.md`（模块与接口）。

| 项目 | 内容 |
| --- | --- |
| 版本 | v0.5（按 2026-10-21 调整单修订） |
| 日期 | 2026-10-21 |
| 状态 | 待评审 |
| 用例总数 | 56（L1×24、L2×6、L3×12、L4×8、L5×6） |

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
| L2 契约 | LLM 客户端与 HTTP 协议适配 | `respx` 拦截 | < 3s | 是 | `pytest -m contract` |
| L3 集成 | Redis / Mongo / MySQL / Runtime+Tool 联合 | fakeredis、mongomock、MySQL 替身；真实服务标记 `@integration` | 5–30s | 是（替身）/ 可选（真实） | `pytest -m integration` |
| L4 端到端 | HTTP 全链路 | 真实进程 + mock 模型服务 | 10–60s | 是 | `pytest -m e2e` |
| L5 非功能 | 性能、并发、安全、脱敏 | 视用例 | 10–120s | 否（`@slow`） | `pytest -m slow` |

> 测试命令以 `README.md` 记录的真实脚本为准（`AGENT.md` §2）。当前 `README.md` 尚未写入命令，属已知缺口，见 `Docs/ISSUE.md` 待登记项。

## 4. 每层测试用例清单

### 4.1 L1 单元测试

| 编号 | 前置条件 | 测试步骤 | 预期结果 |
| --- | --- | --- | --- |
| TC-L1-001 | calculator 已注册 | 调用 `calculator("(2+3)*4")` | 返回 `20`，`ok=True`，无异常 |
| TC-L1-002 | 同上 | 依次调用 `__import__('os').system('x')`、`eval('1')`、`open('a','w')` | 三者均 `ok=False`，`error_code=unsafe_expression`，无任何副作用 |
| TC-L1-003 | 同上 | 调用 `1/0`、`2+`、`"a"+1` | 均返回结构化错误（`division_by_zero` / `syntax_error` / `type_error`），进程不中断 |
| TC-L1-004 | 配置时区为 `Asia/Shanghai` | 调用 `time()` 不传参 | 返回 ISO8601 且偏移为 `+08:00` |
| TC-L1-005 | 同上 | 调用 `time(tz="UTC")`；再调用 `time(tz="Mars/Base")` | 前者返回 `+00:00`；后者 `ok=False`，`error_code=invalid_timezone` |
| TC-L1-006 | todo 存储为内存替身 | 依次 add("a")、add("b")、list()、complete(1)、list() | 第一次 list 返回 2 项；第二次返回 1 项且已完成项状态为 done |
| TC-L1-007 | 空注册表 | 用 `@tool` 注册一个 `echo` 工具后查询注册表 | `registry.get("echo")` 可查到，且 `registry.schemas()` 含该工具 |
| TC-L1-008 | 已注册 `echo(text: str)` | 调用 `to_json_schema()` | 输出合法 JSON Schema，`type=object`、含 `text` 且 `required` 正确 |
| TC-L1-009 | 已注册名为 `echo` 的工具 | 再次注册同名工具 | 抛 `DuplicateToolError`，注册表内容不变 |
| TC-L1-010 | `Sandbox(root=tmp/ws)` | 解析 `../../etc/passwd`、`a/../../../x` | 均抛 `SandboxViolation`，`error_code=path_escape` |
| TC-L1-011 | 同上；在 root 外创建符号链接 `link→/tmp/outside` | 解析 `link/secret.txt`；解析 `C:\Windows\win.ini` | 两者均被阻断（`path_escape` / `absolute_path`） |
| TC-L1-012 | 沙箱 `max_file_size=1024` | 写 2KB 内容；读 2KB 文件 | 两次均 `ok=False`，`error_code=file_too_large`，目标文件未被创建/修改 |
| TC-L1-013 | 构造 5 轮历史，token 远低于预算，K=10 | 调用 `ContextBuilder.build()` | 5 轮全部保留；system prompt 在首位；`payload.tokens_after` 有值且 > 0；`trim_reason` 为空 |
| TC-L1-014 | 历史 14 轮（含第 3 轮的 calculator 往返），K=10，token 预算充足 | 触发裁剪 | `dropped_rounds=4`、`rounds_after=10`、`trim_reason=rounds`；被丢弃轮次内部消息**成对完整移除**，不残留孤立 `tool` 消息 |
| TC-L1-015 | mock LLM：第 1 次返回 tool_calls，第 2 次返回文本 | 运行 `Agent.run()` | steps=2；messages 中 `assistant(tool_calls)` 与 `tool(call_id)` 成对且顺序正确；最终返回第 2 次文本 |
| TC-L1-016 | `max_steps=3`，mock LLM 永远返回 tool_calls | 运行 `Agent.run()` | 恰好 3 步后停止；`truncated=True`；返回明确提示文案；不抛异常 |
| TC-L1-017 | 无配置文件 / 必填项缺失 | 加载配置 | 抛 `ConfigError` 且消息含缺失字段名；合法配置可正常解析 |
| TC-L1-018 | 已注册 LLM 与 Memory 的假实现 | 从容器解析 `Agent` | 返回实例且其依赖为注入的假实现（同一次解析为同一单例） |
| TC-L1-019 | 构造各类异常 | 调用 `to_error_response()` | LlmAuth→`LLM_AUTH/502`、Sandbox→`SANDBOX_VIOLATION/400`、Input→`INVALID_INPUT/400`、未知→`INTERNAL/500` |
| TC-L1-020 | 设置 trace_id 后触发一次工具调用 | 捕获日志输出 | 所有日志行均为合法 JSON，含 `trace_id`、`event`、`duration_ms`，同一次请求内 `trace_id` 一致 |
| TC-L1-021 | search 未配置任何 provider | 调用 `search("今天天气")` | 返回 `ok=False`、`error_code=not_configured`；响应中不含任何伪造的搜索结果 |
| TC-L1-022 | `max_context_tokens=16000`、`max_output=1024`、余量 10% | 计算预算并统计固定中英文文本的 token | 预算 = 16000 − 1024 − 1600 = 13376；同一输入多次计数结果一致（可复现）；空消息计 0；`tiktoken` 缺失时降级为字符比例并记录 `token_counter.degraded` |
| TC-L1-023 | 14 轮，K=10，按轮次裁剪后 token 仍超预算 | 触发双触发裁剪 | 先按轮次丢 4 轮，再按 token 继续整轮丢弃至不超预算；`trim_reason=both`；最终 `tokens_after ≤ budget` |
| TC-L1-024 | mock LLM 第 1 步返回 tool_calls，第 2 步返回文本 | 运行 `Agent.run()` 并检查 `AgentResult.trace` | trace 长度=2；第 1 条含 `action.tool` 与 `observation` 摘要；第 2 条 `thought` 为最终文本；日志含 `event=react.step` |

### 4.2 L2 契约测试（LLM HTTP）

| 编号 | 前置条件 | 测试步骤 | 预期结果 |
| --- | --- | --- | --- |
| TC-L2-001 | `respx` 拦截 `POST /chat/completions` | 发起 `chat(messages, tools=[echo])` | 请求体含 `model`、`messages`、`tools[].function.name/parameters`；Header 含 `Authorization: Bearer ***`；路径与 base_url 拼接正确 |
| TC-L2-002 | 桩响应含 `tool_calls=[{id, function:{name, arguments}}]` | 调用 `chat()` | 解析出 1 个 `ToolCall`，`arguments` 已反序列化为 dict，`finish_reason=tool_calls` |
| TC-L2-003 | 桩响应为普通文本 + `usage` | 调用 `chat()` | `content` 正确；`tool_calls` 为空；`usage.prompt/completion/total` 与响应一致 |
| TC-L2-004 | 桩先返回 429、再返回 500、最后返回 200（`retry=3`） | 调用 `chat()` | 共 3 次请求；最终成功返回；退避间隔单调递增 |
| TC-L2-005 | 桩延迟超过 `timeout` | 调用 `chat()` | 抛 `LLMTimeout`，不无限等待，错误消息含超时秒数 |
| TC-L2-006 | 桩返回 400 与 401 | 分别调用 `chat()` | 抛 `LLMBadRequest` / `LLMAuthError`，且**不重试**（断言请求次数为 1） |

### 4.3 L3 集成测试

| 编号 | 前置条件 | 测试步骤 | 预期结果 |
| --- | --- | --- | --- |
| TC-L3-001 | fakeredis（或真实 Redis） | `append` 三条消息 → `get_recent(2)` | 返回后两条，顺序为时间正序，内容与写入一致 |
| TC-L3-002 | 同上，TTL 设为 1s | 写入后等待 TTL 过期再读 | 返回空集合，且不抛异常 |
| TC-L3-003 | mongomock（或真实 Mongo） | 写入 3 条消息后查询集合 | 集合内 3 条文档，字段 `session_id/role/content/created_at` 完整 |
| TC-L3-004 | 会话 A 有 5 条、会话 B 有 2 条 | 按 session A + 关键词过滤检索 | 只返回 A 中命中关键词的记录，`created_at` 倒序 |
| TC-L3-005 | 短时存储抛连接异常 | 运行一次完整对话 | 对话成功返回；日志含 `memory.degraded` 告警；进程未退出 |
| TC-L3-006 | mock LLM 返回 calculator 的 tool_call | 运行 `Agent.run()` | 真实执行 calculator；第 2 步 LLM 收到工具结果；`AgentResult.tool_traces` 有 1 条记录 |
| TC-L3-007 | 预置历史消息于 Memory | 调用 Context 组装 | 输出 messages = system + 历史片段 + 当前消息，顺序正确且无重复 |
| TC-L3-008 | 两个会话并发运行 | 并发执行 10 次请求 | 两个会话的消息窗口互不污染；各自结果与串行执行一致 |
| TC-L3-009 | 真实或替身 MySQL；启动时已登记 2 个模型、6 个工具 | 完成一次带工具调用的会话后查询五张表 | `models`=2 条、`tools`=6 条且 `enabled` 正确；`sessions` 1 条且 `status / last_active_at / message_count` 正确；`tool_invocations`、`request_metrics` 各有对应 trace_id 记录 |
| TC-L3-010 | MySQL 连接不可用 | 运行一次完整对话 | 对话正常返回；日志含 `systemdb.degraded`；系统信息未写入但进程未退出 |
| TC-L3-011 | 正常链路，记录各写回调用时序 | 发起一次请求并观察调用顺序 | Redis 写入发生在响应返回**之前**且为同步；Mongo 与 MySQL 写入发生在响应**之后**且为异步；三者都不阻塞响应 |
| TC-L3-012 | Mongo 与 MySQL 均抛连接异常 | 发起一次请求 | 响应正常返回 200；日志含 `memory.degraded` / `systemdb.degraded`；进程未退出 |

### 4.4 L4 端到端测试

| 编号 | 前置条件 | 测试步骤 | 预期结果 |
| --- | --- | --- | --- |
| TC-L4-001 | 启动 HTTP 服务，mock 模型返回纯文本 | `POST /chat {"message":"你好"}` | 200；响应 `reply` 非空；`steps=1`；无 traceback |
| TC-L4-002 | 同上，模型返回 calculator 调用 | `POST /chat {"message":"算下 2+2"}` | 200；`tool_calls` 记录 1 次；回复含结果 4 |
| TC-L4-003 | 启动 HTTP 服务 | `POST /chat`、`GET /healthz`，并构造 400/500 场景 | `/chat` 返回 200 且含 `session_id/reply/trace_id/usage`；未传 session_id 时自动生成并回传；`/healthz` 返回 200 且不含密钥；错误码映射正确 |
| TC-L4-004 | 同一 session_id 连续两次请求 | 第 1 轮说"我叫小明"，第 2 轮问"我叫什么" | 第 2 轮回复包含"小明"；两轮 trace_id 不同、session_id 相同 |
| TC-L4-005 | 预置 14 轮历史（窗口 10，token 预算较小） | 发起新问题 | 触发裁剪（日志 `context.trimmed`，`trim_reason` 为 rounds / tokens / both）；回复正常；最终 token 不超预算；无孤立 `tool` 消息 |
| TC-L4-006 | 配置文件缺失必填项 | 启动 HTTP 服务 | 进程启动失败；错误信息指出缺失字段；不产生堆栈噪声 |
| TC-L4-007 | mock 工具抛异常 | 发起请求 | 返回可读说明；进程存活；错误被分类记录 |
| TC-L4-008 | `max_steps=2`，模型持续要求工具 | 发起请求 | 返回"达到最大步数"类明确提示；HTTP 200 且标记 `truncated=true`；无死循环 |

### 4.5 L5 非功能测试

| 编号 | 前置条件 | 测试步骤 | 预期结果 |
| --- | --- | --- | --- |
| TC-L5-001 | mock 模型固定 50ms 返回 | 串行 100 次单轮问答，统计分位 | p95 ≤ 500ms（不含模型真实时延） |
| TC-L5-002 | 20 个独立会话 | 并发发起请求 | 成功率 100%；无跨会话内容串扰；内存无明显增长 |
| TC-L5-003 | 沙箱已就绪 | 跑安全用例集：`..`、绝对路径、符号链接、超长文件名、NTFS 流、大小写变体 | 全部被阻断；无一个越界成功 |
| TC-L5-004 | 配置含密钥 | 触发一次请求并采集全部日志与响应 | 日志与响应中均不含明文密钥（正则扫描 `sk-`、`Bearer `、`api_key`） |
| TC-L5-005 | 全量测试可运行 | 执行带覆盖率统计的测试命令 | 新增代码行覆盖率 ≥ 80%；未覆盖行有说明 |
| TC-L5-006 | `max_steps` 较大 | 运行 200 次请求 | 无文件句柄/连接泄漏（`ResourceWarning` 为 0） |

## 5. 测试环境与工具

### 5.1 运行环境

| 项目 | 要求 |
| --- | --- |
| Python | ≥ 3.11 |
| 操作系统 | Windows 10+ / Linux（CI 以 Linux 为准） |
| Redis | ≥ 7（仅 L3 真实服务用例需要） |
| MongoDB | ≥ 6（同上） |
| 模型 | 单元/集成测试全部使用 mock；仅手工验收时连真实 DeepSeek |

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
| `tiktoken` | token 计数（与生产实现同源）；不可用时相关用例标记 `skip` |
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

> 上述命令为设计约定。`AGENT.md` §2 要求"测试命令以 `README.md` 记录的真实脚本为准"；本次受文件白名单限制未更新 `README.md`，该缺口已列入 `Docs/ISSUE.md` 待登记项，落地阶段 0 时必须补齐。

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
- [ ] P0 与 P1 用例 100% 通过
- [ ] 新增代码覆盖率 ≥ 80%（NFR-TEST-01、AC-16）
- [ ] 沙箱安全用例集（TC-L5-003）全通过
- [ ] 日志脱敏用例（TC-L5-004）通过
- [ ] `ruff` 零告警、`mypy` 无新增错误
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
| AC-06 | TC-L4-004 |
| AC-07 | TC-L3-005 |
| AC-08 | TC-L1-014、TC-L4-005 |
| AC-09 | TC-L4-007 |
| AC-10 | TC-L1-016、TC-L4-008 |
| AC-11 | TC-L4-003、TC-L4-004 |
| AC-12 | TC-L1-020 |
| AC-13 | TC-L4-006 |
| AC-14 | TC-L5-004 |
| AC-15 | TC-L1-007 |
| AC-16 | TC-L5-005 |
| AC-17 | TC-L5-002 |
| AC-18 | 依赖清单评审（非自动化） |
| AC-19 | TC-L3-009、TC-L3-010 |
| AC-20 | TC-L1-022、TC-L1-023、TC-L4-005 |
| AC-21 | TC-L3-011、TC-L3-012 |
| AC-22 | TC-L1-024 |
