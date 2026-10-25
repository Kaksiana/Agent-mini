# M1–M4 未闭环任务汇总

> 汇总时间：2026-10-25 12:45（Asia/Shanghai）
> 当前基线：`4bad549`（`style(s21): normalize formatting`）；`main`、`HEAD`、`origin/main` 一致；汇总开始时工作区干净
> 数据来源：`Docs/S01-report.md`～`Docs/S21-report.md`、`Docs/ISSUE.md`、`Docs/PLAN.md`、`Docs/TESTING.md`、当前代码与测试
> 口径：只收录当前仍可复现、未明确关闭或未完成验收的任务；已由后续提交关闭的项不重复列入，残余项保留

## 1. 总览

| 里程碑 | P0 | P1 | P2 | P3 | 合计 |
| --- | ---: | ---: | ---: | ---: | ---: |
| M1（S00–S05） | 0 | 0 | 0 | 1 | 1 |
| M2（S06–S12） | 0 | 1 | 1 | 1 | 3 |
| M3（S13–S16） | 0 | 1 | 0 | 1 | 2 |
| M4（S17–S21） | 1 | 3 | 7 | 2 | 13 |
| 跨阶段/过程 | 0 | 0 | 0 | 2 | 2 |
| **合计** | **1** | **5** | **8** | **7** | **21** |

**当前最关键的阻塞链：**

1. **P0**：LIVE-001/002/003 既没有测试文件，也没有执行记录（`pytest -m live` 为 0 个用例）。
2. **P1**：S21 容器没有装配 Memory、ContextBuilder、SystemDB、Redis/Mongo，公开的 HTTP 工厂应用缺少 S13–S17 的核心能力。
3. **P1**：`ToolConfig.search_provider` 仍未生效；`/healthz` 仍可空依赖返回 `ok`，且无超时/异步保护。
4. **P1**：POSIX 文件路径没有 Linux 3.11 实跑证据；M3 独立复验仍未执行。

## 2. 优先级定义

| 级别 | 定义 | 处理要求 |
| --- | --- | --- |
| P0 | v0.1 发布/AC 硬门禁；缺失时不能宣称可交付 | 立即补齐并留证 |
| P1 | 里程碑或阶段门禁；核心链路不可用、验收无法成立 | 本阶段/下一阶段前关闭 |
| P2 | 必需但可在 P1 后安排；质量、测试、文档或可验证性缺口 | 纳入迭代并登记 |
| P3 | 可选优化、历史过程债或状态清理 | 排期处理，不阻断发布 |

## 3. 已关闭口径（避免重复计数）

以下项已由后续提交关闭，不再列入本表：

- **S21**：`retry` 接线、非法 env/YAML 转 `ConfigError`、真实 `ThoughtStep` 的 ContextTooLarge 序列化、`ruff format` 清理（`72d87ee`、`4bad549`）。
- **S20**：P1-01～P1-04、P2-02～P2-04 已关闭；仅 P2-01 的 `exc_info` 输出仍有残余（见 M4-S20-01）。
- **S19**：P0-01、P1-01/02/03/05 已关闭；P1-04 的 TC-L5-004 扫描范围仍有残余（见 M4-S19-01）。
- **S18**：P0-01、P1-01/03/05/06、P2-02/03/04 已关闭；P1-02 的 L4 主体已回填但未逐项核对，LIVE 转 M4-GATE-01；P1-04 的健康检查仍有残余（见 M4-S18-01）。
- **S17**：P1-01～P1-04、P2-01/03/04 已关闭；P2-02 的链路测试仍有残余（见 M4-S17-01）；P2-05 归入跨阶段过程债（X-02）。

## 4. M1（S00–S05）

### 4.1 未闭环任务

| ID | 优先级 | 阶段 | 任务 | 当前证据 | 关闭标准 |
| --- | --- | --- | --- | --- | --- |
| M1-01 | P3 | S01/S04 | 复盘并处置早期可选技术债：S01 P2-01/04/06（JSON `Any`、职责重复、空字段状态）；S04 P2-01/02/03/04（循环函数长度、测试目录镜像、Protocol docstring、浅冻结/矛盾状态） | S01/S04 报告将其列为“可选/未修改”；后续阶段未逐项复核 | 逐项确认“修复/接受/转为设计约束”，并在 ISSUE 或 DESIGN 记录结论 |

**M1 结论**：无 P0/P1/P2 阻断项；S05 报告与 PLAN 均记录 M1 已达成。M1 只剩可选技术债，不影响进入 M2。

