# S20 阶段代码产出独立评估报告

> 评估时间：2026-10-24 22:33（Asia/Shanghai）
> 评估基准：`a5cb568..7e887bb`；评估开始时 `main`、`HEAD`、`origin/main` 均为 `7e887bb`，工作区干净
> 评估方式：独立只读复核；除本报告与 `Docs/PROMPT.md` 外，不修改实现、测试、OpenSpec 或远程状态
> 结论：**不通过；S20 暂不可进入 S21**
> 缺陷汇总：**P0 0 项、P1 4 项、P2 6 项、P3 1 项**
> 历史结论：S20 首次评估，无前次结论需要对照

## 1. 评估范围与基准

本次以 S19 收口提交 `a5cb568` 至 S20 归档提交 `7e887bb` 为范围，共 22 个文件、`+261/-50`。重点复核：

- FR-OBS-03、FR-IF-04、NFR-OBS-01、AC-09、AC-12。
- TC-L1-019、TC-L4-007、TC-L4-012。
- OpenSpec `errors` 主规范与归档 change `2026-10-24-s20-error-handling`。
- `AgentError` 层级、LLMError/ToolError/Sandbox/Context 迁移、HTTP 统一处理器、4xx/5xx 日志级别，以及错误路径的 trace 关联。

基础映射已经成立：LLM 认证/超时/限流分别返回 502/408/429，`ContextTooLarge` 返回 400，未知异常返回 500，工具异常不会击穿进程，4xx/5xx 日志级别也有对应实现。现有测试为 **361 passed、2 skipped**，覆盖率 95.07%。

但 S20 的核心目标“任何异常都有明确出处”没有达成：所有错误响应日志的 `trace_id`/`session_id` 都是 `null`，因为请求 `finally` 先清空了 ContextVar，异常处理器之后才写日志；`ERROR_TYPES` 与真实抛出的 LLM/Tool 异常不是同一套类；TC-L1-019 要求的 `to_error_response()` 根本不存在，Sandbox/Input/Internal 的错误码也与文档不一致。静态门禁还因一个未使用 import 失败，新增 3 个单测未打 marker，阶段却已标记完成并归档。

## 2. 复核命令与结果

| 命令 / 检查 | 结果 |
| --- | --- |
| `git diff --stat a5cb568..7e887bb` | 22 files changed，261 insertions，50 deletions |
| `python -m pytest --cov=agent_mini --cov-report=term-missing -q` | **361 passed，2 skipped**，耗时 33.29s；总覆盖率 **95.07%**；`observability/errors.py` 100%，`interface/http.py` 94% |
| `python -m pytest -m unit --collect-only -q` | unit **204** collected（203 passed + 1 skipped），3 个 S20 新单测未标记、不在内 |
| `python -m pytest -m contract --collect-only -q` | contract **64** |
| `python -m pytest -m integration --collect-only -q` | integration **92** collected（91 passed + 1 skipped） |
| 未标记用例筛选 | `tests/unit/test_error_hierarchy.py` 的 **3** 个用例全部 unmarked |
| `python -m ruff check .` | **失败**：`tests/integration/test_http_interface.py:6` 未使用 `json` import |
| `python -m ruff format --check .` | 80 files already formatted |
| `python -m mypy agent_mini tests` | **77 source files，0 errors** |
| `openspec validate --specs --strict` / `--all --strict` | **20 passed，0 failed**；仅既有长 Requirement INFO |
| `git diff --check a5cb568..7e887bb` | 通过 |
| `python -m build` | sdist/wheel 构建成功；wheel 含 `observability/errors.py`（PowerShell 对 stderr 包装返回 1，构建输出本身成功） |
| `pip-audit .` | **No known vulnerabilities found**；S20 未新增依赖 |
| `python -m pip check` | 系统解释器报 `opentelemetry-api` 版本冲突；该包不在项目依赖中，S20 未改依赖，计为环境噪声，不计入阶段结论 |
| 错误映射与日志探针（假异常经 `create_app`） | 6 类错误均返回预期的 HTTP 状态；**每条错误日志的 `trace_id`、`session_id` 均为 `null`，`duration_ms` 恒为 0** |
| 校验失败探针（空白 message） | 返回 400 `INVALID_REQUEST`；应用日志 **0 条** |
| 真实 Agent + 故意失败工具探针 | 返回 200，`tool_calls=1`，trace 内 `error_code=tool_execution_error`；`tool.call` 日志只有 `ok=false`，无错误码 |
| `ContextTooLarge` 响应探针 | 400，响应体只有 `code/message/trace_id`，`steps/trace/truncated` 全部丢失 |
| 层级探针 | `llm.errors.LLMError` 不是 `observability.errors.LLMError`；它与 `tools.registry.ToolError` 都不匹配 `ERROR_TYPES` |

