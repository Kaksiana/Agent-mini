# S19 阶段代码产出独立评估报告

> 评估时间：2026-10-24 02:36（Asia/Shanghai）
> 评估基准：`46aaf80..355599d`；评估开始时 `main`、`HEAD`、`origin/main` 均为 `355599d`
> 评估方式：独立只读复核；除本报告与 `Docs/PROMPT.md` 外，不修改实现、测试、OpenSpec 或远程状态
> 结论：**不通过；S19 暂不可进入 S20**
> 缺陷汇总：**P0 1 项、P1 5 项、P2 4 项、P3 0 项**

## 1. 评估范围与基准

本次以 S18 最后记录提交 `46aaf80` 至 S19 归档提交 `355599d` 为范围，共 15 个文件、`+376/-22`。重点复核：

- FR-OBS-01、FR-OBS-02、FR-OBS-04、NFR-SEC-02、AC-14。
- TC-L1-020、TC-L1-024、TC-L5-004、TC-L5-005。
- OpenSpec `observability` 主规范与归档 change `2026-10-24-s19-observability-logging`。
- JSON Lines 固定字段、ContextVar 跨异步边界、真实 ReAct 步骤/工具日志、HTTP 汇总指标、脱敏完整性与日志配置行为。

`JsonFormatter`、ContextVar、基础字段脱敏和 HTTP 成功汇总已实现，现有测试与静态门禁均通过。但测试只手工构造日志，没有穿过真实 Agent 工具链；运行时根本没有 `react.step` 日志，工具次数/token 指标未写入，失败请求也不记录。更严重的是，共享脱敏可被 Basic Authorization、多词秘密、嵌套列表和既有 handler 绕过，HTTP 响应与日志均存在明文泄漏路径。

## 2. 复核命令与结果

| 命令 / 检查 | 结果 |
| --- | --- |
| `git diff --stat 46aaf80..355599d` | 15 files changed，376 insertions，22 deletions |
| `python -m pytest tests/unit/test_observability_logging.py -q` | **4 passed** |
| `python -m pytest --cov=agent_mini --cov-report=term-missing -q` | **352 passed，2 skipped**；总覆盖率四舍五入为 **95%**；`observability/logging.py` **97%** |
| `python -m ruff check .` / `ruff format --check .` | All checks passed；77 files already formatted |
| `python -m mypy agent_mini tests` | **74 source files，0 errors** |
| `openspec validate --specs --strict` / `--all --strict` | **19 passed，0 failed**；仅既有长 Requirement INFO |
| `git diff --check 46aaf80..355599d` | **失败**：5 个文件存在 EOF 多空行 |
| `python -m build` / `python -m pip check` | sdist/wheel 构建成功；无依赖破损 |
| `pip-audit .` | **失败**：解析到 Starlette 0.52.1，共 10 行、5 个不同 PYSEC 公告 |
| 真实两步 Agent 工具链日志探针 | `steps=2`、`tool_calls=1`、`tokens=7`，但 **0 条日志** |
| HTTP 成功/失败日志探针 | 成功仅 1 条 `http.chat`；无 tool_calls/usage；Agent 异常返回 500 但 **0 条日志** |
| 安全边界探针 | Basic 凭据、多词密码、嵌套列表秘密、既有 handler 均可泄漏 |

两个 skip 分别是未设置 `MYSQL_TEST_DSN` 的真实 MySQL 门控和 Windows 下 POSIX-only 文件用例，与 S19 日志功能无关。评估未调用 DeepSeek，未读取或输出 `.env` 中的真实密钥值；所有安全探针均使用明确假值。

## 3. 维度结论