## 5. M2（S06–S12）

| ID | 优先级 | 阶段 | 任务 | 当前证据 | 关闭标准 |
| --- | --- | --- | --- | --- | --- |
| M2-01 | P1 | S11/S13（ISSUE-040） | 在 Linux + Python 3.11 实跑 POSIX `write_file`（dir_fd/O_DIRECTORY/O_NOFOLLOW/linkat/renameat），移除当前 Windows skip 证据缺口 | `tests/unit/test_write_file.py:131` 仍 skip；本机无 Linux/Python 3.11 实跑记录 | Linux CI/环境跑通 POSIX 用例，附命令与结果；更新 ISSUE-040 |
| M2-02 | P2 | S12/S13（ISSUE-041） | 覆盖率达到 S12 基线 97.04%，或正式重定基线并关闭 ISSUE-041 | 当前总覆盖率 94.93%；ISSUE-041 仍 Open | 补测到目标或书面重定阈值；更新 TESTING/ISSUE |
| M2-03 | P3 | S07/S10/S12 | 处置可选技术债：S07 `evaluation_error`/hypothesis、S10 hypothesis、S12 Schema 的 min/max 约束；S12 provider 全局入口由 M4-S21-02 接管 | 各报告列为可选/未引入；当前无阻断证据 | 逐项修复或登记为接受；provider 全局入口随 M4-S21-02 关闭 |

**M2 结论**：M2 功能已收口；剩余的是 Linux 可达性证明、覆盖率目标和可选约束，不改变 M2 已达成结论。

## 6. M3（S13–S16）

| ID | 优先级 | 阶段 | 任务 | 当前证据 | 关闭标准 |
| --- | --- | --- | --- | --- | --- |
| M3-01 | P1 | S13–S16 / M3 | 执行 M3 独立复验：跨轮记忆、双窗口、Context 拼接/裁剪、M3 demo、S13–S16 残余缺陷复核 | `Docs/PLAN.md:300` 明确“独立复验与 POSIX Linux 验证仍待”；`tests/integration/test_m3_demo.py` 仅 1 个演示用例通过 | 独立只读复验报告；M3 demo 与关键集成用例全绿；更新 PLAN/MEMORY M3 状态 |
| M3-02 | P3 | S13 | 处置 S13 P2-03 等测试债：TTL 测试仍真实 `sleep(1.1)`，可用 fakeredis 可控时间/数值窗口替代 | `tests/integration/test_short_term.py:64-68` | 改为可控时间或登记为接受；不增加不稳定等待 |

**M3 结论**：代码与演示已补齐，但 M3 作为里程碑尚未完成独立验收；POSIX 证据见 M2-01。

## 7. M4（S17–S21）

### 7.1 S17 — MySQL 系统库

| ID | 优先级 | 任务 | 当前证据 | 关闭标准 |
| --- | --- | --- | --- | --- |
| M4-S17-01 | P2 | 补齐 S17 P2-02：把 TC-L3-009~012 拆成同名测试，覆盖 Agent + RegistryExecutor + 五表链路、trace_id、慢 store 非阻塞、Redis 先写、Mongo/MySQL 双故障与 HTTP 200 | `tests/integration/test_systemdb.py` 现有 8 个用例，仓储覆盖率 80%；Agent 用例只注入假 store，未走真实五表 | 新增链路/时序/双故障用例；TC 名称与断言一致；覆盖率不低于门槛 |

### 7.2 S18 — HTTP 接口与健康检查

| ID | 优先级 | 任务 | 当前证据 | 关闭标准 |
| --- | --- | --- | --- | --- |
| M4-S18-01 | P1 | 关闭 S18 P1-04 残余：`/healthz` 在无 checks 时返回 `ok, {}`；检查无超时、同步检查阻塞事件循环；`create_app_from_env` 未注入 Redis/Mongo/MySQL 检查 | `agent_mini/interface/http.py:139-155` 逐项 `check()`；`create_app_from_env` 只传 agent；`/healthz` 探针返回 `{"status":"ok","dependencies":{}}` | 定义异步 health 协议；每项限时；必填依赖未配置/不可用即 `degraded/unavailable`；工厂注入真实 checks；补测试 |

### 7.3 S19 — 日志与脱敏

