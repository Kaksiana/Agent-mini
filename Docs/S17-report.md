# S17 阶段代码产出独立评估报告

> 评估时间：2026-10-24 01:10（Asia/Shanghai）
> 评估基准：`84e2f9c..163eb09`；评估开始时 `main`、`HEAD`、`origin/main` 均为 `163eb09`
> 评估方式：独立只读复核；除本报告与 `Docs/PROMPT.md` 外，不修改实现、测试、OpenSpec 或远程状态
> 结论：**不通过；S17 暂不可进入 S18**
> 缺陷汇总：**P0 0 项、P1 4 项、P2 5 项、P3 0 项**

## 1. 评估范围与基准

本次以 S16/M3 收口提交 `84e2f9c` 至 S17 归档提交 `163eb09` 为评估范围，共 20 个文件、`+818/-18`。重点复核：

- FR-SYS-01~05、FR-RT-07、AC-19。
- TC-L3-009~012 与 `Docs/PLAN.md` S17 验收标准。
- OpenSpec `system-db` 主规范与归档 change `2026-10-24-s17-systemdb`。
- MySQL 五表 DDL、SQLAlchemy Core 仓储、模型/工具 upsert、会话状态、审计与指标写入。
- Agent 响应后异步写入、失败降级、关闭排空与 Redis/Mongo 隔离。
- 测试、覆盖率、静态门禁、依赖、wheel 与阶段流程证据。

五张表、SQLite 仓储 happy path、模型/工具 enabled 保留以及异常 store 不阻断对话已经实现。但启动初始化链路没有实现，`auto_create` 是死配置；会话没有 idle/closed 状态流转；Runtime 把请求与工具耗时固定写成 0；宣称存在的 `MYSQL_TEST_DSN` 门控测试实际不存在。以上问题直接影响 S17 核心验收。

## 2. 复核命令与结果

| 命令 / 检查 | 结果 |
| --- | --- |
| `git diff --stat 84e2f9c..163eb09` | 20 files changed，818 insertions，18 deletions |
| `python -m pytest tests/integration/test_systemdb.py tests/unit/test_package_skeleton.py -q` | **10 passed** |
| `python -m pytest --cov=agent_mini --cov-report=term-missing -q` | **321 passed，1 skipped**；总覆盖率 **95.07%**；`systemdb/repository.py` **78.90%** |
| `.venv\\Scripts\\python.exe -m pytest ...` | 收集失败：该既有 `.venv` 未同步安装 S17 新增的 SQLAlchemy；随后按 README 使用可用的 Python 3.13 环境复测 |
| `python -m ruff check .` | All checks passed |
| `python -m ruff format --check .` | **失败**：`agent_mini/runtime/agent.py:143-145` 会被重排 |
| `python -m mypy agent_mini tests` | **71 source files，0 errors** |
| `openspec validate --specs --strict` / `--all --strict` | **17 passed，0 failed**；仅既有长 Requirement INFO |
| `python -m build` | sdist/wheel 构建成功；wheel 含 `agent_mini/systemdb/schema.sql` |
| `git diff --check 84e2f9c..163eb09` | **失败**：7 个文件存在 EOF 多空行 |
| `python -m pip check` | No broken requirements found |
| `pip-audit .` | 项目依赖 **No known vulnerabilities found**；缓存目录有环境警告 |
| 禁用 Agent 框架扫描 | `pyproject.toml` 与 `agent_mini/` 无命中 |
| MySQL 环境检查 | `MYSQL_TEST_DSN` 未设置；MySQL80 为 Stopped/Disabled；无本地 MySQL Docker 镜像 |

补充：`pip-audit --local` 对共享 Python 环境报告 certifi 1 项、urllib3 3 项已知漏洞；项目路径审计未发现漏洞，因此这些不归因于 S17，但共享验证环境应单独升级。

## 3. 维度结论

