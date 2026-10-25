# S21 阶段代码产出独立评估报告

> 评估时间：2026-10-25 12:28（Asia/Shanghai）
> 评估基准：`6173912..3fddcc8`；评估开始时 `main`、`HEAD`、`origin/main` 均为 `3fddcc8`，工作区干净
> 评估方式：独立只读复核；除本报告与 `Docs/PROMPT.md` 外，不修改实现、测试、OpenSpec 或远程状态
> 结论：**不通过；S21 不可收口，M4/v0.1 不可交付**
> 缺陷汇总：**P0 0 项、P1 6 项、P2 4 项、P3 1 项**
> 前置复核：S20 的 P1 已基本关闭，但 S20 P2-02 的修复引入了真实 `ContextTooLarge` 返回 500 的回归

## 1. 评估范围与基准

本次以 S20 修复收口提交 `6173912` 至 S21 归档提交 `3fddcc8` 为范围，共 23 个文件、`+620/-39`。重点复核：

- FR-CFG-01、FR-CFG-02、FR-CFG-03、FR-CFG-04、FR-LLM-05、AC-13、AC-19。
- TC-L1-017、TC-L1-018、TC-L4-006。
- OpenSpec `config` 主规范与归档 change `2026-10-24-s21-config-di`。
- 四类配置模型/加载器、YAML+env 优先级、`ConfigError` 启动失败、DI 容器作用域/override、HTTP 工厂迁移。
- 配置是否真正进入 Agent 的工具、Prompt、Memory、Context、SystemDB 装配，而不只是“能解析”。

S21 的配置解析与通用容器骨架已经落地：四类冻结模型、`SecretStr`、YAML+env 合并、`ConfigError` 缺字段提示、singleton/transient/override 都有实现；`container.override(Service.LLM, ...)` 也确实能让新解析的 Agent 使用替身。

但“配置与依赖注入收口”没有完成：容器只注册 `config/llm/agent/app` 四个键，`ToolConfig`、`PromptConfig`、`SystemDBConfig`、`redis_url`、`mongo_uri` 全部没有被消费；`ModelConfig.retry` 被静默丢弃；非法 env 类型直接抛 pydantic `ValidationError`；真实 `ContextTooLarge.trace` 会让错误响应 500；`ruff format` 门禁仍然失败。最终 HTTP 工厂出来的应用没有沙箱、Prompt、Memory、Context 裁剪和 MySQL 审计能力，M4 不能成立。

## 2. 前置 S20 修复复核

S20 报告修复提交为 `fbfd178` 与 `6173912`，本次先复核其是否真正关闭上一轮 P1：

| S20 项 | 复核结果 | 证据 |
| --- | --- | --- |
| P1-01 错误日志 trace | **通过** | 错误探针日志已带请求 `trace_id`/`session_id`，不再是 null |
| P1-02 LLM/Tool 重复根 | **通过** | `llm.errors.LLMError` 与 `tools.registry.ToolError` 改为 observability 别名，新增共享根测试 |
| P1-03 错误码/`to_error_response` | **通过** | `INVALID_INPUT`、`SANDBOX_VIOLATION`、`INTERNAL` 已统一；`to_error_response()` 存在并接入 `_error` |
| P1-04 静态/marker/计数 | **部分通过** | `ruff check`、marker、unmarked 0 已恢复；但 S20 修复引入的 UTF-8 BOM 使 `ruff format --check` 仍失败 |
| P2-01 日志异常出处 | **部分通过** | 已有 `error_type`/`error_message`/`duration_ms`；`exc_info` 虽传入 logger，但 `JsonFormatter` 仍将标准字段排除，JSON 行没有堆栈 |
| P2-02 ContextTooLarge 证据 | **回归失败** | 测试用 `{"step": 1}` 假 trace 通过；真实 `ThoughtStep` 对象进入 `JSONResponse` 后触发 `TypeError`，响应变为 500 |
| P2-03/04 文档漂移 | **通过（S20 范围）** | ISSUE-024 已单一 Resolved；README 更新到 S20；设计清单去重 |

因此 S21 的起点并不是干净的：S20 的 P1 基本关闭，但 P2-02 的修复带入了新的运行时回归，S21 未修复，最终阶段不能把它当作已关闭项。

## 3. 复核命令与结果