| ID | 优先级 | 任务 | 当前证据 | 关闭标准 |
| --- | --- | --- | --- | --- |
| M4-S19-01 | P2 | 补齐 TC-L5-004 的扫描面：当前安全 E2E 只扫 HTTP/stderr/SQLite 五表，未扫 MySQL 审计表与版本控制文件 | `tests/integration/test_observability_security.py:77-96` 使用 SQLite；无 `git ls-files`/MySQL 扫描 | 在真实 MySQL 审计表与 `git ls-files` 上扫描唯一哨兵，确认无完整密钥/reasoning；补测试 |

### 7.4 S20 — 统一异常与日志

| ID | 优先级 | 任务 | 当前证据 | 关闭标准 |
| --- | --- | --- | --- | --- |
| M4-S20-01 | P2 | 关闭 S20 P2-01 残余：`exc_info` 虽传入 logger，但 `JsonFormatter` 将标准字段排除，JSON 行没有异常堆栈 | `agent_mini/interface/http.py` 的 `http.error` 传 `exc_info=exc`；`agent_mini/observability/logging.py` 的 Formatter 跳过 `exc_info` | JSON 行输出经脱敏的异常类型/堆栈；`RedactionFilter` 覆盖异常文本；补 500 日志断言 |
| M4-S20-02 | P3 | 关闭 S20 P3-01：`configure_logging` 用 `handler.__class__.__module__.startswith("_pytest.")` 保留 pytest 私有 handler，生产代码带测试框架特判 | `agent_mini/observability/logging.py:125-131` | 用显式参数/注入替代特判；测试与生产 handler 行为一致 |

### 7.5 S21 — 配置与 DI

| ID | 优先级 | 任务 | 当前证据 | 关闭标准 |
| --- | --- | --- | --- | --- |
| M4-S21-01 | P1 | 关闭 S21 P1-02：容器只装配 LLM/Agent/APP，未装配 Memory、ContextBuilder、SystemDB、Redis/Mongo；`PromptConfig` 的 system prompt/窗口轮次、`SystemDBConfig`、`redis_url`、`mongo_uri` 均未消费 | 探针：`Service` 只有 `config/llm/agent/app`；Agent 的 `context_builder/system_prompt/system_db/short_term/mid_term` 全为 None | 增加服务键/工厂并注入 Agent；工厂应用具备系统提示、记忆、上下文裁剪、MySQL 审计与依赖健康检查；补集成测试 |
| M4-S21-02 | P1 | 关闭 S21 P1-01 残余：`ToolConfig.search_provider` 未生效，`search` 仍走模块级 `NullProvider` | `container._build_agent` 未调用 `configure_search_provider`；探针 `search` 返回 `not_configured` | 按配置构造/注入 SearchProvider；未配置时显式 `not_configured`；补 provider 生效与未配置两条测试 |
| M4-S21-03 | P2 | 修正启动契约：`MYSQL_DSN` 被强制要求但 SystemDB 未接线；README 只要求 `DEEPSEEK_API_KEY`；uvicorn 失败输出完整堆栈；`/healthz` 空依赖 | `load_config` 必填 DSN；仅设置 API Key 时 `ConfigError: 配置缺失: MYSQL_DSN`；uvicorn 打印 traceback；`/healthz` 200 空依赖 | 明确 DSN 必填/可选的取舍并同步 README/.env；工厂失败单行可定位、无堆栈噪声；health 反映依赖 |
| M4-S21-04 | P2 | 补齐 S21 P2-02 测试：容器装配（Memory/Context/SystemDB）、search provider、成功工厂启动、空依赖 health；修正 `test_env_factory_requires_key` 实际因 `MYSQL_DSN` 通过的假阳性 | `tests/unit/test_config.py` 只验证 retry/ToolConfig/非法配置；无装配/启动/search 测试 | 新增上述集成/单元用例并纳入默认门禁 |
| M4-S21-05 | P2 | 对齐文档与 OpenSpec：DESIGN §3.8 仍声称装配 ToolRegistry/Memory/ContextBuilder/SystemDB；OpenSpec config 只要求 LLM override；README 配置步骤不完整 | `Docs/DESIGN.md:375`；`openspec/changes/archive/2026-10-24-s21-config-di/design.md:10`；`openspec/specs/config/spec.md:12-19` | 文档如实描述已装配范围；OpenSpec 覆盖 Tool/Prompt/Memory/SystemDB 或明确未完成项；README 启动步骤可执行 |
| M4-S21-06 | P2 | 补齐 S21 过程/依赖证据：S21 开发条目缺原始 Prompt；ISSUE-025 声称已重解析，但当前 `pytest 9.0.2` 与 `<9` 冲突，editable 元数据仍只声明 httpx/pydantic；pydantic-settings/PyYAML 未在提交说明声明 | `Docs/PROMPT.md:2344-2347`；`Docs/ISSUE.md:295`；`pip show agent-mini`；`pyproject.toml:10-30` | 补原始 Prompt/关键约束/关联提交；干净环境 `pip install -e .` 并确认 pytest 8.x；补依赖声明与验证记录 |
| M4-S21-07 | P3 | 清理 S21 P3-01：`http.py` 未使用 DEFAULT_*、`LOGGER = __import__("logging")`、`_ = _builtin` 占位、`AppConfig.version` 未使用 | `agent_mini/interface/http.py:31-35`；`agent_mini/config/models.py:95` | 删除死代码或注释用途；统一 logger 获取方式 |

