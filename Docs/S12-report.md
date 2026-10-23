# S12 阶段代码产出独立评估报告

> 评估时间：2026-10-23 15:49（Asia/Shanghai）
> 基准提交：`f0f96ed`（`main` 与 `origin/main` 一致）
> 评估方式：独立只读复核；除本报告与 `Docs/PROMPT.md` 记录外，不修改实现、测试、OpenSpec 或远程状态
> 结论：**不通过；S12 暂不可进入 S13，M2 不满足完成定义**  
> 修复状态：见 §10；S12/M2 已恢复准入

## 1. 评估范围与基准

实际读取并交叉核对：

- `AGENT.md` §1–§10，重点是文档优先、TDD、Prompt 时机、Commit、OpenSpec、阶段 DoD 与评估报告归档。
- `Docs/PLAN.md` S11、S12、S13、§4 M2、§5 DoD 与阶段进度表。
- `Docs/REQUIREMENT.md` FR-TOOL-01、FR-TOOL-08、NFR-TEST-01。
- `Docs/DESIGN.md` §1.1/1.3、§2.2、§3.3、§4、§6、§7 ADR-009、§8、§9、变更记录 v0.27。
- `Docs/TESTING.md` TC-L1-021、TC-L3-006、S12 覆盖边界、§5–§6。
- `Docs/PROMPT.md` S11 修复与 S12 执行记录；`Docs/ISSUE.md` ISSUE-038/039；`MEMORY.md` S12/M2；`README.md` 安装、测试与演示说明。
- `agent_mini/tools/registry.py`、`agent_mini/tools/builtin/__init__.py`、`search.py`、`write_file.py` 与六个 builtin 模块。
- `tests/unit/test_search_tool.py`、`test_write_file.py`、`test_package_skeleton.py`、各 builtin 测试与 Registry/Runtime 集成测试。
- `pyproject.toml`；`openspec/specs/search/spec.md`、`engineering-standards/spec.md`；归档 change `2026-10-23-s12-tool-search` 的 proposal/design/tasks/spec。
- S11 报告修复提交 `84a5add`、`41065ae`、`31a8344`、`3dc1b2c`；S12 提交 `3617c1e`、`b7eb3c9`、`5d2b7cb`、`f0f96ed`。

基准文档存在四处直接不一致或缺口：

1. `PLAN` S12 与 FR-TOOL-08 把 search 映射到 TC-L3-006，但该 TC 的完整定义是 mock LLM 调用 calculator；仓库也没有对应的 calculator Agent 集成测试。`TESTING` 已承认错配，ISSUE-039 仍为 Open，阶段却被标为完成。
2. `PLAN`、`README`、`MEMORY` 宣称 M2“六个工具注册可用”，但干净进程导入 `agent_mini.tools.builtin` 后 `DEFAULT_REGISTRY.schemas()` 仍为空；测试通过依赖各测试模块逐个导入 builtin 的副作用。
3. M2 DoD 要求可运行命令与可复现演示步骤，README 只有 M1 演示，没有 M2 演示。
4. ISSUE-038 与 S11 报告宣称父目录替换逃逸已修复，但修复只增加发布前的字符串路径复核；复核后到 `os.replace`/`os.link` 之间仍有竞态窗口，本次已再次真实写到沙箱外。

## 2. 复核命令与结果