| 命令 / 检查 | 结果 |
| --- | --- |
| `git diff --stat 6173912..3fddcc8` | 23 files changed，620 insertions，39 deletions |
| `python -m pytest --cov=agent_mini --cov-report=term-missing -q` | **373 passed，2 skipped**，33.21s；总覆盖率 **94.85%**；`config/loader.py` 87%、`config/container.py` 95%、`config/models.py` 95% |
| `pytest -m unit/contract/integration --collect-only -q` | unit 217（216 passed + 1 skipped）、contract 64、integration 94（93 passed + 1 skipped）；unmarked **0**；合计 375 |
| `python -m ruff check .` | All checks passed |
| `python -m ruff format --check .` | **失败**：4 个文件需重排（3 个 UTF-8 BOM + `tools/registry.py` 空行） |
| `python -m mypy agent_mini tests` | **78 source files，0 errors** |
| `openspec validate --specs --strict` / `--all --strict` | **21 passed，0 failed**；仅既有长 Requirement INFO |
| `git diff --check 6173912..3fddcc8` | 通过 |
| `python -m build` | sdist/wheel 构建成功；wheel 含 `agent_mini/config/*`；METADATA 含 pydantic-settings/PyYAML |
| `pip-audit .` | **No known vulnerabilities found** |
| 配置/DI 探针 | 容器只有 `config/llm/agent/app`；Agent 的 context_builder/system_prompt/system_db/short_term/mid_term 全为 None |
| 工具配置探针 | `ToolConfig(enabled=False, sandbox_root=..., max_file_size=123, search_provider="probe")` 下仍返回 6 个 Schema；`read_file` 返回 `missing_sandbox_root`；`search` 返回 `not_configured` |
| retry 探针 | 配置 `retry=1`，客户端 `_max_attempts=3` |
| 非法 env 探针 | `MYSQL_POOL_SIZE=abc`、`DEEPSEEK_TIMEOUT=abc`、`MYSQL_AUTO_CREATE=notabool` 均抛 pydantic `ValidationError`，不是 `ConfigError` |
| 非法 YAML 探针 | `model: not-a-map`、`systemdb: not-a-map` 抛原生 `ValueError`；`tool`/`prompt` 非映射被静默忽略 |
| HTTP 启动探针 | 仅设置 `DEEPSEEK_API_KEY` 时启动报 `配置缺失: MYSQL_DSN`；uvicorn 输出完整 Python 堆栈 |
| `/healthz` 探针（合法 env） | 200 `{"status":"ok","dependencies":{}}`，没有任何依赖检查 |
| 真实 `ContextTooLarge` 探针 | `trace` 为 `ThoughtStep` 时返回 **500 INTERNAL**，日志 `error_type=TypeError`；`json.dumps` 确认 `ThoughtStep` 不可序列化 |
| 安装环境 | `pytest 9.0.2`，但 `pyproject.toml` 声明 `pytest>=8.0,<9`；`pip show agent-mini` 的 Requires 仍只有 `httpx,pydantic` |

两个 skip 分别是真实 MySQL（`MYSQL_TEST_DSN` 未设置）和 Windows 下 POSIX-only 文件用例。`pytest -m live`、`-m e2e` 仍是 0 个用例，M4 的真实 API 与 MySQL 验收没有执行。评估未调用 DeepSeek，未读取或输出 `.env` 中的真实密钥值。

## 4. 维度结论

| 维度 | 结论 | 证据 |
| --- | --- | --- |
| 功能完整性 | **不通过** | 配置可解析但 Tool/Prompt/Memory/Context/SystemDB 未装配；全链路口径不成立 |
| 正确性 | **不通过** | retry 被忽略；非法配置类型不转 ConfigError；真实 ContextTooLarge 返回 500 |
| 可靠性 | **部分通过** | 缺字段能快速失败、通用容器可 override；但启动堆栈噪声、健康检查为空、Context 错误路径崩溃 |
| 测试与覆盖率 | **不通过** | 94.85% 行覆盖，但装配、retry、非法 env、真实 trace、成功工厂启动均无断言 |
| 可读性与架构 | **部分通过** | 配置模型/加载器短小清晰；容器只装配顶层，`Any` 与 per-file ignore 偏多 |
| 安全与依赖 | **部分通过** | `SecretStr` 与 repr 隔离有效，`pip-audit` 无告警；依赖安装证据与 pytest 版本不一致 |
| 性能 | **未评估** | 未做配置加载/容器解析基准；不阻塞本阶段 |
| 工程与流程 | **不通过** | `ruff format` 红；OpenSpec/文档晚于实现；PROMPT 缺原始 Prompt |
| 文档一致性 | **不通过** | README 仍 S00–S20；DESIGN 有字面 `\n\n` 且全链路声明与实现矛盾；OpenSpec 缩窄范围 |