### 7.6 M4 发布门禁

| ID | 优先级 | 任务 | 当前证据 | 关闭标准 |
| --- | --- | --- | --- | --- |
| M4-GATE-01 | P0 | 实现并执行 LIVE-001/002/003（真实 DeepSeek 直答、真实工具闭环、思考模式） | `pytest -m live` 为 0 个用例；ISSUE-044 Open；PLAN §5.3 要求真实 API 记录 | 新增 live 标记测试；`RUN_LIVE=1 DEEPSEEK_API_KEY=...` 通过；留存模型、usage、trace_id 与脱敏结果；更新 ISSUE-044 |

## 8. 跨阶段/过程任务

| ID | 优先级 | 任务 | 当前证据 | 关闭标准 |
| --- | --- | --- | --- | --- |
| X-01 | P3 | 清理 ISSUE-008/009 的过期 Open 状态：README 已有测试命令、OpenSpec 已有 change/规范 | `Docs/ISSUE.md:78-96` 仍为 Open | 复核后改 Resolved 或说明豁免；保持编号连续 |
| X-02 | P3 | 记录历史过程债：早期 S01/S05/S06、S17、S20、S21 存在文档晚于实现、Prompt 缺原始记录、OpenSpec 缩窄/事后归档等；无法回溯补齐的，明确标记为历史债 | 各阶段报告与 PROMPT 记录；S21 修复记录仍只有摘要 | 在 ISSUE/AGENTS 记录“不可追溯”结论；后续阶段按 change→红测→实现→文档→门禁→归档执行 |

## 9. 建议执行顺序

1. **P1 核心链路**：M4-S21-01（Memory/Context/SystemDB/Redis/Mongo 装配）→ M4-S21-02（search provider）→ M4-S18-01（health）。
2. **P1 验证门禁**：M2-01（Linux/POSIX）→ M3-01（M3 独立复验）。
3. **P0 发布门禁**：M4-GATE-01（LIVE 测试与真实 API 验收）；建议在 P1 全链路口径确定后执行，避免用单一 Agent 替身“通过”LIVE。
4. **P2 质量补齐**：M4-S21-03/04/05/06、M4-S17-01、M4-S19-01、M4-S20-01、M2-02。
5. **P3 清理**：M1-01、M2-03、M4-S21-07、X-01、X-02。

## 10. 复核命令与当前基线

| 命令 | 当前结果 |
| --- | --- |
| `python -m pytest --cov=agent_mini --cov-report=term-missing -q` | **376 passed，2 skipped**，覆盖率 **94.93%** |
| `python -m ruff check .` / `python -m ruff format --check .` | 通过；81 files formatted |
| `python -m mypy agent_mini tests` | 78 source files，0 errors |
| `openspec validate --all --strict` | 21 passed，0 failed |
| `git diff --check` | 通过 |
| `pip-audit .` | No known vulnerabilities found |
| `python -m pytest -m live --collect-only -q` | **0 个用例** |
| `python -m pytest tests/integration/test_m3_demo.py -q` | 1 passed |
| S21 配置/DI 探针 | `Service` 仅 `config/llm/agent/app`；Agent 的 context_builder/system_prompt/system_db/short_term/mid_term 均为 None；search 返回 `not_configured` |
| 启动探针 | 仅设置 `DEEPSEEK_API_KEY` 时 `ConfigError: 配置缺失: MYSQL_DSN` |
| 健康检查探针 | `/healthz` 返回 200 `{"status":"ok","dependencies":{}}` |

## 11. 工作区状态与副作用