两个 skip 分别是未设置 `MYSQL_TEST_DSN` 的真实 MySQL 门控和 Windows 下 POSIX-only 文件用例，与 S20 无关。评估未调用 DeepSeek，未读取或输出 `.env` 中的真实密钥值；所有探针均使用假值。

## 3. 维度结论

| 维度 | 结论 | 证据 |
| --- | --- | --- |
| 功能完整性 | **不通过** | 错误路径日志无 trace；错误码契约与 TC-L1-019 不一致；`to_error_response()` 不存在 |
| 正确性 | **部分通过** | 4xx/5xx、408/429/502/400/500 状态正确；ContextTooLarge 丢 steps/trace/truncated；错误日志字段错误 |
| 可靠性 | **通过** | 工具异常返回 200 且进程存活；未知异常兜底 500；后台任务未回归 |
| 测试与覆盖率 | **不通过** | 95.07% 行覆盖但关键错误路径未被断言；3 个新单测 unmarked；ruff 门禁失败 |
| 可读性与架构 | **部分通过** | 模块短小、字段清晰；但两套 LLMError/ToolError 和无效 `ERROR_TYPES` 破坏“统一”语义 |
| 安全与依赖 | **通过** | 未新增依赖，`pip-audit` 无告警；错误日志未输出异常消息，暂未发现新的秘密泄漏路径 |
| 性能 | **部分通过** | 未见算法瓶颈；错误日志仍同步写 stderr，无并发/阻塞验证 |
| 工程与流程 | **不通过** | 实现提交先于文档/OpenSpec；PROMPT 只有摘要没有原始 Prompt；静态门禁失败仍归档 |
| 文档一致性 | **不通过** | README 仍停在 S00–S18；TESTING 日期/计数/TC-L1-019 未同步；ISSUE-024 状态自相矛盾 |

## 4. 分级问题清单

### P1-01 — 错误路径日志丢失 `trace_id`/`session_id`，NFR-OBS-01、AC-12 不成立

- **位置**：`agent_mini/interface/http.py:146-147`、`:174-183`、`:185-195`；`agent_mini/observability/logging.py:59-67`。
- **问题**：`chat` 的 `finally` 在异常继续向上抛之前执行 `reset_trace_context()`，把 ContextVar 清成 `None`；FastAPI 的 `agent_error`/`internal_error` 处理器随后才写日志，且 `extra` 中没有显式 `trace_id`/`session_id`。探针中 6 类错误（Sandbox、SandboxViolation、Input、LLMAuth、LLMTimeout、未知）全部输出 `trace_id=null`、`session_id=null`，而响应体的 `trace_id` 正常非空。
- **判定依据**：NFR-OBS-01 要求每个请求至少 1 条带 `trace_id` 的完成日志；AC-12 要求每次请求日志包含 `trace_id`；FR-OBS-02 要求 trace 贯穿请求。失败请求现在恰好没有可关联的日志，错误响应无法与日志、`SystemDB` 记录对齐。
- **建议方向**：在 `chat` 的 `except` 中先取 `request.state.trace_id`/`session_id` 写日志，再交给统一处理器；或在处理器中显式 `extra={"trace_id": request.state.trace_id, ...}`。补“格式化后的 JSON 行”断言，而不是只断言 `caplog` 记录字段。

### P1-02 — “统一”异常层级实际有两套 `LLMError`/`ToolError`，`ERROR_TYPES` 无法覆盖真实异常