## 5. 分级问题清单

### P1-01 — ToolConfig 只加载不生效：启停、沙箱根、大小上限、search provider 全部被忽略

- **位置**：`agent_mini/config/models.py:54-60`；`agent_mini/config/container.py:102-112`；`agent_mini/tools/registry.py:98-101`；`agent_mini/tools/builtin/search.py:69-75`。
- **问题**：`ToolConfig` 的 `enabled`、`sandbox_root`、`max_file_size`、`search_provider` 都能从 YAML/env 解析，但 `_build_agent` 只做 `RegistryExecutor(DEFAULT_REGISTRY)`，没有传 `ToolContext`、没有用 enabled 映射重建注册表、没有调用 `configure_search_provider`。探针在 `enabled=False`、`sandbox_root=<tmp>`、`max_file_size=123`、`search_provider="probe"` 下仍得到 6 个工具 Schema；`read_file` 返回 `missing_sandbox_root`；`search` 返回 `not_configured`。
- **判定依据**：FR-CFG-02 明确要求工具启停与工具级参数可配置；DESIGN §3.3 要求 `ToolContext.sandbox_root` 提供沙箱根；当前配置字段只停留在模型层，生产 Agent 完全看不到。
- **建议方向**：按 `ToolConfig` 构造 `ToolRegistry(enabled=...)` 或从默认注册表筛选；把 `sandbox_root/max_file_size` 写入 `ToolContext` 并传给 `RegistryExecutor`；按 `search_provider` 选择/注入 SearchProvider。补“配置 false 时无工具”“沙箱配置生效”“search provider 生效”的集成测试。

### P1-02 — Container 只装配 LLM/Agent/APP，Memory、ContextBuilder、SystemDB、Redis/Mongo 均未接入

- **位置**：`agent_mini/config/container.py:20-26,80-118`；`agent_mini/runtime/agent.py:30-82`；`Docs/DESIGN.md:375`；`Docs/TESTING.md:114`。
- **问题**：`Service` 只有 `CONFIG/LLM/AGENT/APP`，`build_container` 只注册这四个工厂。探针显示 `Agent` 的 `_context_builder=None`、`_system_prompt=None`、`_system_db=None`、`_short_term=None`、`_mid_term=None`；`SystemDBConfig`、`redis_url`、`mongo_uri` 虽被加载却从未消费。`/healthz` 因此返回空依赖。TC-L1-018 要求“已注册 LLM 与 Memory 的假实现”，但容器没有 Memory 键，`_build_agent` 也不注入 `short_term`/`mid_term`，测试无从注入。
- **判定依据**：FR-CFG-03 要求 system prompt 外置文件生效；FR-CFG-04 要求按配置装配组件且测试可替换；DESIGN §3.8 明确列出 `LLMClient、ToolRegistry、Memory、ContextBuilder、SystemDB、Agent`。当前只完成 LLM/Agent，属于核心交付缺失。
- **建议方向**：为 ToolRegistry/Memory/ContextBuilder/SystemDB 增加服务键与工厂；在 `_build_agent` 中调用 `with_context`、`with_system_db`、`with_mid_term`、构造 short_term 并传入；读取 system prompt 文件；为 Redis/Mongo/MySQL 生成健康检查。补“override 假 LLM+假 Memory 后 Agent 依赖为替身”“工厂应用具备上下文/记忆/审计”的集成测试。

### P1-03 — `ModelConfig.retry` 被静默忽略，重试次数不可配置

- **位置**：`agent_mini/config/models.py:36`；`agent_mini/config/container.py:90-99`；`agent_mini/llm/client.py:33-34,90-106`。
- **问题**：`ModelConfig.retry` 可解析（默认 2、范围 0–5），但 `_build_llm` 只把 base_url/model/timeout 传给 `ClientConfig`，没有创建 `RetryPolicy`。探针配置 `retry=1`，客户端 `_max_attempts` 仍为默认 3。另有一个潜在冲突：配置允许 0–5，而 `RetryPolicy` 只接受 1–3；一旦接上就会对 0/4/5 抛异常。
- **判定依据**：FR-LLM-05 与 FR-CFG-01 都要求“重试次数可配置”；当前字段存在但没有行为，属于静默失效。
- **建议方向**：把 `retry` 映射为 `RetryPolicy(max_attempts=...)`，并将模型校验范围收紧到 1–3；补 `retry=1` 时只发一次请求、`retry=3` 时最多三次的契约测试。