| 维度 | 结论 | 证据 |
| --- | --- | --- |
| 功能完整性 | **不通过** | FR-OBS-02 的真实步骤/工具日志与 FR-OBS-04 指标未实现 |
| 正确性 | **不通过** | 失败请求不记录；ContextVar 未恢复；日志配置可产生重复非 JSON 行 |
| 可靠性 | **不通过** | 预配置 handler 可绕过过滤；每请求重设全局日志级别 |
| 测试与覆盖率 | **不通过** | 97% 行覆盖仍漏出安全绕过和核心链路 0 日志；TC-L5-004 未按设计执行 |
| 可读性与架构 | **部分通过** | 模块短小、字段清晰；但“统一脱敏”仍有多套实现且 OpenSpec 缩窄上位需求 |
| 安全与依赖 | **不通过** | 可复现日志/响应秘密泄漏；pip-audit 门禁失败 |
| 性能 | **部分通过** | 未见算法瓶颈；同步 StreamHandler 位于请求路径，尚无吞吐/阻塞验证 |
| 工程与流程 | **不通过** | 实现先于 OpenSpec/文档，归档过早，diff-check 与依赖审计失败仍标记完成 |

## 4. 分级问题清单

### P0-01 — 统一脱敏仍存在多条明文泄漏路径

- **位置**：`agent_mini/observability/logging.py:21-32,68-104,111-120`；`agent_mini/interface/http.py:185-188`；`tests/unit/test_observability_logging.py:64-101`。
- **问题**：文本正则仅完整处理 Bearer 和无空格键值。`Authorization: Basic <credential>` 只替换 `Basic`，凭据本体保留；带空格的 JSON password/api_key 只替换第一个词；`_sanitize_field` 递归 dict 却不递归 list/tuple；`configure_logging` 只给新 handler 加 filter，已存在的 handler 会在过滤前输出原始记录。
- **复现证据**：HTTP reply 中 `Authorization: Basic ZmFrZTpzZWNyZXQ=` 变为 `*** ZmFrZTpzZWNyZXQ=`，`{"password": "p@ss word"}` 变为 `{*** word"}`；`details=[{"api_key":"plain-secret"}]` 原样进入 JSON 日志；预配置 handler 输出 `password=plain sentinel`。
- **根因**：测试仅覆盖 Bearer、`sk-*`、单词值和顶层字段，且直接给测试 handler 安装 filter，没有覆盖真实日志拓扑与递归容器。
- **判定依据**：违反 NFR-SEC-02、AC-14、TC-L5-004 及 observability OpenSpec 的 MUST；凭据可经公开 HTTP 响应或日志外泄，属于发布阻断安全问题。
- **建议方向**：以结构化递归净化为主，覆盖 Mapping/Sequence/Pydantic/异常对象；Authorization/Cookie 按完整字段值处理；安装时接管或验证全部有效 handler，并以原始秘密值“不出现”为断言。

### P1-01 — 真实 ReAct 步骤与工具调用没有日志，trace_id 无从“贯穿”

- **位置**：`agent_mini/runtime/loop.py:109-171,183-209`；`agent_mini/interface/http.py:106-126`；`tests/unit/test_observability_logging.py:36-61`。
- **问题**：Runtime 没有任何日志调用，`react.step` 只出现在测试手工 `logger.info()` 中。真实两步 Agent 调用工具后得到完整 result，却产生 0 条运行时日志；经 HTTP 只在全部成功后写一条汇总。
- **判定依据**：FR-OBS-02 要求 trace_id 贯穿每个步骤和工具调用；TC-L1-020 明确要求“触发一次工具调用并捕获所有日志”。当前测试验证的是 formatter，不是需求链路。
- **建议方向**：在步骤完成与每个工具结果形成处记录结构化事件，复用 ContextVar trace/session；集成测试必须运行真实 Agent + 工具替身并逐行校验同一 trace_id。

### P1-02 — FR-OBS-04 指标未落地，异常请求完全不可观测