| 维度 | 结论 | 证据 |
| --- | --- | --- |
| 功能完整性 | **不通过** | 启动建表/模型工具登记无装配入口；会话只支持 active |
| 正确性 | **不通过** | 请求与工具 `duration_ms` 永远为 0；重复 upsert 会改写 `created_at` |
| 可靠性 | **部分通过** | 异常 store 不阻断响应并告警；但没有真实 MySQL 连接、超时和 shutdown 验证 |
| 测试与覆盖率 | **不通过** | 全量绿，但 TC-L3-009~012 仅名义映射；MySQL 门控不存在；新仓储覆盖率 78.90% |
| 可读性与架构 | **部分通过** | 仓储 API 清晰；`schema.sql` 与 metadata 双 DDL 已漂移，`auto_create` 无效 |
| 安全与依赖 | **通过** | 参数化 SQL、无对话正文列、无禁用框架、项目依赖审计无已知漏洞 |
| 性能 | **部分通过** | 系统库写入通过后台任务不阻塞主响应；逐条事务写审计，尚无批量/并发实测 |
| 工程与流程 | **不通过** | Ruff format/diff-check 失败；OpenSpec 与 Prompt 在代码后提交；文档出现转义文本 |

## 4. 分级问题清单

### P1-01 — 启动初始化与登记链路未实现，`auto_create` 为死配置

- **位置**：`agent_mini/systemdb/models.py:10-17`、`agent_mini/systemdb/repository.py:40-80`；全仓生产代码无 `ensure_schema/upsert_models/upsert_tools` 调用方。
- **问题**：仓储只暴露需要手工调用的方法。`SystemDBConfig.auto_create` 被保存但从未读取；模型与工具记录也没有启动协调器或初始化 API 消费。即使提供 DSN，启动后五表和登记数据仍不会自动出现。
- **判定依据**：PLAN S17 明确要求“启动时模型与工具登记正确 upsert”；DESIGN §3.9 要求 `auto_create=true` 时启动执行；OpenSpec 要求启动 upsert。
- **建议方向**：提供单一初始化入口，按 `auto_create` 决定建表，再幂等登记模型/工具；由后续应用装配明确调用，并覆盖 true/false、重复启动和失败降级。

### P1-02 — FR-SYS-01 的会话状态流转缺失

- **位置**：`agent_mini/systemdb/repository.py:82-91,242-275`。
- **问题**：公开 API 只有 `upsert_session`，插入与更新都把状态写成 `active`；没有设置 idle/closed 的接口。已有 idle/closed 会话再次 upsert 还会被强制恢复为 active。
- **边界证据**：反射结果仅有 `_session_upsert` 与 `upsert_session`；代码中没有其他会话状态写入路径。
- **判定依据**：FR-SYS-01 是 P0，要求 active/idle/closed 状态；DESIGN §3.9 明确“状态流转”。
- **建议方向**：定义受约束的状态转换 API 与允许转换表，区分“活跃刷新”和显式关闭，并补状态合法性、幂等和并发更新测试。

### P1-03 — 审计与请求指标耗时被固定写成 0

- **位置**：`agent_mini/runtime/agent.py:107-150,216-228`；`agent_mini/systemdb/repository.py:138-176`。
- **问题**：Agent 没有记录请求开始时间，调用 `record_turn` 时直接传入常量 `0`；仓储又把同一个值写入每条工具审计和请求指标，因此线上时延数据恒为 0。
- **边界证据**：使用 AsyncMock 捕获调用参数，得到 `duration_ms=0`；该结果与 LLM 实际耗时无关。
- **判定依据**：FR-SYS-04、TC-L3-009 和表设计均要求工具审计与请求级 `duration_ms` 指标，常量 0 不是有效指标。
- **建议方向**：用单调时钟测量整轮请求；工具级耗时应在执行器边界单独采集，不能复用请求总耗时。新增非零与多工具不同耗时断言。

### P1-04 — 真实 MySQL 门控测试不存在，S17 的目标方言未获可执行验证