### P1-04 — 非法 env/YAML 类型不抛 `ConfigError`，部分非法配置被静默接受

- **位置**：`agent_mini/config/loader.py:69,73-74,81-82,87-94`。
- **问题**：`_Env` 在 `try` 之外构造，`MYSQL_POOL_SIZE=abc`、`DEEPSEEK_TIMEOUT=abc`、`MYSQL_AUTO_CREATE=notabool` 直接抛 pydantic `ValidationError`；`model: not-a-map`、`systemdb: not-a-map` 在 `dict(...)` 处抛原生 `ValueError`；`tool: not-a-map`、`prompt: not-a-map` 被 `_merge_tool/_merge_prompt` 静默当作空映射，使用默认值继续启动。
- **判定依据**：OpenSpec `config` 规范要求“必填项缺失/类型或枚举非法时抛 ConfigError”；AC-13 要求配置缺失或非法时启动失败并给出可定位错误。当前错误类型不统一，且部分非法配置根本不会失败。
- **建议方向**：把 `_Env` 构造、YAML section 类型检查、`AppConfig` 校验统一包进 `ConfigError` 转换；对 `model/tool/prompt/systemdb` 强制 mapping；为每个非法 env 类型和非法 section 类型补用例。

### P1-05 — 真实 `ContextTooLarge.trace` 触发 500，部分工具链上下文溢出无法返回 400

- **位置**：`agent_mini/interface/http.py:194-200,246-259`；`agent_mini/context/window.py:30-32`；`agent_mini/runtime/loop.py:142-146`。
- **问题**：S20 为 ContextTooLarge 增加 `steps/trace/truncated` 响应字段，但 `_error` 把 `exc.trace` 直接放进 `JSONResponse`。循环中 `exc.trace` 是 `ThoughtStep` Pydantic 对象，不是 dict；探针中真实 trace 导致 JSON 序列化 `TypeError`，最终返回 500 `INTERNAL`，而不是 400 + 证据。S20 测试用 `error.trace = ({"step": 1},)` 的假 dict 避开了该问题。
- **判定依据**：FR-IF-04 要求上下文过大映射 400；TC-L4-012 要求 `CONTEXT_TOO_LARGE` 与 trace_id；DESIGN §3.5 要求错误响应带脱敏 trace、steps、`truncated=true`。该路径一旦在工具执行后触发，客户端得到 500，且实际证据丢失。
- **建议方向**：序列化前对每个 trace 项调用 `model_dump(mode="json")`（或统一用 `to_error_response` 接受模型并转换）；新增“工具已执行后仍超预算”的集成用例，断言 400 与完整 trace。

### P1-06 — `ruff format --check` 失败，静态门禁未通过

- **位置**：`agent_mini/llm/errors.py:1`；`agent_mini/tools/sandbox.py:1`；`tests/integration/test_http_flows.py:1`（UTF-8 BOM）；`agent_mini/tools/registry.py:13,200`（空行）。
- **问题**：`ruff check` 通过，但 `ruff format --check` 报 4 个文件需重排；S20 修复与 S21 的 `test_http_flows` 编辑引入了 BOM，S21 未清理。OpenSpec tasks 2.1 与 PLAN 仍把 S21 标为完成。
- **判定依据**：AGENT §2.2、§10 与 PLAN §5.1 DoD 要求提交前静态检查全绿；最终阶段以红门禁归档会使 M4 结论不可信。
- **建议方向**：去掉 BOM、执行 `ruff format`；把 `ruff format --check` 与 `ruff check` 一起纳入阶段门禁，重新跑全量后再勾选 tasks。

### P2-01 — 启动契约与 README 冲突：强制 MYSQL_DSN 但未使用，失败时输出完整堆栈

- **位置**：`agent_mini/config/loader.py:70-72,105-111`；`agent_mini/interface/http.py:80-85`；`README.md:3,55-57`；`agent_mini/config/container.py:102-118`。
- **问题**：`load_config` 把 `MYSQL_DSN` 列为必填，但容器从未创建 SystemDB；README 的 HTTP 快速开始只要求设置 `DEEPSEEK_API_KEY`，按文档执行会得到 `ConfigError: 配置缺失: MYSQL_DSN`。直接运行 uvicorn 时，工厂异常打印完整 Python 堆栈，违反 TC-L4-006 “不产生堆栈噪声”。同时 `/healthz` 返回空依赖，无法反映 Redis/Mongo/MySQL 状态。
- **判定依据**：FR-SYS-05 要求 MySQL 不可用不影响主链路；AC-19 要求系统库不可用时对话仍可完成；TC-L4-006 要求启动失败信息可定位且无堆栈噪声；FR-IF-03 要求健康检查反映依赖连通性。
- **建议方向**：要么把 SystemDB 配置改为可选并真正接入降级，要么在 README/.env.example/设计中明确它是启动必填并说明原因；为 uvicorn 工厂提供捕获 `ConfigError` 的启动包装（打印单行错误、退出码非 0）；按已配置依赖生成 health checks。