- **位置**：`agent_mini/observability/errors.py:24-35,66-74`；`agent_mini/llm/errors.py:6-10`；`agent_mini/tools/registry.py:20-24`。
- **问题**：`observability/errors.py` 定义了 `LLMError`、`ToolError`，但 `llm/errors.py` 的 `LLMError` 和 `tools/registry.py` 的 `ToolError` 都直接继承 `AgentError`，不是这两个根的子类。探针确认：
  - `isinstance(LLMError("x"), observability.errors.LLMError) is False`；
  - `isinstance(LLMError("x"), ERROR_TYPES) is False`；
  - `isinstance(RegistryToolError("x"), ERROR_TYPES) is False`。
- **判定依据**：FR-OBS-03 要求统一异常分类体系；DESIGN §3.7 写的是单一 `AgentError → LLMError/ToolError/...` 链。现在 `ERROR_TYPES` 是一组“看起来像根、实际不被抛出”的类，未来任何按 `ERROR_TYPES` 做 `except`/映射的代码都会静默漏掉真实 LLM/Tool 异常。`tests/unit/test_error_hierarchy.py:21-26` 只检查它们都继承 `AgentError`，恰好掩盖了重复根。当前生产代码尚未消费 `ERROR_TYPES`，所以这不是一次已发生的请求失败，但它直接否定了 S20 的核心交付物“统一层级”，属于必须先修的架构缺陷。
- **建议方向**：只保留一套根类：让 `llm.errors.LLMError` 继承/别名 `observability.errors.LLMError`，`tools.registry.ToolError` 同理；为每个具体异常补 `issubclass`/`isinstance(…, ERROR_TYPES)` 断言，并删除永不抛出的重复类或明确其用途。

### P1-03 — 错误码契约与 TC-L1-019 不一致，`to_error_response()` 不存在

- **位置**：`Docs/TESTING.md:115`；`agent_mini/observability/errors.py:41,55`；`agent_mini/tools/sandbox.py:23-29`；`agent_mini/interface/http.py:182-195`；`tests/unit/test_error_hierarchy.py:32-34`；`tests/integration/test_http_interface.py:93-118`。
- **问题**：TC-L1-019 要求“调用 `to_error_response()`”，但仓库中没有任何 `to_error_response` 定义或调用。错误码也不同：
  - `SandboxViolation("path_escape", ...)` 返回 400/`path_escape`，文档要求 `SANDBOX_VIOLATION`；基类 `SandboxError` 的 code 又是 `SANDBOX_ERROR`；
  - `InputError` 返回 400/`INVALID_REQUEST`，文档要求 `INVALID_INPUT`；
  - 未知异常返回 500/`INTERNAL_ERROR`，文档要求 `INTERNAL`。
  新测试直接断言 `violation.code == "path_escape"`，等于把实现现状固化，而不是验证 TC-L1-019。
- **判定依据**：FR-IF-04、FR-OBS-03 与 AC 追溯要求“验收标准—测试用例—实现”一致；AGENT §7 明确没有 TC 映射的 AC 不得视为完成。当前 TC 既不可执行，也无法通过。
- **建议方向**：先冻结契约：HTTP 层使用稳定的家族错误码（如 `SANDBOX_VIOLATION`、`INVALID_INPUT`、`INTERNAL`），具体原因放 `error_code`/`details`；实现可单元测试的 `to_error_response()` 或等价错误对象构造器；同步修改 TESTING、实现与测试，并保留 LLM 子类的 502/408/429 映射断言。

### P1-04 — 静态门禁失败，新增单测未标记，完成声明与证据不符

- **位置**：`tests/integration/test_http_interface.py:6`；`tests/unit/test_error_hierarchy.py:1-47`；`Docs/TESTING.md:12`；OpenSpec 归档 `tasks.md` 2.1；`Docs/PLAN.md:359`。
- **问题**：`ruff check .` 因 S20 新增的 `import json` 未使用而失败；`test_error_hierarchy.py` 没有 `pytestmark = pytest.mark.unit`，3 个用例在 `-m unit` 下不会运行。TESTING 写“361（unit 203、contract 64、integration 91、unmarked 0）”，实际是 203 + 64 + 91 + 3 unmarked = 361，`unmarked 0` 不成立。OpenSpec tasks 2.1 已勾选“全量/静态/OpenSpec/wheel”，但静态门禁实际为红。
- **判定依据**：AGENT §2.2、§10 与 PLAN §5.1 DoD 要求提交前 ruff 零告警、全量测试通过；把失败门禁标记为完成会使后续 S21 继承不可信基线。
- **建议方向**：删除未使用 import；给新测试补 marker；修正 TESTING 计数；在 ruff/mypy/pytest/OpenSpec 全部重新通过前不要勾选 tasks、不要把阶段标为完成。