- 汇总开始时 `HEAD`、`main`、`origin/main` 均为 `4bad549`，工作区干净。
- 本次仅新增本汇总文档并向 `Docs/PROMPT.md` 追加记录；未修改实现、测试、OpenSpec 或远程状态。
- 全量测试、覆盖率、静态检查、OpenSpec、构建与探针更新了常规缓存和被忽略的 `build/`、`dist/`、`.coverage`、`.pytest_cache/`、`.ruff_cache/`、`.mypy_cache/`、`agent_mini.egg-info/`。
- 未调用 DeepSeek API，未读取或输出 `.env` 中的真实密钥值；所有探针使用假值。

## 12. 本次执行记录（2026-10-25）

### Docker 真机测试

| 项目 | 命令 | 结果 |
| --- | --- | --- |
| MySQL 8 | `MYSQL_TEST_DSN=mysql+asyncmy://root:testpass@127.0.0.1:3307/agent_mini pytest tests/integration/test_systemdb.py -q` | **8 passed** |
| Linux/Python 3.11 POSIX | `docker run --rm -v <repo>:/app -w /app python:3.11-slim ... pytest tests/unit/test_write_file.py -q` | **22 passed, 1 skipped**（Windows mkstemp seam） |

Docker 容器：`agent-mini-mysql`（mysql:8.0，3307->3306）已启动并保留；python:3.11-slim 为临时容器。

### 按建议顺序已处理

| ID | 本次结果 |
| --- | --- |
| M4-S21-01 | **部分关闭**：容器新增 short/mid/systemdb/context 服务；Agent 注入 short_term、system_db、context builder；Prompt 文件存在时读取。Redis/Mongo 仅配置 URL 时装配；真实 Redis/Mongo 链路未测。 |
| M4-S18-01 | **部分关闭**：`create_app_from_env` 注入 redis/mongo/mysql health；仍无每项超时，同步 check 仍可能阻塞。 |
| M2-01 | **部分关闭**：Linux 3.11 POSIX 22 passed；`test_parent_swap_before_publish_is_blocked` 因 Windows mkstemp 注入 seam 在 POSIX skip，未移除该 skip。 |
| M4-S21-02 | 未关闭：search_provider 仍未生效 |
| M4-S21-03/04/05/06 | 未关闭 |
| M3-01、M4-GATE-01 | 未执行；LIVE 无 Key |
| M4-S19-01、M4-S20-01、M4-S17-01 | 未关闭 |

### 新发现并修复

- POSIX `write_file` 使用 `os.rename` 导致 replace 失败测试不被注入；改为 `os.replace`，并把发布阶段 OSError 与路径校验错误区分。
- POSIX 临时文件在 `_TargetExistsError` 时未清理；已补清理。
- `test_concurrent_create_is_not_overwritten` 增加 POSIX `os.link` 注入分支。

### 门禁

`377 passed, 2 skipped`；unit 220；contract 64；integration 93；覆盖率 **94.56%**；ruff/format/mypy 通过。

### 追加（2026-10-25 13:13）

- M4-S21-02 按当前阶段决策 **mock-only 关闭**：`ToolConfig.search_provider` 支持 `none|mock`；`mock` 返回确定性本地结果，不访问网络；`none` 明确 `not_configured`。测试：`test_search_provider_mock_and_none`。
- 真实搜索 provider 不进 v0.1；后续接入需新 change。

### 追加（2026-10-25 15:27）

- **M4-S18-01 关闭**：health 检查支持异步函数/同步函数线程化；单项 2s 超时；空 checks 返回 degraded；容器注入 mysql/redis/mongo（配置时）。测试 `test_health_slow_check_times_out`、`test_health_empty_is_degraded`。
- **M4-S21-03 部分关闭**：新增 `agent_mini.interface.server:main` 与 `agent-mini` console script；ConfigError 单行退出码 2，无 Traceback；README 明确 `DEEPSEEK_API_KEY` 与 `MYSQL_DSN` 必填。
- **M4-S21-01 仍部分**：Redis/Mongo 仅在 URL 配置时装配，未做真实服务链路测试。
- 门禁：381 passed、2 skipped；unit 222；integration 95；覆盖率 94.56%。

### 追加（2026-10-25 15:45）