### P2-02 — 新增测试没有覆盖装配、retry、非法配置和真实 Context 路径

- **位置**：`tests/unit/test_config.py:104-108`；`tests/integration/test_http_flows.py:192-195`；`tests/unit/test_config.py:42-54`。
- **问题**：`test_build_container_tops` 只断言 config 同一性与 agent 瞬时，不检查 LLM/工具/Prompt/Memory/SystemDB 依赖；`test_env_factory_requires_key` 删除 `DEEPSEEK_API_KEY` 后，`.env` 仍提供 Key，实际因缺少 `MYSQL_DSN` 而通过，测试名与失败原因不符；没有 `retry`、非法 env 类型、非法 YAML section、成功 `create_app_from_env`、真实 `ThoughtStep` Context 的用例。
- **判定依据**：TC-L1-018 要求“LLM 与 Memory 的假实现”可注入；TC-L4-006 要求启动失败行为；当前测试只验证了解析和通用容器，未验证 S21 的核心装配语义。
- **建议方向**：补容器依赖断言、override 后 Agent 使用假 LLM/Memory、retry 请求次数、非法配置矩阵、成功工厂启动与真实 Context 证据的集成用例。

### P2-03 — 文档漂移：README 仍 S00–S20、DESIGN 字面 `\n\n` 且全链路声明与实现不符、OpenSpec 缩窄

- **位置**：`README.md:3,55-57`；`Docs/DESIGN.md:375`；`openspec/changes/archive/2026-10-24-s21-config-di/design.md:10`；`openspec/changes/archive/2026-10-24-s21-config-di/specs/config/spec.md:12-19`。
- **问题**：README 仍写“当前完成 S00–S20”；DESIGN §3.8 宣称容器装配 `ToolRegistry/Memory/ContextBuilder/SystemDB`，与实际只装配 LLM/Agent/APP 矛盾，并在同一行留下字面 `\n\n**S21 实现**`；OpenSpec change 的 design 只写“装配 LLM/Agent/HTTP app”，spec 只要求 LLM override，未覆盖 Tool/Prompt/Memory/SystemDB，属于用缩小后的 change 通过归档。
- **判定依据**：AGENT §1 文档优先与 §7 需求驱动；PLAN S21 验收要求“模型/工具/Prompt 三类配置可加载并校验；容器可装配全链路”；设计/规范不得低于上位需求。
- **建议方向**：更新 README 到 S21 与真实启动步骤；修复 DESIGN 字面转义并如实描述已装配范围；把 Tool/Prompt/Memory/SystemDB 纳入 change/spec 或明确记录未完成项。

### P2-04 — 阶段流程与依赖证据不成立：PROMPT 无原始 Prompt、OpenSpec 晚于代码、ISSUE-025 关闭证据不足

- **位置**：`Docs/PROMPT.md:2344-2347`；提交 `bf99a70`/`9b511b1` 早于 `3fddcc8`；`Docs/ISSUE.md:288-296`；`pyproject.toml:10-30`；`tests/unit/test_config.py`。
- **问题**：S21 的 PROMPT 条目只有“执行摘要/验收”两行，没有原始 Prompt、任务目标、关键约束、人工修正与关联提交，按 AGENT §3 属于不合格；OpenSpec change 只在最终归档提交 `3fddcc8` 出现，编码前没有 change；tasks 2.1 在 `ruff format` 失败时仍勾选。ISSUE-025 宣称已重新解析依赖，但当前环境 `pytest 9.0.2` 与声明的 `<9` 冲突，`pip show agent-mini` 的 Requires 仍只有 `httpx,pydantic`，新增 `pydantic-settings`/`PyYAML` 未在提交说明中声明。
- **判定依据**：AGENT §1.1、§2.2、§3.4–3.5、§6.1、§9.5；PLAN §5.1 DoD。最终阶段以“已完成”记录这些证据，审计不可复现。
- **建议方向**：按模板补原始 Prompt；后续阶段先建 change 再编码；在干净环境重新 `pip install -e .` 并确认 pytest 8.x；把新依赖与上界决策写入提交说明/设计/ISSUE；门禁全绿后再勾选 tasks。