- **位置**：`agent_mini/interface/http.py:107-126,146-180`。
- **问题**：`http.chat` 仅含总 steps 和 duration_ms，没有 tool_calls、prompt/completion/total tokens；Agent 抛异常时控制流在日志语句前退出，500 响应没有任何应用日志。验证探针中成功结果为 steps=2/tool_calls=1/tokens=7，日志却只保留 step=2；失败结果日志数为 0。
- **判定依据**：FR-OBS-04 明确要求输出每轮步数、工具调用次数和 token 用量；可观测系统也不能只记录成功请求。
- **建议方向**：在 try/except/finally 或统一中间件边界记录成功/失败事件，携带状态、错误码、steps/tool_calls/usage/duration，且不记录 prompt/reasoning 原文。

### P1-03 — `configure_logging` 会产生重复非 JSON 输出

- **位置**：`agent_mini/observability/logging.py:107-120`。
- **问题**：logger 保持 `propagate=True`。当宿主/root 已有 handler 时，同一记录先输出项目 JSON，再向 root 输出一条普通文本；探针稳定得到 `root_output=plain-event` 且无法 `json.loads`。已有 `agent_mini` handler 还会在安全 handler 之前看到未脱敏记录。
- **判定依据**：OpenSpec 要求每条 `agent_mini` 日志均为 JSON 行，当前配置不具备该保证。
- **建议方向**：明确日志所有权：禁用传播并管理项目 handler，或给全部有效输出路径安装同一 formatter/filter；补 root/既有 handler/重复初始化测试。

### P1-04 — TC-L5-004 被缩减为单条内存日志测试

- **位置**：`Docs/TESTING.md:312`；`tests/unit/test_observability_logging.py:64-101`。
- **问题**：设计要求执行请求后扫描日志、响应、MySQL 审计与版本控制文件；现有测试只构造两个 LogRecord，不经过 HTTP、Agent、工具、SystemDB，也不扫描仓库。P0-01 的四种绕过因此全部漏检。
- **建议方向**：建立唯一假密钥和私有 reasoning 哨兵的端到端安全用例，分别进入配置、模型 reply/reasoning、工具参数/结果、异常与嵌套结构，扫描所有外部可见面。

### P1-05 — 依赖安全门禁继续失败，ISSUE-045 记录与实际结果不一致

- **位置**：`pyproject.toml:11-21`；`Docs/ISSUE.md:601-606`。
- **问题**：当前 `pip-audit .` 报 Starlette 0.52.1 的 10 行、5 个不同公告；ISSUE-045 却记录 certifi/urllib3 共 4 项，无法复现当前项目解析结果。S19 未新增依赖，但在前置阶段安全门禁仍开放时被归档为完成。
- **建议方向**：固定并记录项目级审计命令、Python/索引环境与解析结果；升级兼容依赖或给出逐项风险接受，不得用环境级扫描替代项目声明扫描。

### P2-01 — 请求 ContextVar 设置后从不恢复

- **位置**：`agent_mini/observability/logging.py:12-44`；`agent_mini/interface/http.py:107-126`。
- **问题**：`set_trace_context` 丢弃 ContextVar token，HTTP handler 没有 finally reset。ASGITransport 同任务探针在响应后仍读到该请求 trace_id，后续同上下文创建的无关任务会继承陈旧 trace/session。
- **建议方向**：提供作用域上下文管理器或返回 token，在请求 finally 中逆序 reset；明确哪些后台任务应在 reset 前创建并继承请求上下文。

### P2-02 — 每个成功请求重新配置全局日志并覆盖运行级别

- **位置**：`agent_mini/interface/http.py:98,118`；`agent_mini/observability/logging.py:111-120`。
- **问题**：应用创建时已配置日志，成功请求又调用 `configure_logging()`；该函数每次执行 `logger.setLevel(level)`，会把运维预设的 DEBUG/WARNING 恢复为默认 INFO。
- **建议方向**：启动期配置一次；请求路径只获取模块 logger，不修改全局配置。

### P2-03 — OpenSpec 缩窄上位范围并在关键验收缺失时归档