### P2-01 — 错误日志缺少异常出处与耗时；校验失败 400 完全没有日志

- **位置**：`agent_mini/interface/http.py:167-172,174-195`；`agent_mini/observability/logging.py:140-163`；归档 change `design.md` 第 10 行。
- **问题**：`agent.error`/`http.error` 只记录 `event`、`code`、恒为 0 的 `duration_ms`，没有异常类名、异常消息或堆栈；`JsonFormatter` 把 `exc_info` 归入标准字段直接排除，`RedactionFilter` 也不清洗 `exc_info`，归档 design 所称“日志 exc_info 经 Filter”没有落地。`RequestValidationError` 的 400 路径只返回响应，应用日志为 0 条。
- **判定依据**：FR-OBS-03 要求“任何异常都有明确出处”，FR-OBS-01 要求含耗时；当前 500 只能看到 `INTERNAL_ERROR`，无法定位异常来源；4xx 校验错误也没有 WARNING 记录。
- **建议方向**：记录脱敏后的异常类型与消息，必要时输出经 Filter 清洗的 `exc_info`；格式化器显式输出异常字段；校验处理器也写 `agent.error`/`http.validation_error`，并使用请求的 `trace_id`；`duration_ms` 从请求开始计时，不要硬编码 0。

### P2-02 — `ContextTooLarge` 响应丢失 `steps`/`trace`/`truncated`

- **位置**：`agent_mini/interface/http.py:182-183`；`agent_mini/context/window.py:30-32`；`Docs/DESIGN.md:352`。
- **问题**：`ContextTooLarge` 明确携带 `steps`、`trace`、`tool_traces`、`truncated=True`，统一处理器却只输出 `code/message/trace_id`。探针确认 400 响应没有这些字段，已发生的工具证据全部丢失。
- **判定依据**：DESIGN §3.5 要求上下文过大的错误响应带脱敏 trace、steps 和 `truncated=true`；TC-L4-012 只断言三个基础字段，不能替代该设计要求。
- **建议方向**：为 `ContextTooLarge` 增加可选的 `steps/trace/truncated` 响应字段，或在统一错误对象中保留子类附加数据；补“工具执行后仍超预算”的集成断言。该问题在 S18 已存在，S20 重写处理器时未顺手关闭，应作为遗留债处理。

### P2-03 — ISSUE-024 状态自相矛盾，正文含字面 `\n`

- **位置**：`Docs/ISSUE.md:284-285`。
- **问题**：第 284 行把 `\n- 状态：Resolved（2026-10-24）...` 作为普通文本写在一行，第 285 行仍是 `- 状态：Open`；标题却写“已关闭”。同一 issue 同时存在 Resolved 与 Open，且验证信息嵌在字面转义里。
- **判定依据**：AGENT §4 要求每条 issue 只有一个状态且 `Resolved` 有可复现验证；ISSUE 标题与 `MEMORY.md` 已把 ISSUE-024 当作关闭，实际正文仍保留 Open，无法一致追溯。
- **建议方向**：合并为单条 `- 状态：Resolved`，写清验证命令/结果；删除字面 `\n` 与重复状态行；如仍需保留历史，使用 Git 历史而不是双状态。

### P2-04 — 文档状态漂移：README、TESTING、包说明与设计清单