### P3-01 — 死代码与可读性：未使用常量、`__import__` logger、`_builtin` 占位、未使用的 `version`

- **位置**：`agent_mini/interface/http.py:31-35`；`agent_mini/config/models.py:95`；`agent_mini/config/container.py`（大量 `Any` 与 per-file ignore）。
- **问题**：`DEFAULT_BASE_URL`、`DEFAULT_MODEL`、`DEFAULT_TIMEOUT_SECONDS` 在工厂迁移后已无引用；`LOGGER` 仍通过 `__import__("logging")` 获取；`_ = _builtin` 保留为导入副作用占位；`AppConfig.version` 未被使用。它们不影响功能，但增加维护噪声。
- **判定依据**：AGENT §2 可维护性；配置收口阶段应清理迁移遗留。
- **建议方向**：删除死常量，直接用 `logging.getLogger`；显式注释 builtin 注册副作用或移除；确认 `version` 的用途或删除。

## 6. 需求—实现—测试追溯

| 需求 / 用例 | 实现 | 自动化证据 | 结论 |
| --- | --- | --- | --- |
| FR-CFG-01 / TC-L1-017 | ModelConfig + loader + SecretStr | `test_config.py` 解析/缺失/枚举用例 | **部分通过**：解析与缺失通过；非法 env 类型不转 ConfigError；retry 未生效 |
| FR-CFG-02 / TC-L1-017 | ToolConfig 字段 | 无工具装配断言 | **不通过**：字段齐全但不影响工具 |
| FR-CFG-03 / TC-L4-006 | PromptConfig 字段 | 无 system prompt 装配断言 | **不通过**：路径未读取，Agent 无 system prompt |
| FR-CFG-04 / TC-L1-018 | Container 工厂/singleton/transient/override | 通用容器测试、LLM override 探针 | **部分通过**：通用容器与 LLM override 可用；无 Memory/Tool/Context/SystemDB 装配 |
| FR-LLM-05 | base_url/model/timeout 已传，retry 未传 | 无 retry 测试 | **部分通过**：前三项生效，retry 静默失效 |
| AC-13 / TC-L4-006 | 缺字段 ConfigError；uvicorn 堆栈 | 仅有缺字段异常测试 | **不通过**：非法类型错误类型不对；启动有堆栈噪声；README 步骤失败 |
| FR-SYS-05 / AC-19 | MYSQL_DSN 必填但 SystemDB 未装配 | 无 | **不通过**：MySQL 能力不可用且启动被硬绑定 |
| NFR-TEST-01 / AC-16 | 94.85%，config 模块 >80% | 全量覆盖率 | **数值通过、行为覆盖不足** |
| NFR-SEC-02 / AC-14 | SecretStr 与 repr 隔离 | `test_config.py` repr 断言 + S19 安全 E2E | **通过（S21 范围）**：未发现新的密钥泄漏 |

## 7. 边界抽查

| 探针 | 结果 | 判定 |
| --- | --- | --- |
| 容器服务键 | 只有 `config/llm/agent/app` | 全链路缺失 |
| Agent 装配 | context_builder/system_prompt/system_db/short_term/mid_term 全为 None | 全链路缺失 |
| `retry=1` | 客户端 `_max_attempts=3` | 配置被忽略 |
| `enabled=False` + 4 个工具参数 | 仍返回 6 个 Schema；read_file `missing_sandbox_root`；search `not_configured` | 工具配置未生效 |
| `MYSQL_POOL_SIZE=abc` | pydantic `ValidationError` | 错误类型错误 |
| `model: not-a-map` | 原生 `ValueError` | 错误类型错误 |
| `tool: not-a-map` / `prompt: not-a-map` | 静默使用默认值 | 非法配置未拒绝 |
| 仅设置 API Key 启动 | `ConfigError: 配置缺失: MYSQL_DSN` + uvicorn 完整堆栈 | 快速开始失败、堆栈噪声 |
| 合法 env 的 `/healthz` | 200，`dependencies={}` | 健康检查为空 |
| 真实 `ThoughtStep` ContextTooLarge | 500 `INTERNAL`，`TypeError` | 错误路径回归 |
| `pip show agent-mini` | Requires 仍只有 httpx/pydantic | 依赖证据陈旧 |
| wheel 构建 | 含 `agent_mini/config/*` 与新增 Requires-Dist | 通过 |