- **位置**：`tests/integration/test_systemdb.py:28-30,33-108`；`openspec/changes/archive/2026-10-24-s17-systemdb/design.md:12`；`Docs/ISSUE.md:511`。
- **问题**：所有仓储用例都硬编码 `sqlite+aiosqlite`。代码、测试和配置中没有读取 `MYSQL_TEST_DSN`，也没有 MySQL pytest marker/skip。OpenSpec 和 ISSUE 却声称设置该变量即可运行门控验证。
- **判定依据**：S17 目标是 MySQL 8；SQLite 不能证明 JSON、DATETIME(6)、索引、BIGINT、连接池和 `ON DUPLICATE KEY UPDATE` 的实际行为。当前即使提供 MySQL DSN，测试仍只会跑 SQLite。
- **建议方向**：增加真实 MySQL 环境门控 fixture，执行 `schema.sql` 两次并覆盖五表、upsert、enabled 保留、审计/指标、连接不可用；缺环境时显式 skip，CI 至少有一条 MySQL 8 job。

### P2-01 — `schema.sql` 与 metadata 双 DDL 已经漂移

- **位置**：`agent_mini/systemdb/schema.sql:1-60`、`agent_mini/systemdb/repository.py:50-55,281-343`。
- **问题**：`ensure_schema()` 完全不执行打包的 `schema.sql`，而是调用 metadata `create_all`。metadata 把审计表主键建为 `INTEGER`，且没有 schema.sql 中三个二级索引；由不同入口建出的 MySQL 表结构不一致。
- **边界证据**：MySQL 方言编译的 metadata `tool_invocations` DDL 为 `id INTEGER` 且只有主键，无 `idx_tool_invocations_session_time`。
- **建议方向**：选定唯一 DDL 真源；若 schema.sql 是权威，初始化就执行并测试它；若 metadata 是权威，从 metadata 生成迁移/DDL，并对结构做一致性测试。

### P2-02 — TC-L3-009~012 的自动化映射名不副实，新增仓储覆盖率低于门槛

- **位置**：`tests/integration/test_systemdb.py:1-148`。
- **问题**：测试文件标题一次声明四个 TC，但没有覆盖“带真实工具调用的 Agent→五表”链路、对应 trace_id、非阻塞时序、Redis 先写、Mongo/MySQL 双异常或 HTTP 200；连接失败测试只测 `ensure_schema`。异步测试的 store 立即返回，也不能证明不阻塞。仓储精确覆盖率只有 78.90%。
- **判定依据**：TC-L3-009~012 的步骤与预期均比现有 5 个用例更完整；NFR-TEST-01 要求新增/修改代码覆盖率至少 80%。
- **建议方向**：按 TC 拆分测试名称与前置条件，增加 Agent+RegistryExecutor+三类存储的链路测试、慢 store 非阻塞测试、双故障日志测试和 MySQL 方言分支覆盖。

### P2-03 — 模型/工具重复 upsert 会改写 `created_at`

- **位置**：`agent_mini/systemdb/repository.py:181-240`。
- **问题**：duplicate update 的字段集合只排除 `enabled`，因此同时更新 `created_at`；创建时间退化为“最近启动时间”，与 `updated_at` 无法区分。
- **边界证据**：同一模型间隔 20ms upsert 两次，查询得到 `created_at_changed=True`。
- **判定依据**：表同时提供 created_at/updated_at，通常分别表示首次创建与最后更新；重复启动的幂等登记不应抹去首次创建时间。
- **建议方向**：更新集合排除主键、唯一键、enabled 和 created_at，只刷新业务字段与 updated_at；补时间字段不变/变化断言。

### P2-04 — 格式门禁与 S17 文档渲染失败

- **位置**：`agent_mini/runtime/agent.py:143-145`、`Docs/DESIGN.md:398`，以及本阶段 7 个 EOF 多空行。
- **问题**：`ruff format --check` 失败；DESIGN 把 `\\n` 作为普通文本写入单行，导致 §3.9.1 与后续 §4 无法正常形成 Markdown 结构；多份文档还引入 BOM/EOF 噪音。
- **判定依据**：阶段 DoD 要求静态门禁通过且文档可读；当前自动格式检查和 `git diff --check` 均失败。
- **建议方向**：按项目格式化器修正代码；把字面转义恢复为真实换行，并统一 UTF-8/EOF 策略。