- **位置**：`README.md:3`；`Docs/TESTING.md:10-14`；`agent_mini/observability/__init__.py:1`；`tests/unit/test_package_skeleton.py:70-71`；`Docs/DESIGN.md` 版本记录。
- **问题**：README 仍称“当前完成 S00–S18”“不包含 S19–S21 治理/DI”，与 PLAN 的 S20 已完成矛盾；TESTING 版本已到 v0.24，日期仍是 2026-10-23，注释仍写“截至 S14…305 passed”；`observability` 包 docstring 仍是“待 S19–S20 落地”；`DESIGN_FILES` 中 `observability/errors.py` 重复出现两次；DESIGN 变更历史没有 S20 行。
- **判定依据**：AGENT §1 文档优先与 §7 需求驱动要求文档与实现同步；S19 报告已指出 README/TESTING 漂移，S20 仍未修复。
- **建议方向**：把 README 更新到 S20/S21 边界；修正 TESTING 日期、S14 注释与计数；更新包 docstring；去重设计清单；补 DESIGN 版本行。

### P2-05 — 新增测试未覆盖关键错误路径，且使用了生产不会抛出的类

- **位置**：`tests/integration/test_http_interface.py:93-118,246-259`；`tests/unit/test_error_hierarchy.py:21-34`。
- **问题**：HTTP 映射表使用 `observability.errors.SandboxError/ToolError`，但真实工具路径抛的是 `SandboxViolationError`，`ToolError` 也不会从注册表执行路径抛出；测试没有覆盖真实的 `SandboxViolation`、`ToolRegistrationError`、`RequestValidationError` 日志、5xx ERROR 级别、`trace_id/session_id/duration_ms` 字段。`test_error_log_code_matches_response_and_level` 只断言 `code` 与 `WARNING`，不足以发现 P1-01/P2-01。
- **判定依据**：TC-L1-019/TC-L4-007/TC-L4-012 要求的是错误对象与真实请求链路；高覆盖率不能替代对格式化 JSON 行、实际异常类和部分工具链的断言。
- **建议方向**：参数化使用实际抛出的异常类；以 `JsonFormatter` 输出字符串断言 `trace_id/session_id/duration_ms`；增加真实 Agent + 失败工具 + 校验失败三条集成用例；单独覆盖 5xx 的 ERROR 级别。

### P2-06 — Docs First、OpenSpec 先行、TDD 与 PROMPT 记录均不成立

- **位置**：提交顺序 `86430cd`/`a288aca`/`885b188`/`6bd767f` 早于 `539f434`/`7e887bb`；`Docs/PROMPT.md:2315-2318`；`openspec/changes/archive/2026-10-24-s20-error-handling/*`。
- **问题**：S20 的 OpenSpec change 只在最后的归档提交中出现，编码前没有 change；实现提交 `86430cd`、`a288aca` 没有对应测试，`885b188` 才补异常层级测试；PROMPT 的 S20 条目只有“执行摘要/验收”两行，没有原始 Prompt、任务目标、关键约束、人工修正与关联提交，按 AGENT §3 属于不合格；归档 tasks 在 ruff 失败时仍全部勾选。
- **判定依据**：AGENT §1.1、§2.2、§3.4–3.5、§6.1 与 PLAN §5.1 DoD。
- **建议方向**：后续阶段严格执行“change → 失败测试 → 实现 → 文档回填 → 门禁通过 → 归档”；PROMPT 按模板逐字保留原始 Prompt；如本轮确为追溯补记，应在 ISSUE 记录例外，而不是把 tasks 直接勾满。

### P3-01 — 生产日志配置为 pytest 保留 handler 特判，`LOGGER` 用 `__import__` 获取

- **位置**：`agent_mini/observability/logging.py:127-131`；`agent_mini/interface/http.py:34`。
- **问题**：`configure_logging` 通过 `handler.__class__.__module__.startswith("_pytest.")` 保留 pytest 私有 handler，把测试框架知识写进生产代码，且使测试环境与生产环境的 handler 清理行为不同；`LOGGER = __import__("logging").getLogger(...)` 绕过了正常的模块 import，降低可读性。
- **判定依据**：S19 已要求“日志所有权明确、只输出 JSON、幂等”；测试捕获应通过 fixture/注入完成，而不是生产代码给 `_pytest` 开洞。
- **建议方向**：让 `configure_logging` 只管理自己的 handler，测试用独立 logger/handler 或 `caplog`；如需保留外部 handler，提供显式参数；改为正常 `logging.getLogger`。

## 5. 需求—实现—测试追溯