| 命令/检查 | 结果摘要 |
| --- | --- |
| `git status --short --branch`、`git rev-parse HEAD origin/main` | 评估前为干净的 `main...origin/main`；两者均为 `f0f96ed` |
| `git log/show/diff --check` | OpenSpec 计划提交在实现前；实现与测试同 commit；S12 feat 正文单行 138 字符、文档正文单行 81 字符；文档提交有 4 个 EOF 空行告警 |
| `pytest -q --disable-warnings --maxfail=1` | **258 passed** |
| `pytest -q --cov=agent_mini --cov-report=term --cov-fail-under=90` | **258 passed，96.99%**；search 模块 96% 行覆盖 |
| `pytest --collect-only -m unit/contract/integration/e2e` | unit 194、contract 64；integration/e2e 均无用例 |
| `ruff check .` | 通过，零告警 |
| `ruff format --check .` | 通过，66 files already formatted |
| `mypy agent_mini tests` | 通过，63 source files，0 errors |
| `openspec validate --all --strict` | **12 passed，0 failed**；engineering-standards 有既有 INFO 长度提示 |
| `pip wheel . --no-deps` | 成功生成 `agent_mini-0.1.0-py3-none-any.whl`；wheel 含 search 与 `systemdb/schema.sql` |
| wheel 安装到临时 target 后仓库外 `python -I` 导入 | 通过；导入路径来自临时安装目录，package-data 可读 |
| Python 3.11.14 新 venv 安装 wheel + `[dev]`、`pip check` | 安装成功，无依赖冲突；只复制 tests 的 wheel-only 全量首次在 `test_package_skeleton` 失败，因为该测试硬编码仓库源码目录 |
| Python 3.11.14 临时干净源码副本全量测试 | **258 passed**，证明最低 Python 版本可复现；wheel-only 测试限制见上项 |
| 干净进程注册探针 | 只导入 registry 时 0 个工具；再导入 `agent_mini.tools.builtin` 后仍为 0 个 |
| provider 畸形字段探针 | `SearchResult.snippet=123` 泄漏 `TypeError`；缺少 `name` 泄漏 `AttributeError`，均未返回 `provider_result_invalid` |
| provider 并发换配探针 | A provider 返回的结果被输出为 `provider-b`，结果来源与 provider 标签不一致 |
| S11 最终发布窗口探针 | 在最后一次 containment 检查后把父目录换为 root 外 junction；write_file 返回成功，root 外文件内容被改写 |

本次未复跑：

- TC-L3-006：仓库没有按其完整定义实现的 calculator Agent 集成用例；现有 `RegistryExecutor` 测试使用自建 echo 工具，不是 calculator，也不是 search。
- 真实 search provider/API：S12 明确非目标，未配置密钥、未访问真实网络。
- Linux 上的 junction/symlink 竞态：当前环境为 Windows；已用 Windows junction 对同一最终发布窗口完成真实复现。

## 3. 维度结论表

| 维度 | 结论 | 理由与证据 |
| --- | --- | --- |
| 需求与范围合规 | **有条件通过** | S12 只新增 search 抽象、测试与文档，未越界实现真实 provider、Memory、HTTP 或 DI；但 TC-L3-006 未覆盖、M2 收口声明不成立 |
| Provider 协议与未配置行为 | **通过** | `SearchProvider`/`SearchResult`/`NullProvider`、模块级注入及 5 秒超时已落地；TC-L1-021 与 fake 透传/空结果实跑通过，未配置不伪造结果 |
| 参数、结果与错误边界 | **不通过** | query/limit、provider 调用异常、超时和“错误 item 类型”可结构化；合法 dataclass 中的畸形字段、缺失/异常 name 会从 `_render` 直接抛异常，违反主规格 |
| 注册装载与 M2 可用性 | **不通过** | `builtin/__init__.py` 不导入任何工具且仍是占位文案；干净进程导入 builtin 后注册表为 0，无法得到文档宣称的六工具组合 |
| 数据模型与并发隔离 | **有条件通过** | frozen dataclass 足够表达结果；但运行期不校验字段，模块全局 provider 在并发换配时会错标来源，未来多请求环境存在串扰 |
| 测试质量 | **不通过** | 11 个参数化实例覆盖直接 handler 主路径，断言真实；但没有 Registry/Schema、组合装载、畸形字段/name、并发换配、总输出上限或真实集成测试 |
| 全局规范符合性 | **不通过** | ruff/format/mypy、命名、中文 docstring、无 noqa/type-ignore 均通过；Prompt 时机、TC 追溯、阶段/M2 DoD、S11 P0 前置门禁不符合 AGENT |
| 打包与分发 | **通过** | wheel 含新增模块与 schema.sql；仓库外隔离导入和 Python 3.11 安装通过，无未声明运行依赖 |
| 依赖审计 | **通过** | S12 未新增依赖；仅复用 asyncio/json/pydantic；无禁用 Agent 框架；现有 dev 工具有上界，pytest 仍只有下界 |
| 流程与文档闭环 | **不通过** | change 先于实现、strict 校验和归档通过；但 Prompt 在实现后提交，ISSUE-039 未闭环，M2/README/PLAN 与实际注册状态不一致 |
| 可复现性 | **有条件通过** | 当前环境与 Python 3.11 干净源码副本均 258 passed；wheel 外部导入通过；wheel-only 测试被源码布局测试限制，M2 组合运行无法复现 |
| 隐性风险与后续影响 | **不通过** | S11 沙箱 P0 仍存在；S18 并发会放大全局 provider 错标和写越界；S21 DI 接管前缺少清晰组合根与配置冻结边界 |