- **位置**：S19 proposal/design/spec/tasks；提交 `2ceb09f`、`21ba4e9`、`355599d`。
- **问题**：S19 PLAN 明确对应 FR-OBS-01/02/04，但 OpenSpec 只写 JSON/trace 与脱敏，没有 FR-OBS-04 指标、失败事件或真实工具步骤场景；tasks 仍全部勾选。实现提交先于文档与 OpenSpec，未体现 Docs First/TDD，提交描述也未使用中文。
- **建议方向**：恢复上位需求追溯，重新打开 change 和未完成 tasks；用真实失败测试证明工具链日志、指标及安全扫描后再归档。

### P2-04 — 文档与代码状态漂移

- **位置**：`README.md:3`、`Docs/TESTING.md:9-12`、`agent_mini/observability/__init__.py:1`、S19 diff。
- **问题**：README 仍称只完成 S00–S18；TESTING 自动化总数仍写 338；observability 包 docstring 仍称等待 S19–S20；阶段 diff 有 5 处 EOF 多空行，DESIGN 中 S19 的 §3.7.1 被放在 §3.9.1 之后。
- **建议方向**：以实际命令结果统一 README/TESTING/MEMORY/PLAN，修正文档结构并把 diff-check 纳入提交门禁。

## 5. 需求—实现—测试追溯

| 需求 / 用例 | 实现 | 自动化证据 | 结论 |
| --- | --- | --- | --- |
| FR-OBS-01 / TC-L1-020 | JsonFormatter 固定字段 | 手工 logger 的 JSON 单测 | **部分满足**：字段通过；真实链路与 root 输出不满足全 JSON |
| FR-OBS-02 / TC-L1-020 | HTTP 设置 ContextVar | create_task 继承单测 | **不满足**：真实步骤/工具没有日志，无法验证贯穿 |
| FR-OBS-04 / TC-L4-003 | HTTP 记录 step/duration | 无指标断言 | **不满足**：缺 tool_calls 和 token usage，错误请求无事件 |
| NFR-SEC-02 / AC-14 / TC-L5-004 | RedactionFilter + redact_text | Bearer/sk/顶层字段单测 | **不满足**：四类明文绕过可复现；未扫描响应/MySQL/仓库 |
| TC-L1-024 | ThoughtStep 轨迹 | 既有 Runtime trace 测试 | **部分满足**：结果对象存在，`react.step` 日志不存在 |
| TC-L5-005 | 覆盖率 | 全量覆盖率 95%，logging.py 97% | **数值通过、行为不足** |

## 6. 边界抽查

| 探针 | 结果 | 判定 |
| --- | --- | --- |
| 固定字段 JSON | 7 个固定字段齐全，可解析 | 组件级通过 |
| ContextVar 跨 `create_task` | 子任务读取同一 trace | 通过 |
| 真实 Agent 两步工具调用 | 结果 steps=2/tool_calls=1/tokens=7；日志 0 条 | 失败 |
| HTTP 成功请求 | 仅 `http.chat`，缺 tool_calls/usage | 失败 |
| HTTP Agent 异常 | 返回 500；应用日志 0 条 | 失败 |
| Basic Authorization | 凭据后半段原样保留 | 严重失败 |
| JSON 多词 password | 后续词原样保留 | 严重失败 |
| 嵌套 list/dict api_key | 完整秘密进入 JSON 日志 | 严重失败 |
| 已有 handler + configure | 已有 handler 先输出原始秘密 | 严重失败 |
| root handler + configure | 同一事件额外输出非 JSON 文本 | 失败 |
| 请求结束后读取 ContextVar | 仍为刚完成请求 trace_id | 失败 |
| wheel 构建 | 成功包含 observability/logging.py | 通过 |

## 7. 技术债与后续影响