| 需求 / 用例 | 实现 | 自动化证据 | 结论 |
| --- | --- | --- | --- |
| FR-OBS-03 / TC-L1-019 | `AgentError` + 7 个子类 + HTTP 处理器 | `tests/unit/test_error_hierarchy.py`、HTTP 映射参数化 | **不通过**：两套 LLM/Tool 根；Sandbox/Input/Internal 码不符；`to_error_response()` 不存在 |
| FR-IF-04 / TC-L4-003、TC-L4-012 | HTTP 状态映射 | 408/429/502/400/500 参数化用例 | **部分通过**：状态正确；错误码命名与响应附加字段未对齐 |
| NFR-OBS-01 / AC-12 | 错误日志 `agent.error`/`http.error` | 探针：6 类错误 trace 均为 null | **不通过**：失败请求没有可关联 trace 的日志 |
| FR-OBS-01 | JSON 固定字段、`duration_ms` | logging 单测 + 探针 | **部分通过**：JSON 合法；错误日志 `duration_ms` 恒 0 |
| AC-09 / TC-L4-007 | 工具异常转 `ToolResult` | 真实 Agent + 失败工具探针 | **通过**：200、进程存活、trace 有 `tool_execution_error`；日志未带错误码 |
| TC-L4-012 | `ContextTooLarge` 400 + trace | HTTP 映射 + 探针 | **部分通过**：400/code/trace_id 正确；steps/trace/truncated 丢失 |
| NFR-SEC-02 / AC-14 | 共享脱敏复用 | S19 安全 E2E 仍通过 | **通过（S20 范围）**：未新增泄漏路径；错误日志未输出异常消息 |
| NFR-TEST-01 / AC-16 | 覆盖率 | 95.07%，errors.py 100% | **数值通过、行为覆盖不足** |

## 6. 边界抽查

| 探针 | 结果 | 判定 |
| --- | --- | --- |
| 成功请求 JSON 日志 | `trace_id`/`session_id` 正常，`duration_ms` 非 0 | 通过 |
| LLMAuth 502 | 响应 502/`LLM_AUTH`；日志 ERROR/`LLM_AUTH`；trace null | 状态与级别通过，trace 失败 |
| LLMTimeout 408 | 响应 408/`LLM_TIMEOUT`；日志 WARNING | 通过（除 trace） |
| SandboxError 400 | 响应 400/`SANDBOX_ERROR`；日志 WARNING/`SANDBOX_ERROR` | 通过（除 trace） |
| SandboxViolation 400 | 响应 400/`path_escape`，文档要求 `SANDBOX_VIOLATION` | 契约失败 |
| InputError 400 | 响应 400/`INVALID_REQUEST`，文档要求 `INVALID_INPUT` | 契约失败 |
| 未知异常 500 | 响应 500/`INTERNAL_ERROR`，文档要求 `INTERNAL`；日志 ERROR、trace null、无堆栈 | 兜底通过，出处失败 |
| 空白 message 400 | 响应 400/`INVALID_REQUEST`；应用日志 0 条 | 日志失败 |
| 真实工具失败 | 响应 200、`tool_calls=1`、trace `tool_execution_error`；`tool.call` 无 error_code | 可靠性通过，分类日志不完整 |
| ContextTooLarge | 响应 400，只有 code/message/trace_id | 部分失败 |
| `ERROR_TYPES` 成员判定 | 实际 LLM/Tool 异常均不匹配 | 失败 |
| wheel 构建 | 含 `observability/errors.py` | 通过 |

## 7. 技术债与后续影响

1. 错误路径的 trace 关联必须先修；否则 S21 的配置错误、依赖装配错误仍然只能得到一条无请求标识的 ERROR 日志。
2. 两套异常根会继续扩散：S21 新增 `ConfigError` 时若沿用当前写法，`ERROR_TYPES`、`except` 与 HTTP 映射会进一步分叉。
3. 错误码命名需要在 S21 前冻结；`SANDBOX_VIOLATION`/`path_escape`、`INVALID_INPUT`/`INVALID_REQUEST`、`INTERNAL`/`INTERNAL_ERROR` 三组冲突会直接影响客户端契约与 TC 追溯。
4. 若补 `exc_info`，必须同时修改 `JsonFormatter` 与 `RedactionFilter`；当前格式化器丢弃标准 `exc_info`，过滤器也不清洗它，直接打开会形成新的泄密面。
5. `ContextTooLarge` 的部分 trace 丢失是 S18 遗留债，S20 的统一处理器把它泛化了；应在本阶段关闭，而不是留给 S21。
6. 错误耗时目前恒 0，无法用于 SLO；应在请求边界统一计时并写入成功/失败两条日志。