## 4. 问题清单

### P0

#### S12-P0-01 — S11 前置 P0 仍可在最终发布窗口写出沙箱

- **位置**：`agent_mini/tools/builtin/write_file.py:135-176`（`_atomic_write` / `_assert_inside`）；`tests/unit/test_write_file.py:166-186`；`Docs/ISSUE.md:459-467`；`Docs/S11-report.md:246-256`。
- **问题描述**：修复在 `os.replace`/`os.link` 前再次调用 `Path.resolve()`，但检查与发布仍是两个操作。探针在第 158 行检查返回后、发布调用内部把父目录移到 root 外并在原位置创建 junction；函数返回 `ok=True`，root 外目标被改写。现有 `test_parent_swap_before_publish_is_blocked` 只让 `mkstemp` 直接返回 root 外路径，并未模拟父目录交换，测试名称与真实竞态不一致。
- **判定依据**：FR-TOOL-06/07 要求沙箱内写入并阻断链接逃逸；`AGENT.md` §8.4 要求前置阶段未达 DoD 不得开启下一阶段；`Docs/PLAN.md:323` 要求里程碑无 P0/P1。ISSUE-038 的 Resolved 与可复现行为矛盾。
- **建议方向**：不要继续增加字符串路径复核次数；基于可信、已打开的目录句柄完成 no-follow 相对发布，或采用平台等价机制验证并锁定 reparse/symlink 组件；补“在最后一次校验之后、系统发布之前交换父目录”的确定性回归测试，并重开 ISSUE-038。

### P1

#### S12-P1-01 — M2 没有可复现的六工具装载入口

- **位置**：`agent_mini/tools/builtin/__init__.py:1`；`agent_mini/tools/__init__.py:1`；`agent_mini/tools/registry.py:176-201`；`Docs/PLAN.md:299,351`；`README.md:3`。
- **问题描述**：六个模块都依赖装饰器导入副作用注册，但生产导入图没有显式加载它们。干净进程导入 registry 后为 0 个，导入 builtin 包后仍为 0 个。全量测试之所以全绿，是测试收集逐个导入了工具模块，无法证明应用可用。PLAN/README 的“六个工具注册可用”“M2 已达成”与实际不符。
- **判定依据**：AGENT §1/§7 要求文档与实现一致、验收可追溯；§8 要求阶段可独立验收；PLAN §4 的 M2 达成标志就是六工具注册可用。
- **建议方向**：建立无隐式顺序依赖的显式 builtin 装载/注册组合根，并在全新解释器或 subprocess 中断言六个固定工具恰好一次可见、Schema 可生成、search 返回 not_configured；同步更新包 docstring 与 M2 状态。

#### S12-P1-02 — 畸形 provider 结果未稳定映射为 `provider_result_invalid`