## 8. 技术债与后续影响

1. 配置“能解析”不等于“能装配”。在补齐 Tool/Prompt/Memory/Context/SystemDB 之前，最终工厂应用实际退化为“无沙箱、无系统提示词、无记忆、无上下文裁剪、无审计”的单轮 HTTP 包装。
2. 容器只装配顶层组件会让 S21 的 DI 变成表面能力：`override` 只能替换 LLM，无法替换 TC-L1-018 要求的 Memory；后续新增组件仍要改业务代码。
3. `retry` 字段与 `RetryPolicy` 的取值范围不一致（0–5 vs 1–3），接线前必须先统一，否则配置 0/4/5 会在启动或首次请求时失败。
4. 配置错误统一转 `ConfigError` 是 AC-13 的基础；当前 pydantic 异常与原生 `ValueError` 会泄漏实现细节，也不利于 CLI/运维定位。
5. `ContextTooLarge` 的部分 trace 必须显式序列化；否则“工具执行后超预算”这一真实路径会从设计的 400 变成 500。
6. 依赖上界已写入 `pyproject.toml`，但当前环境和 editable 元数据没有重新解析；ISSUE-025 的关闭状态应先由干净安装复验。
7. M4 仍未执行真实 API（LIVE 0 个用例）和真实 MySQL（skip）；即使 S21 代码补齐，也不能直接宣布 v0.1 可交付。

## 9. 总体门禁结论

**S21 不通过；S21 不可收口，M4/v0.1 不可交付。**

进入下一阶段/发布前至少必须：

1. 关闭 P1-01：让 `ToolConfig` 的启停、沙箱、大小上限、search provider 真正进入 Agent 的工具执行路径。
2. 关闭 P1-02：按配置装配 ToolRegistry、Memory、ContextBuilder、SystemDB（含 Redis/Mongo），并让 TC-L1-018 的 Memory 替身可注入。
3. 关闭 P1-03：把 `ModelConfig.retry` 接到 `RetryPolicy`，统一 1–3 的取值范围并验证请求次数。
4. 关闭 P1-04：所有非法 env/YAML 类型统一转 `ConfigError`，非法 section 不得静默回退。
5. 关闭 P1-05：真实 `ThoughtStep` 的 ContextTooLarge 响应必须 400 且携带序列化后的 trace/steps/truncated。
6. 关闭 P1-06：清理 BOM/格式并让 `ruff format --check`、`ruff check`、mypy、OpenSpec、全量测试全部通过。
7. 关闭 P2-01/P2-02/P2-03/P2-04：修正启动与 README/健康检查契约、补齐装配测试、修复文档与 PROMPT/依赖证据。
8. 之后仍需 LIVE-001/002（及思考模式 003）、真实 MySQL 与 POSIX 验收，才能讨论 M4。

## 10. 工作区状态与副作用

- 评估开始时工作区干净，`HEAD`、`main`、`origin/main` 均为 `3fddcc8`；未提交、未推送、未修改远程状态。
- 按只读评估边界，仅新增本报告并向 `Docs/PROMPT.md` 追加本次原始 Prompt 与摘要。
- 全量测试、覆盖率、静态检查、OpenSpec、构建、uvicorn 失败启动与探针更新了常规缓存和被忽略的 `build/`、`dist/`、`.coverage`、`.pytest_cache/`、`.ruff_cache/`、`.mypy_cache/`、`agent_mini.egg-info/`；未做破坏性清理。
- 探针临时脚本位于 `%TEMP%\s21_probe.py`，评估结束后删除；未创建后台服务或持久化配置。
- 未调用 DeepSeek API，未读取或输出 `.env` 中的真实密钥值；所有安全/配置探针均使用假值。
- `pip-audit` 未发现已知漏洞；`pip check` 的系统级 `opentelemetry` 冲突与项目依赖无关，未作为 S21 缺陷。

## 11. 修复记录（2026-10-25）

| 报告项 | 修复 |
| --- | --- |
| P1-03 retry | 配置范围收紧 1–3，容器映射 `RetryPolicy(max_attempts)`；测试 `retry=1` |
| P1-04 非法 env/YAML | `_Env` ValidationError 转 ConfigError；`model/tool/prompt/systemdb` 强制映射 |
| P1-05 Context trace 500 | `ThoughtStep.model_dump(mode=json)` 序列化；真实 ThoughtStep 测试 400 |
| P1-06 format 门禁 | 清理 BOM/空行，`ruff format --check` 通过 |
| P1-01 ToolConfig | `enabled=False` 空注册表；sandbox_root/max_file_size 注入 ToolContext；测试生效 |
| P1-02 Memory/Context/SystemDB 装配 | **未修复**，仍仅 LLM/Agent/App |
| P2-01 启动/MYSQL | 未改；MYSQL_DSN 仍必填，README 已指明 |
| P2-03 文档 | README S21、DESIGN 字面 \\n、TESTING 计数 |