## 8. 总体门禁结论

**S20 不通过，暂不可进入 S21。**

进入 S21 前至少必须：

1. 关闭 P1-01：错误日志必须带本次请求的 `trace_id`/`session_id`，并用格式化 JSON 行断言。
2. 关闭 P1-02：合并 `LLMError`/`ToolError` 重复根，使 `ERROR_TYPES` 能覆盖实际异常。
3. 关闭 P1-03：冻结错误码契约，补齐 `to_error_response()` 或等价构造器，使 TC-L1-019 可执行且通过。
4. 关闭 P1-04：修复 ruff、给新单测打 marker、修正 TESTING 计数，重新跑全部门禁后才能标记完成。
5. 关闭 P2-01/P2-02：补异常出处、错误耗时、校验 400 日志，并保留 `ContextTooLarge` 的 steps/trace/truncated。
6. 修复 ISSUE-024、PROMPT、README、TESTING 的文档漂移，补齐 S20 的 OpenSpec/测试追溯。

P2/P3 中未阻断 S21 的条目可作为技术债，但 P1 必须全部关闭并复验。

## 9. 工作区状态与副作用

- 评估开始时工作区干净，`HEAD`、`main`、`origin/main` 均为 `7e887bb`；未提交、未推送、未修改远程状态。
- 按只读评估边界，仅新增本报告并向 `Docs/PROMPT.md` 追加本次原始 Prompt 与摘要。
- 全量测试、覆盖率、静态检查、OpenSpec、构建与探针更新了常规缓存和被忽略的 `build/`、`dist/`、`.coverage`、`.pytest_cache/`、`.ruff_cache/`、`.mypy_cache/`、`agent_mini.egg-info/`；未做破坏性清理。
- 探针临时脚本位于 `%TEMP%\s20_error_probe.py`、`%TEMP%\s20_tool_probe.py`，评估结束后删除；未创建后台服务或持久化配置。
- 未调用 DeepSeek API，未读取或输出 `.env` 中的真实密钥值；安全探针仅使用假值。
- `pip-audit .` 未发现已知漏洞；`pip check` 的系统级 `opentelemetry` 冲突与项目依赖无关，未作为 S20 缺陷。

## 11. 修复记录（2026-10-24）

| 报告项 | 修复 |
| --- | --- |
| P1-01 错误日志丢 trace | chat 保存 request.state trace/session/started；validation/agent/internal 日志显式携带；finally 仅清 ContextVar |
| P1-02 重复 LLMError/ToolError | `llm.errors.LLMError` 与 `tools.registry.ToolError` 改为 observability 别名，单一根 |
| P1-03 错误码/to_error_response | 冻结 `INVALID_INPUT`、`SANDBOX_VIOLATION`、`INTERNAL`；新增 `to_error_response()` 并接入 `_error` |
| P1-04 静态/marker | 删除未用 import；test_error_hierarchy 加 unit marker；unmarked 0 |
| P2-01 日志字段 | agent.error 增加 error_type/error_message/trace/session/duration；validation/500 也记录；未知异常 exc_info |
| P2-02 ContextTooLarge | 响应补 steps/trace/truncated |
| P2-03 ISSUE-024 | 删除字面 \\n 与重复 Open，单一 Resolved |
| P2-04 文档漂移 | README S20、TESTING 日期/计数、包 docstring、DESIGN 清单去重 |
| P2-05 测试 | 真实 SandboxViolation、RequestValidationError、未知异常、5xx ERROR、Context 证据 |

**复验**：364 passed、2 skipped；unit 207、contract 64、integration 93；覆盖率 **95.10%**；ruff/mypy/OpenSpec 通过。