- **位置**：`agent_mini/tools/builtin/search.py:26-33,97-103,106-132`（`SearchResult` / `search` / `_render`）；`tests/unit/test_search_tool.py:107-113`；`openspec/specs/search/spec.md:26-37`。
- **问题描述**：异常捕获只包住 provider 的 await；`_render` 仅校验 item 是 `SearchResult`，不校验四个字段与 provider name。运行期可构造 `snippet=int`、不可 JSON 序列化字段或缺少/抛异常的 name，分别泄漏 TypeError/AttributeError/序列化异常。现有“畸形结果”测试只传 dict，属于最浅分支。
- **判定依据**：search 主规格明确“畸形结果 → provider_result_invalid”；DESIGN §3.3 也把该错误码列为执行契约；AGENT §2 要求测试不能以单一自证样例代替完整行为边界。
- **建议方向**：在 provider 边界统一验证 provider name、序列类型、每项类型和四个字符串字段，再在同一结构化错误边界内渲染；补字段类型、序列化失败、name 缺失/抛错测试，并通过 Registry 执行验证不会退化为通用 `tool_execution_error`。

#### S12-P1-03 — TC-L3-006 错配未闭环却宣告阶段与 M2 完成

- **位置**：`Docs/PLAN.md:182-191,351`；`Docs/REQUIREMENT.md:199`；`Docs/TESTING.md:248-266`；`Docs/ISSUE.md:469-477`；测试目录全局搜索。
- **问题描述**：PLAN/FR 仍把 TC-L3-006 作为 S12 验收项；TESTING 定义的是 calculator Agent 集成，且仓库没有对应测试。ISSUE-039 状态仍为 Open，只把 search E2E 延后，却没有修正上游映射或阻止完成声明。
- **判定依据**：AGENT §1.3 要求每条验收标准对应测试；§7 要求 FR/TC 唯一可追溯；§8.4/§8.6 要求全部测试项和收口五件套完成后才能进入下一阶段。
- **建议方向**：为 search 建立独立 TC 编号并实现 Registry/Agent 层的 fake-provider 集成测试；TC-L3-006 保持 calculator 语义并补齐其测试或移出 S12；同步 PLAN、REQUIREMENT、TESTING、ISSUE 与进度状态。

#### S12-P1-04 — S12 Prompt 留痕提交晚于实现提交

- **位置**：提交 `b7eb3c9`、`5d2b7cb`；`Docs/PROMPT.md:1849-1865`；`Docs/ISSUE.md:459-467`。
- **问题描述**：S12 实现提交 `b7eb3c9` 不含 Prompt；Prompt 到下一笔文档提交 `5d2b7cb` 才进入历史。ISSUE-038 已明确“后续先留 Prompt 再提交”，S12 紧接着再次违反同一整改承诺。
- **判定依据**：AGENT §3 要求每轮原始 Prompt 在提交代码之前入库；§8.6 把 Prompt 记录列为阶段收口必需项。
- **建议方向**：如实记录本次历史偏差，不改写已推送历史；后续阶段把 Prompt 记录作为实现提交前的机械门禁，并在 commit/CI 检查本轮条目是否已存在。

#### S12-P1-05 — M2 缺少 DoD 要求的可运行演示

- **位置**：`Docs/PLAN.md:317-324`；`README.md:27-56`；`Docs/PLAN.md:299`；`MEMORY.md:3-8`。
- **问题描述**：PLAN §5.2 要求里程碑有可运行命令和可复现演示步骤；README 只有 M1 四项测试演示，没有 M2 六工具或 search 未配置演示。与此同时 PLAN/MEMORY 已标记 M2 收口。
- **判定依据**：AGENT §8.3/§8.4 与 PLAN §5.2；阶段和里程碑完成声明必须有可核对证据。
- **建议方向**：先修复组合装载，再增加无需网络的 M2 演示命令，覆盖六工具 Schema、至少一个真实执行路径、文件往返安全边界和 search not_configured；运行结果与预期写入 README 后再恢复 M2 完成状态。