- **M3-01 部分关闭**：`Docs/M3-review.md` 记录 51 passed；只读执行，非独立第三方评审。
- **M4-S19-01 部分关闭**：新增 `test_sentinel_not_in_tracked_files` 扫描 `git ls-files`；真实 MySQL 审计表扫描仍未做。
- **M4-S20-01 关闭**：`JsonFormatter` 输出脱敏 `error_type/error_message/stack`；新增异常堆栈 JSON 测试。
- **Docker Redis/Mongo 未执行**：Docker Desktop 再次停止，无法启动 redis/mongo 容器；MySQL/Linux 证据沿用前次。
- **M4-GATE-01**：`DEEPSEEK_API_KEY` 仍不存在，LIVE 阻塞。
- 门禁：383 passed、2 skipped；unit 223、contract 64、integration 96；覆盖率 94.57%。

### 追加（2026-10-25 15:55）

- **M4-GATE-01 关闭**：`RUN_LIVE=1 pytest tests/live -q` → **3 passed**（LIVE-001/002/003）；Key 来自 `.env`，未输出。
- **真实组件**：`agent-mini-mysql`(3307)、`agent-mini-redis`(6380)、`agent-mini-mongo`(27018) 均 Up；容器 health 探针返回 `{'redis':'ok','mongo':'ok','mysql':'ok'}`。
- **M4-S21-01 部分关闭**：Redis/Mongo/MySQL 客户端装配与 health 已实测；对话记忆链路未做真实 Redis/Mongo 往返。
- 门禁：`RUN_LIVE=1` 全量 **386 passed、2 skipped**；默认全量 383 passed、2 skipped + live 3 skipped；覆盖率 94.53%。

### 追加（2026-10-25 16:05）

- **M4-S19-01 关闭**：新增 `test_mysql_audit_sentinel_scan`，真实 MySQL 五表扫描唯一哨兵；`git ls-files` 扫描已有。
- **M4-S21-01 关闭**：新增真实 Redis/Mongo 往返测试（`test_redis_real_round_trip`、`test_mongo_real_round_trip`）与容器装配 health。
- **真机门禁**：`RUN_LIVE=1` + 三个 Docker 组件环境，全量 **390 passed、1 skipped**；默认 **383 passed、8 skipped**。
- 覆盖率 **94.76%**（2670 statements，140 missed）。

### 追加（2026-10-25 16:20）

- **M4-S17-01 关闭**：新增真实 SQLite 仓储 + RegistryExecutor + Agent 五表链路测试；断言 sessions/tool_invocations/request_metrics 各 1、trace_id 一致。
- **wheel + 仓库外导入**：`python -m build --wheel` 成功；`pip install --no-deps --target <temp> dist/*.whl` 后在 `C:\` 导入，`agent_mini` 与 `agent_mini.config.models` 均解析到 temp。
- **Python 3.11 全量**：`python:3.11-slim` + 三 Docker 服务 + RUN_LIVE=1 全量 **390 passed、2 skipped**（git 不可用、POSIX Windows seam）。
- 本机 Docker+LIVE 全量 **391 passed、1 skipped**；覆盖率 **94.76%**。
- M3 独立评审子代理进行中，未关闭 M3-01。

### 追加（2026-10-25 16:15）

- **M3-01 P1 修复**：trim_reason、跨存储顺序、ensure_indexes、reasoning 计费一致性；Mongo 脏文档逐条跳过。
- **M4-S17-01 关闭**：真实五表链路测试。
- **wheel/仓库外导入、Python 3.11 全量** 已完成。
- M3 独立复审已提交子代理复核，P2/P3（真实全链路、重复读）仍开放。

### 追加（2026-10-25 16:30）

- **M3-01 P1 闭合**：独立子代理复核 A/B 故障路径均为 `r1,r2,r3`；M3 五文件 **53 passed**。
- **M4-S17-01 关闭**；**wheel + 仓库外导入**重建成功；**Python 3.11 全量 392 passed、2 skipped**。
- 本机 Docker+LIVE 全量 **393 passed、1 skipped**；默认 **386 passed、8 skipped**；覆盖率 **94.62%**。
- M3 仍留 P2 真实全链路、P3 重复 build/fit/索引/关闭客户端。

### 追加（2026-10-25 16:45）

- **M3 P2 关闭**：真实 Redis+Mongo+ContextBuilder 链路测试通过。
- **M3 P3**：search_rounds 自动建索引、Agent.close 关闭外部客户端已关闭；重复 build/fit 保留（回退以免破坏 deadline 语义）。
- **门禁**：395 收集；Docker+LIVE 394 passed、1 skipped；默认 387 passed、8 skipped；Python 3.11 393 passed、2 skipped；覆盖率 **94.72%**。