**复验**：376 passed、2 skipped；unit 219、contract 64、integration 93；覆盖率 **94.93%**；ruff/mypy 通过。

## 12. 修复记录（2026-10-25）

- 容器新增 short/mid/systemdb/context 服务；Agent 注入 short_term/system_db/context；Prompt 文件可读。
- `/healthz` 注入 redis/mongo/mysql 检查（Redis/Mongo 仅配置 URL 时）。
- Docker 真机：MySQL 8 用例 8 passed；Linux/Python 3.11 POSIX 22 passed、1 skip。
- POSIX `write_file`：`os.replace`、发布失败不误报 path_escape、FileExists 临时文件清理。
- 复验：377 passed、2 skipped；unit 220、contract 64、integration 93；覆盖率 94.56%。
- 未关闭：search_provider、health 超时、M3 独立复验、LIVE、P2 其余项。

## 13. search provider 阶段决策（2026-10-25）

- 当前阶段仅 mock：`none` 返回 `not_configured`；`mock` 返回确定性本地结果。
- 不接真实搜索 API；`ToolConfig.search_provider` 限定 `none|mock`，支持 `SEARCH_PROVIDER` 环境变量。
- 复验：378 passed、2 skipped；unit 221；覆盖率 94.58%。

## 14. 收尾（2026-10-25）

- health：异步/同步检查线程化、2s 超时、空依赖 degraded；容器注入 mysql/redis/mongo。
- 启动：`agent-mini` console script 捕获 ConfigError，单行 stderr、退出码 2、无 Traceback。
- 381 passed、2 skipped；unit 222、contract 64、integration 95；覆盖率 94.56%。

## 15. 收尾二（2026-10-25）

- S20 异常堆栈 JSON 化并脱敏，补测试。
- S19 仓库扫描测试；MySQL 审计扫描仍缺。
- M3 只读复验 51 passed，记录于 M3-review；非独立评审。
- 383 passed、2 skipped；覆盖率 94.57%。

## 16. LIVE 与 Docker 组件（2026-10-25）

- `.env` 提供 Key；`RUN_LIVE=1 pytest tests/live -q` → 3 passed。
- MySQL/Redis/Mongo 容器均 Up；health 探针三项 ok。
- `RUN_LIVE=1` 全量 386 passed、2 skipped；覆盖率 94.53%。

## 17. 真实 MySQL/Redis/Mongo（2026-10-25）

- MySQL 审计：真实五表哨兵扫描通过。
- Redis/Mongo：真实记忆往返通过。
- 全部 Docker + LIVE：390 passed、1 skipped；默认 383 passed、8 skipped；覆盖率 94.76%。

## 18. 构建与跨版本（2026-10-25）

- wheel 构建成功，仓库外 target 导入成功。
- Python 3.11 全量（Docker + 三服务 + LIVE）：390 passed、2 skipped。
- 本机 Docker+LIVE 全量：391 passed、1 skipped；覆盖率 94.76%。
- S17 五表真实链路测试通过。

## 19. M3 P1 修复（2026-10-25）

- trim_reason=None、跨存储顺序、ensure_indexes、include_reasoning=False。
- Mongo 脏文档逐条跳过。
- M3 用例 51 passed；全量 Docker+LIVE 391 passed、1 skipped；覆盖率 94.60%。

## 20. 最终复核（2026-10-25）

- 独立子代理确认跨存储 A/B 故障路径闭合；M3 53 passed。
- Python 3.11 全量 392 passed、2 skipped；wheel 重建并仓库外导入成功。
- 本机 Docker+LIVE 393 passed、1 skipped；覆盖率 94.62%。

## 21. M3 P2/P3 收尾（2026-10-25）

- 真实 Redis+Mongo+ContextBuilder 链路通过。
- search_rounds 自动建索引；Agent.close 关闭客户端。
- 重复 build/fit 因 deadline 语义回退，保留 P3。
- 395 收集；Docker+LIVE 394/1；Python 3.11 393/2；覆盖率 94.72%。