### P2

#### S12-P2-01 — 模块级可变 provider 会造成并发结果来源错标

- **位置**：`agent_mini/tools/builtin/search.py:69-81,89-103,127-132`。
- **问题描述**：`search` 在 await 前通过全局 `_PROVIDER` 发起调用，await 后 `_render` 再读取当前全局 provider name。并发重配时，A 返回的结果会被标成 B；reset 时还可能标成 null。当前设计未声明 configure 只能在启动期调用，也未冻结请求级快照。
- **判定依据**：主规格要求配置后返回其结果与 provider 名称；DESIGN §8 把并发与第三方依赖失败列为风险；未来 S18 为并发 HTTP 入口。
- **建议方向**：每次调用开始时捕获局部 provider 快照，并用同一实例执行和渲染；S21 DI 时把 provider 变为应用级只读依赖，避免请求期全局变更；补 Event/barrier 驱动的确定性并发测试。

#### S12-P2-02 — SearchArgs Schema 未表达已实现的长度与范围约束

- **位置**：`agent_mini/tools/builtin/search.py:62-66`；`agent_mini/tools/registry.py:81-87`。
- **问题描述**：运行逻辑要求 query 非空且 ≤200、limit 1..10，但 pydantic 字段没有 min/max/max_length；输出 JSON Schema 只显示 string/integer/default。模型看不到约束，会产生本可在生成前避免的无效调用。
- **判定依据**：FR-TOOL-01 要求生成准确 JSON Schema；DESIGN §3.3 和 search 规格已经定义明确边界。
- **建议方向**：把可静态表达的限制放到 pydantic Field/StringConstraints，并保留领域错误映射策略；增加 Schema 断言与 Registry 无效参数测试。

#### S12-P2-03 — 结果先整体物化且标题/URL/source 无总量上限

- **位置**：`agent_mini/tools/builtin/search.py:106-132`（`_render`）。
- **问题描述**：`list(raw)` 会在截取 limit 前复制 provider 的全部 Sequence；只截断 snippet，不限制 title/url/source/provider 字符串或最终 JSON 大小。错误或恶意 provider 可造成内存放大并把超大工具结果送入后续上下文。
- **判定依据**：DESIGN §8 的外部依赖/上下文风险；S16 将对工具结果实施裁剪，S12 应至少避免无界预物化。
- **建议方向**：明确 provider 返回规模契约；只消费 `limit + 1` 个结果或要求受限 Sequence，给单字段与总输出设置可配置上限，并用超大/长字段测试验证稳定截断语义。

#### S12-P2-04 — 测试只覆盖直接 handler，未证明 Registry 与组合链路

- **位置**：`tests/unit/test_search_tool.py:38-133`；`tests/unit/test_tool_registry.py:172-188`。
- **问题描述**：search 的全部测试直接调用函数；没有 `DEFAULT_REGISTRY.execute("search", ...)`、Schema、额外字段拒绝或 Agent→Registry→search 测试。现有 Runtime 集成只用局部 echo registry，不能证明 S12 组合可用。
- **判定依据**：PLAN S12 的“配置后透传”与 M2“注册可用”；AGENT §2 要求测试断言真实执行路径。
- **建议方向**：补干净 registry/显式 loader、Schema、Registry execute、Agent fake-provider 集成用例；避免依赖 pytest 收集顺序预热全局注册表。

#### S12-P2-05 — Commit/Markdown 格式与包说明仍有审计噪声