### P2-05 — Docs First、OpenSpec、Prompt 与提交规范未闭环

- **位置**：提交 `c6a27d8`、`a360145`、`163eb09`；`Docs/PROMPT.md:2161-2173`；S17 OpenSpec proposal/design/tasks。
- **问题**：实现提交先于 S17 文档与 OpenSpec 归档提交；没有可核验的代码前 change/红测历史。S17 Prompt 条目缺目标、关键约束、人工修正/最终决策和关联提交；proposal 无回滚方式；三条提交描述为英文。
- **判定依据**：AGENT.md §1/2/3/5/6/8 与用户全局契约要求文档先行、TDD、Prompt 六要素、OpenSpec 先建后实现及中文提交描述。
- **建议方向**：后续阶段先提交 change、设计、测试设计与失败证据，再实现；收口前按清单补齐 Prompt/Issue/回滚/验证和中文 Conventional Commit。

## 5. 需求—实现—测试追溯

| 需求 / 用例 | 实现 | 自动化证据 | 结论 |
| --- | --- | --- | --- |
| FR-SYS-01 / TC-L3-009 | session upsert、last_active_at、message_count | SQLite 重复 upsert 得到 count=2/status=active | **部分满足**：无 idle/closed 状态流转 |
| FR-SYS-02 / TC-L3-009 | models 表与 MySQL/SQLite upsert | SQLite 2 条、enabled 手工值保留 | **部分满足**：无启动登记，未跑 MySQL，created_at 被改写 |
| FR-SYS-03 / TC-L3-009 | tools 表、JSON Schema 与 upsert | SQLite 6 条 | **部分满足**：无启动登记，未验证工具 enabled 与 MySQL JSON |
| FR-SYS-04 / TC-L3-009 | tool_invocations/request_metrics 插入 | 仓储直接插入各 1 条 | **不满足**：无 Agent 工具闭环，耗时恒 0，未断言 trace 内容 |
| FR-SYS-05 / TC-L3-010 | 仓储捕获异常；Agent 捕获 store 异常 | Broken store 探针正常返回 `ok` 并告警 | **组件级通过**；真实 MySQL 不可用未验证 |
| FR-RT-07 / TC-L3-011 | `asyncio.create_task` 后返回、drain | store.called 测试 | **部分满足**：未测慢写非阻塞与 Redis→响应→Mongo/MySQL 时序 |
| FR-RT-07 / TC-L3-012 | Mongo/MySQL 异常不阻断 | 仅分别存在既有 Mongo 测试与本轮 Broken store 探针 | **部分满足**：未测同请求双异常与双日志 |
| AC-19 | 五表、登记、会话、审计、降级 | SQLite happy path + 静态 schema | **未通过**：P1-01~04 尚未关闭 |

## 6. 边界抽查

| 探针 | 结果 | 判定 |
| --- | --- | --- |
| SQLite 连续两次 create_all | 五表存在，无异常 | 通过（仅 SQLite） |
| 模型/工具重复 upsert | 行数不增加，手工 enabled 保留 | 通过 |
| 同一模型间隔 20ms 重复 upsert | `created_at_changed=True` | 失败 |
| AsyncMock 捕获 Agent→record_turn | `duration_ms=0` | 失败 |
| Broken store 抛 ConnectionError | reply=`ok`，日志含 `systemdb.degraded` | 通过 |
| 会话公开 API 反射 | 仅 `upsert_session`，无 idle/closed | 失败 |
| MySQL 方言编译 upsert | 可生成 `ON DUPLICATE KEY UPDATE` SQL | 组件级通过，未执行 |
| MySQL 方言编译 metadata DDL | 主键为 INTEGER，缺 schema.sql 索引 | 失败 |
| `MYSQL_TEST_DSN` 搜索 | 仅文档命中，测试/实现无读取 | 失败 |
| request_metrics 表内容隔离 | 无 content 列 | 通过 |

## 7. 技术债与后续影响