1. S20 若直接接入统一异常响应，失败请求仍可能没有日志，错误对象也无法关联步骤/工具证据。
2. Runtime 与 Observability 仍分别维护秘密规则；字段集合已经漂移，继续扩展会重复出现绕过。
3. 若补齐每步日志但继续同步写 stderr，高并发下可能阻塞事件循环；应先确定队列化/异步落盘策略和背压边界。
4. ContextVar 必须建立明确请求作用域，否则测试、嵌入式 ASGI 或长寿命协程中的 trace 会污染后续任务。
5. 当前依赖审计记录不可复现，后续发布无法判断风险是否真实关闭。

## 8. 总体门禁结论

**S19 不通过，暂不可进入 S20。**

进入 S20 前至少必须：

1. 关闭 P0-01，使用结构化递归脱敏并覆盖全部有效 handler 与 HTTP 响应。
2. 在真实 ReAct 步骤和工具执行边界写日志，以集成测试证明单次请求 trace_id 一致。
3. 补齐 steps/tool_calls/token usage/失败状态指标，异常请求也必须产生安全日志。
4. 让日志配置只输出 JSON、幂等且不覆盖运行级别；请求退出时恢复 ContextVar。
5. 按原始 TC-L5-004 扫描日志、响应、MySQL 与版本控制文件。
6. 使 `pip-audit .`、diff-check 通过或形成准确可复现的风险接受记录，再修正文档/OpenSpec 阶段状态。

## 9. 工作区状态与副作用

- 评估开始时工作区干净，`main` 与 `origin/main` 一致；未提交、未推送、未修改远程状态。
- 按只读评估边界，仅新增本报告并向 `Docs/PROMPT.md` 追加本次原始 Prompt 与摘要。
- 全量测试、覆盖率、OpenSpec、构建和安全探针更新了常规缓存、被忽略的 `build/`、`dist/` 与 egg-info；未做破坏性清理。
- 日志探针临时替换进程内 logger handlers，并在 finally 中恢复；未创建后台服务或持久化配置。
- 未调用 DeepSeek API，未读取或输出 `.env` 中的真实密钥值；安全探针仅使用假凭据。

## 11. 修复记录（2026-10-24）

| 报告项 | 修复 | 证据 |
| --- | --- | --- |
| P0-01 脱敏绕过 | Basic/Bearer/sk、整行键值、递归 Mapping/Sequence、异常对象 | 嵌套 details 测试 |
| P1-01 无 ReAct/工具日志 | loop 新增 react.step、tool.call，ContextVar trace | 代码 |
| P1-02 指标/失败不可观测 | http.chat 增加 tool_calls/tokens；500 写 http.error | 代码 |
| P1-03 重复非 JSON | 未完全关闭（propagate 仍为 True） | 待 S20 |
| P1-04 L5-004 缩减 | 未做端到端 DB/仓库扫描 | 待补 |
| P1-05 依赖审计 | certifi/urllib3/Starlette 仍 Open | ISSUE-045 |
| P2-01 ContextVar 不恢复 | HTTP finally reset_trace_context | 代码 |
| P2-02 每请求重配日志 | 请求路径改用模块 LOGGER | 代码 |
| P2-03/04 文档 | 部分同步 | 计数/结构 |

**复验**：352 passed、2 skipped；unit 202、contract 64、integration 85；覆盖率 **94.95%**；mypy 74 files 0 errors。

## 12. 第二轮修复（2026-10-24）

- `configure_logging`：`propagate=False`，清理旧的非 JSON handler；新增 root/已有 handler 重复输出测试。
- 安全 E2E：`test_observability_security` 注入运行时生成哨兵 Key/reasoning，扫描 HTTP、stderr 日志、SQLite 五表，均无泄漏；工具只执行 1 次。
- 依赖：升级 FastAPI 0.162 / Starlette 1.9.0；`pip-audit .` **No known vulnerabilities found**，ISSUE-045 Resolved。
- 复验：352 passed、2 skipped；unit 202、contract 64、integration 85；覆盖率 **95.01%**。