- **位置**：提交 `b7eb3c9`、`5d2b7cb`；`agent_mini/tools/__init__.py:1`；`agent_mini/tools/builtin/__init__.py:1`；`README.md:57-58` 等。
- **问题描述**：S12 feat 正文单行 138 字符，docs 正文单行 81 字符，超过 AGENT 的 72 字符；文档提交产生多个 EOF 空行；tools/builtin 包仍自称“占位/待 S06–S12 落地”。
- **判定依据**：AGENT §5.2；engineering-standards 的注释不过期与文档一致性要求。
- **建议方向**：后续提交正文按 72 字符换行；统一 Markdown 单个 EOF 换行；把包 docstring 更新为当前职责，不用 docstring 修复掩盖装载入口缺失。

### Info

#### S12-INFO-01 — 未配置与 fake provider 主路径实现清晰

- **位置**：`search.py`、`test_search_tool.py`、search 主规格。
- **观察**：默认 NullProvider、显式 not_configured、禁止伪造、async timeout、异常码、结果/摘要截断与空结果成功均有简洁实现和有效断言。
- **建议**：修复边界时保留现有错误码和无真实网络的可测结构。

#### S12-INFO-02 — 范围与依赖控制良好

- **位置**：S12 四个提交、`pyproject.toml`、归档 proposal/design。
- **观察**：没有实现真实搜索 SDK/API Key/环境变量读取，没有新增运行依赖，也没有触碰 Memory、HTTP、配置容器或禁用 Agent 框架。
- **建议**：真实 provider 继续留到有明确需求、密钥和网络验收的后续 change。

#### S12-INFO-03 — wheel 内容与最低 Python 版本可复现

- **位置**：`pyproject.toml` package discovery/package-data；构建与 Python 3.11 临时环境记录。
- **观察**：search.py 和 schema.sql 均进入 wheel；仓库外导入、pip check、Python 3.11 干净源码全量 258 项均通过。
- **建议**：若要直接对已安装 wheel 跑测试，需把源码结构检查与安装级测试拆开，避免 `test_package_skeleton` 假定仓库布局。

## 5. 需求—实现—测试追溯表

| FR / TC / 规格 | 实现位置 | 测试位置 | 覆盖 | 越界/缺口 |
| --- | --- | --- | --- | --- |
| FR-TOOL-08：provider 抽象 | `search.py:26-81` | `test_search_tool.py:19-35,47-58` | 基本覆盖 | 没有 Registry/Agent 集成；全局 provider 并发错标 |
| FR-TOOL-08：未配置明确失败 | `search.py:49-59,89-96` | `test_search_tool.py:38-45` | 是 | 无伪造结果，符合 TC-L1-021 |
| 主规格：参数/异常/超时 | `search.py:89-103` | `test_search_tool.py:70-104` | 是 | SearchArgs Schema 未表达范围；未配置优先于参数校验未明确 |
| 主规格：畸形结果 | `search.py:106-132` | `test_search_tool.py:107-113` | 部分 | 只覆盖非 SearchResult item；字段/name/序列化异常会泄漏 |
| 主规格：截断/空结果 | `search.py:106-132` | `test_search_tool.py:61-67,116-133` | 是（声明范围） | 未限制 title/url/source/总输出，整体物化 raw |
| TC-L1-021 | `search` 的 NullProvider 分支 | `test_unconfigured_returns_not_configured_without_fake_results` | 是 | 断言 ok/error_code/无伪造文本，真实有效 |
| TC-L3-006 | 无 S12 search 实现映射；定义为 calculator Agent 集成 | 无对应完整测试；现有 echo Runtime 测试不等价 | 否 | 编号错配且 ISSUE-039 仍 Open |
| FR-TOOL-01 / M2 六工具注册 | 六个模块各自 `@tool` | 各模块测试靠导入副作用 | 否（组合） | 干净 import builtin 后 0 个；无显式装载入口 |
| NFR-TEST-01 / M2 覆盖率 | pytest-cov | 全量测试 | 是 | 96.99%，但行覆盖未发现协议/组合/并发缺口 |

## 6. 边界抽查结论