1. S18 HTTP 装配没有可直接复用的系统库启动初始化单元；若直接接入，数据库可能保持空表/空登记。
2. session 无状态转换会阻塞后续会话管理接口和关闭语义，不能只留给配置阶段处理。
3. 恒为 0 的 duration 会污染 S19 可观测指标，必须在产生数据的 Runtime/工具边界修正，而不是报表层补偿。
4. schema.sql 与 metadata 双真源会使开发、自动建表和生产手工 DDL 逐步分叉，后续迁移成本上升。
5. 当前每条工具审计单独开启事务；大量工具调用时写放大明显，后续可在正确性修复后评估单事务/批量写入。
6. `Agent.drain()` 仍统一使用 `_mongo_timeout` 和 `memory.degraded` 超时日志处理全部后台任务；当 system timeout 大于 mongo timeout 时，系统库任务可能在关闭阶段被提前取消，宜在后续补独立排空策略。
7. 继承风险：ISSUE-040 的 Linux/POSIX 验证、Python 3.11 独立复验仍未在本轮关闭；本次使用 Python 3.13.9/Windows。

## 8. 总体门禁结论

**S17 不通过，暂不可进入 S18。**

进入 S18 前至少必须：

1. 关闭 P1-01：实现并验证 `auto_create`、启动建表和模型/工具登记入口。
2. 关闭 P1-02：实现 active/idle/closed 状态流转与合法转换测试。
3. 关闭 P1-03：采集真实请求/工具耗时，禁止常量 0 指标。
4. 关闭 P1-04：建立可执行的 MySQL 8 门控测试并至少完成一次真实环境验证。
5. 统一 DDL 真源，补齐 TC-L3-009~012，修复 created_at、格式门禁与文档/流程问题后重新执行全量门禁。

已有的五表 schema、参数化写入、SQLite happy path、enabled 保留、职责隔离和降级探针是可复用基础，但不能替代缺失的启动能力、状态生命周期、真实指标和 MySQL 验证。

## 9. 工作区状态与副作用

- 评估开始时工作区干净，`main` 与 `origin/main` 一致；未提交、未推送、未修改远程状态。
- 按只读评估边界，仅新增本报告并向 `Docs/PROMPT.md` 追加本次原始 Prompt 与摘要。
- 全量测试、覆盖率、Ruff、mypy、OpenSpec 和边界探针产生/更新常规 `.pytest_cache`、`.coverage`、`.mypy_cache`、`.ruff_cache`；均为既有或被忽略产物。
- `python -m build` 更新了被忽略的 `build/`、`dist/` 与 `agent_mini.egg-info/`；为避免删除评估前已有产物，未做破坏性清理。
- 既有 `.venv` 缺少 S17 依赖，本轮未改写该环境；最终复核使用系统 Python 3.13.9。
- pip-audit 缓存写入出现跨卷移动警告，不影响项目审计结果；未生成仓库内跟踪文件。


## 11. 修复记录（2026-10-24）

| 报告项 | 修复 | 证据 |
| --- | --- | --- |
| P1-01 启动链路 | `initialize(models,tools)` 按 auto_create 建表并 upsert | `test_initialize_and_status_transitions` |
| P1-02 会话状态 | `set_session_status` 允许转换表；upsert 不再强制 active | 状态测试 idle 保留 |
| P1-03 耗时 0 | Agent 单调时钟记录请求时长传入 record_turn | duration_ms≥10 |
| P1-04 MySQL 门控 | `MYSQL_TEST_DSN` fixture；MySQL 执行 schema.sql 两次 | 无 DSN skip（ISSUE-043） |
| P2-01 双 DDL | MySQL 走 schema.sql；SQLite 走 metadata | 代码 |
| P2-03 created_at | upsert 更新排除 created_at | `test_created_at_is_stable_on_upsert` |
| P2-04 格式 | ruff/mypy/EOF 修复 | 通过 |

**复验**：323 passed、2 skipped；unit 198、contract 64、integration 61（MySQL 1 skip）；覆盖率 **94.66%**；mypy 71 files 0 errors。