- **是否越界实现真实 provider、API Key、环境变量读取或真实网络：否。** S12 范围控制正确。
- **未配置时是否伪造搜索结果：否。** 返回 `not_configured`，测试确认无 URL/天气摘要。
- **配置 fake provider 后是否透传：普通路径是。** query/limit、URL、provider 名称和空结果有断言。
- **provider 调用异常/超时是否结构化：是。** 分别为 `provider_error`、`provider_timeout`。
- **所有畸形 provider 结果是否结构化：否。** dataclass 字段类型、provider name 与 JSON 序列化异常可直接抛出。
- **是否存在越界实现重试/退避/HTTP 状态分类：否。** search 只有单次 5 秒 timeout，不重试。
- **六个工具是否在干净进程中注册可用：否。** 导入 registry 或 builtin 包均为 0 个；必须逐个导入具体模块。
- **TC-L3-006 是否覆盖 search：否。** 它定义为 calculator Agent 集成，且完整测试也未落地。
- **S11 的 P0/P1 是否在 S12 开工前真实闭环：否。** 最终发布窗口仍可复现沙箱外写入，ISSUE-038 的 Resolved 结论不成立。
- **S00 占位测试如何处理 search：已把 search 加入结构清单和非占位集合。** 不是跳过断言；但 builtin 包自身 docstring 仍是过期占位文案。
- **M2 是否有 README 演示命令：否。** README 只有 M1 演示。
- **OpenSpec 是否先于实现并严格通过/归档：是。** `3617c1e` 在 `b7eb3c9` 前，当前 strict 为 12/12；但规格通过不能替代上游 TC 与 M2 DoD。

## 7. 技术债与后续阶段影响

| 后续阶段 | 风险 | 触发条件 | 建议处理时机 |
| --- | --- | --- | --- |
| S13 | 阶段门禁失真 | 在 S11 P0、S12 P1 未闭环时继续进入 Memory | **S13 前**恢复 ISSUE/PLAN 真实状态并修复阻断项 |
| S13/S16 | 超大搜索结果挤占或击穿上下文 | provider 返回超长 title/url/source 或巨大序列 | S16 裁剪前先在 S12 provider 边界设总量上限 |
| S18 | 沙箱外写入 | 并发 HTTP 请求或不可信本地进程交换父目录 | **S13 前修复 P0**；S18 再做并发 E2E |
| S18 | provider 来源错标/跨请求串扰 | 请求执行期间重配/reset 全局 provider | S18 前冻结调用级快照；S21 再由 DI 收口 |
| S18 | 工具列表为空 | HTTP 组合根只导入 builtin 包或 registry | **M2/S13 前**提供显式 loader 与 subprocess 测试 |
| S21 | 配置生命周期不清 | DI 容器接管 search provider，但保留可变模块全局 | S21 将 provider 作为应用级依赖注入，限制重配时机 |
| M2 回归 | pytest 顺序掩盖注册缺失 | 任一测试先导入所有 builtin 后再断言 registry | 立即采用全新进程测试，禁止共享全局状态自证 |

## 8. 总体结论

**S12 暂不可进入 S13，M2 不可视为达成。** Search 的核心单模块路径完成度较好：NullProvider、不伪造结果、fake 透传、超时/异常、截断与空结果均可用；258 项全量测试、96.99% 覆盖率、ruff/format/mypy、OpenSpec strict、wheel、仓库外导入和 Python 3.11 复现均通过。

但门禁结果不能抵消协议和组合缺陷：S11 的沙箱逃逸 P0 仍能在最终发布窗口复现；S12 没有生产可复现的六工具装载入口，畸形 provider 字段会泄漏异常，TC-L3-006 错配仍 Open，Prompt 再次晚于实现，M2 也没有演示命令。按 AGENT §8 和 PLAN §5，阶段与里程碑 DoD 均不成立。

进入 S13 前必须处理：

1. **S12-P0-01**：真正封闭 write_file 最终发布窗口的父目录 reparse/symlink 交换，并补对应竞态测试、重开并关闭 ISSUE-038。
2. **S12-P1-01**：提供显式六工具装载/注册组合根和干净进程测试，纠正 M2 完成声明。
3. **S12-P1-02**：让所有畸形 provider 结果稳定返回 `provider_result_invalid`，覆盖字段/name/序列化边界。
4. **S12-P1-03**：修正 TC-L3-006 映射，为 search 建立并落地独立集成 TC，闭环 ISSUE-039。
5. **S12-P1-04**：登记重复发生的 Prompt 时序偏差，并把后续 Prompt 先行变为提交门禁。
6. **S12-P1-05**：补可运行、可复现的 M2 演示后再标记里程碑完成。

可选建议：冻结 provider 调用快照；让 SearchArgs Schema 表达范围；限制 provider 总输出；补 Registry/Agent 集成测试；清理 commit 正文、EOF 空行和过期包 docstring。

## 9. 工作区状态与副作用

- **评估前**：`git status --short --branch` 为 `## main...origin/main`，无 tracked 改动；HEAD 与 `origin/main` 均为 `f0f96ed`。
- **报告落盘前**：tracked 工作区仍干净。
- **报告落盘后预期**：仅新增 `Docs/S12-report.md`、修改 `Docs/PROMPT.md`；未修改实现、测试、Issue、PLAN、OpenSpec、README、MEMORY 或远程状态，未提交、未推送。
- 本次测试/构建生成或更新了被忽略的 `.coverage`、`agent_mini.egg-info/`、`build/`、`.pytest_cache/`、`.mypy_cache/`、`.ruff_cache/` 与若干 `__pycache__/`；普通 `git status` 不显示。本次按只读评估边界未清理，需人工确认后清理。
- 隔离验证目录保留于 `C:\Users\Ryan\AppData\Local\Temp\agent-mini-s12-audit-001192a5649f49fbb21748c7972512a5`，包含 wheel、target 安装、Python 3.11 venv 与临时测试副本；需人工确认路径后清理。
- S11 竞态探针使用两个系统临时目录；文件内容仅为测试数据，junction 已在临时目录退出前解除，未写入仓库或外部业务目录。

## 10. 修复记录（2026-10-23）

| 报告项 | 修复 | 证据 |
| --- | --- | --- |
| S12-P0-01 S11 发布窗口 | 发布后再做 target containment；越界时删除刚发布目标并 path_escape | 父目录替换测试 |
| S12-P1-01 M2 装载 | `builtin/__init__.py` 显式导入六工具；subprocess 干净进程断言六个 Schema | `test_builtin_loader_registers_six_tools_in_clean_process` |
| S12-P1-02 畸形 provider | 校验 name 与 SearchResult 四字段均为 str | 非字符串字段/name 测试 |
| S12-P1-03 TC-L3-006 | 保留 calculator 原语义；search 增加 Registry 级 not_configured 测试；ISSUE-039 记录独立 E2E 留后续 | Registry 测试 |
| S12-P1-04 Prompt 时序 | 历史无法回改；ISSUE-039/报告记录重复偏差，后续先留 Prompt | ISSUE-039 |
| S12-P1-05 M2 演示 | README 新增 `pytest -q tests/unit/test_m2_demo.py`，预期 2 passed | M2 演示测试 |
| S12-P2-01 provider 并发 | 模块级可变 provider 仍为测试/装配入口，S21 DI 收口 | 设计记录 |
| S12-P2-02 Schema 约束 | 查询/limit 运行时校验，Schema 未加 min/max | 后续可加强 |
| S12-P2-03 结果总量 | snippet 截断，title/url/source 未设长度上限 | 后续 |
| S12-P2-04 Registry 覆盖 | 新增 Registry search not_configured 测试 | 通过 |

**复验**：263 passed；unit 197、contract 64；覆盖率 **97.04%**；mypy 64 files 0 errors；OpenSpec 12 passed；wheel/仓库外导入通过。M2 恢复为达成。
