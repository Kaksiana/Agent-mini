# S06 独立评估报告

> 评估日期：2026-10-22  
> 基准提交：`0a96631`（`main` 与 `origin/main` 一致）  
> 评估性质：只读代码、测试、规范、流程与分发复核  
> 总体结论：**不通过；修复 P1 后方可进入 S07**（修复后见 §10；S06 已恢复准入）

## 1. 评估范围与基准

### 1.1 实际读取范围

| 基准 | 实际读取位置 | 核对重点 |
| --- | --- | --- |
| 阶段计划与 DoD | `Docs/PLAN.md` S06、§5、阶段状态表 | S06 输出、验收标准、TC、准出状态 |
| 功能需求 | `Docs/REQUIREMENT.md` §5.3、FR-TOOL-01、FR-RT-06、NFR-REL-02、NFR-MAINT-01/02、AC-05/15/16/18 | 注册、Schema、启停、错误结构、分层和安全阀 |
| 设计契约 | `Docs/DESIGN.md` §2.2、§3.2.4、§3.3、§3.5、§3.7、§6～§8 | ToolResult、参数验证、可信上下文、执行和依赖边界 |
| 测试定义 | `Docs/TESTING.md` TC-L1-007/008/009、TC-L1-028、TC-L2-009、TC-L3-006/013 及 S04 延后表 | S06 直接验收与跨阶段回填 |
| 全局规范 | `AGENT.md` 全文；`openspec/specs/engineering-standards/spec.md` | Docs First、TDD、异步、错误、测试、提交、OpenSpec |
| 过程记录 | `Docs/PROMPT.md` S06 条目；`Docs/ISSUE.md` ISSUE-025/031/032；`MEMORY.md` S06；`Docs/S05-report.md` §10 | 前置修复、红绿证据、状态声明 |
| OpenSpec | `openspec/changes/archive/2026-10-22-s06-tool-registry/`；`openspec/specs/tool-registry/spec.md` | change 时序、规格完整性、归档 |
| 实现与测试 | `agent_mini/tools/registry.py`、`runtime/registry_adapter.py`、`runtime/loop.py`、`runtime/result.py`；`tests/unit/test_tool_registry.py` 及全量 tests | 注册、执行、Schema、适配、不可变性、回归 |
| 构建与依赖 | `pyproject.toml`、README、wheel | 依赖变化、包文件、仓库外导入 |

### 1.2 文档基准之间的一致性

- `PLAN` S06 与 TC-L1-007/008/009 对“注册后可查、pydantic Schema、重复拒绝”的定义一致，现有三个对应测试均有效通过。
- `REQUIREMENT` FR-TOOL-01 还明确要求“支持启停”，`DESIGN` §3.3 要求按配置决定启停并让下一请求使用新快照；`PLAN`、`TESTING` 和 S06 OpenSpec 均遗漏该验收维度，实现也只保存 `enabled_key` 而不执行过滤。
- `DESIGN` §3.3 要求模型伪造 `session_id` 等额外参数必须拒绝；当前任意普通 pydantic 模型默认忽略额外字段，S06 的统一注册表没有建立该边界。
- `TESTING` S04 覆盖边界将真实 `unknown_tool`/参数校验/ToolResult 回填交给 S06，但 S06 测试没有覆盖真实注册表的 unknown 分支；覆盖率也显示 `registry.py:102` 未执行。
- S06 OpenSpec 把 handler 契约写为 `ToolResult`，实现却把任意非字符串对象（包括 `None`）转成成功文本，规格与行为不一致。
- `PLAN`/README/MEMORY/ISSUE 已声明 S06 完成，但上述 P1 尚未关闭。

## 2. 复核命令与结果

### 2.1 实际复跑

| 命令/验证 | 结果 |
| --- | --- |
| `git status --short --branch`、`git log origin/main..HEAD` | 评估前工作区干净；`main` 与 `origin/main` 一致 |
| `git log/show/diff 1c8f29a..0a96631` | S06 共 3 个提交；代码 `dcffea5` 早于 change/文档 `371f982`，之后由 `0a96631` 归档 |
| `python -m pytest -q -m unit -p no:cacheprovider` | **56 passed，64 deselected，0.37s** |
| `python -m pytest -q -m contract -p no:cacheprovider` | **64 passed，56 deselected，47.50s** |
| `python -m pytest --cov=agent_mini --cov-report=term-missing`（coverage 文件定向到仓库外） | **120 passed，49.84s；总覆盖率 95%，registry 91%，adapter 100%** |
| `ruff format --check .` | **54 files already formatted** |
| `ruff check .` | **All checks passed** |
| `mypy agent_mini tests` | **Success: no issues found in 51 source files** |
| `openspec validate --all --strict` | **5 passed，0 failed**；`openspec list` 无活动 change |
| `python -m pip check` | **No broken requirements found** |
| `pip wheel --no-deps` 到仓库外临时目录，安装到临时 target 后从仓库外导入 | wheel 构建/安装成功；`ToolRegistry`、`ToolSpec`、`ToolResult`、`RegistryExecutor` 可导入；含 registry、adapter、`schema.sql` |
| 禁用框架、`noqa`、`type: ignore`、debug/eval/exec 扫描 | 源码与测试零命中；只出现文档中的禁用框架名称和测试假密钥 |
| `git diff 1c8f29a..0a96631 -- pyproject.toml` | 无差异，S06 未新增依赖 |

### 2.2 定向行为探针

| 探针 | 实际结果 | 判定 |
| --- | --- | --- |
| 注册 `enabled_key="ECHO_ENABLED"` 的工具 | Schema 仍公开，调用仍成功 | 启停只存元数据，没有行为 |
| 给 `EchoArgs(text)` 传入额外 `session_id="forged"` | 返回成功 `echo:x` | 额外参数被静默丢弃，没有按设计拒绝 |
| 同步 handler 阻塞 50ms，外层 `asyncio.wait_for(..., 10ms)` | 正常成功，耗时 50.4ms，没有超时 | 同步 handler 阻塞事件循环并绕过 deadline |
| handler 返回 `None` | `ToolResult(ok=True, content="None")` | 违反 handler 返回 ToolResult 的契约并掩盖实现错误 |
| unknown tool | `ok=False,error_code=unknown_tool` | 实现分支正确，但正式测试未覆盖 |
| 空工具名注册后取 Schema | 注册成功；到 `RegistryExecutor.schemas()` 才抛 ValidationError | 注册边界未及早验证元数据 |
| 修改 `ToolCallTrace.args` 内嵌字典 | 内嵌值可由 `old` 改为 `new` | 只做到顶层只读，不是深不可变 |
| 失败 ToolResult 使用空 content | 构造成功 | “可读说明”未形成运行时不变量 |

### 2.3 历史红灯复核

- 在仓库外用父提交 `1c8f29a` 重建代码，再叠加最终 `test_tool_registry.py`：pytest 在收集阶段因缺少 `runtime.registry_adapter` 退出 2。
- 该结果不是断言失败，按 `AGENT.md` §2 与工程规范“红必须是正确行为失败、不能是 import/语法错误”，不能作为有效逐 TC 红灯。
- 当前历史只证明 `dcffea5` 同时提交了实现和测试；`Docs/PROMPT.md` 未记录任何进入执行阶段的红灯命令与失败原因。

### 2.4 未复跑项

- 未执行真实 calculator/time/todo/file/search：分别属于 S07～S12。
- 未执行会话上下文注入和越权隔离：ToolContext 按归档设计留到 S09；本次只验证了 S06 参数边界能否承接该阶段。
- 未调用真实 provider、数据库或 HTTP 接口；这些均不属于 S06。

## 3. 维度结论

| 维度 | 结论 | 理由与证据 |
| --- | --- | --- |
| 需求与范围合规 | 不通过 | 未越界实现具体工具/Memory/HTTP，但 FR-TOOL-01 的启停能力缺失；`registry.py:51-121`。 |
| 注册、查找与重复保护 | 通过 | `register/get/schemas/@tool` 已实现；TC-L1-007/009 的查找、顺序和不覆盖断言通过。 |
| JSON Schema 正确性 | 有条件通过 | Schema 与 pydantic 同源，TC-L1-008 通过；但名称元数据在注册时不校验，空名延迟到 Runtime adapter 才失败。 |
| 参数校验与安全边界 | 不通过 | 缺少必填字段会失败，但额外字段默认被忽略；伪造 `session_id` 的探针成功。 |
| 执行与错误边界 | 不通过 | unknown/ValidationError/普通异常可结构化；同步 handler 可绕过 deadline，`None` 又会被转换为成功。 |
| Runtime 集成与分层 | 有条件通过 | `RegistryExecutor` 可驱动两步 Agent 且无具体工具依赖；但同步调用破坏 S05 的取消保证，Schema 类型表述也不统一。 |
| 数据模型与不可变性 | 有条件通过 | ToolResult 的 ok/error_code 两项矛盾被拒绝；ToolCallTrace 只有顶层 mapping proxy，嵌套仍可变。 |
| 测试质量与 TDD | 不通过 | 8 个 S06 测试全部通过，但未覆盖启停、unknown、额外字段、同步取消、非法返回和深不可变；历史红只到收集失败。 |
| 全局代码规范 | 有条件通过 | Ruff、format、mypy、复杂度和禁止项扫描通过；异步阻塞、Docs First、Prompt/TDD 记录不符合全局规范。 |
| 打包与分发 | 通过 | wheel 包含新增模块和 `systemdb/schema.sql`，仓库外导入成功。 |
| 依赖与范围边界 | 通过 | 未修改依赖，未引入禁用 Agent 框架或具体内置工具。 |
| 流程与文档闭环 | 不通过 | change 晚于代码、Prompt 只存摘要、OpenSpec/TESTING 缩窄 FR、完成状态超前。 |

## 4. 问题清单

### P0

无。

### P1

#### S06-P1-01 — FR-TOOL-01 的启停能力没有实现

- **位置**：`agent_mini/tools/registry.py:51-91,124-149`，`ToolSpec.enabled_key`、`ToolRegistry.schemas/execute`；`openspec/specs/tool-registry/spec.md:9-21`
- **问题描述**：`enabled_key` 仅保存字符串，注册表没有启停状态、配置快照或过滤入口。标记为禁用的工具仍发送给模型并可执行。S06 OpenSpec 还完全遗漏启停需求。
- **判定依据**：`Docs/REQUIREMENT.md:192` 的 FR-TOOL-01 明确“支持启停”；`Docs/DESIGN.md:302,329` 要求配置决定启停、快照从下一请求生效。
- **建议方向**：在不提前实现 S21 配置加载器的前提下，为 Registry 提供显式、可注入的启停状态/快照；`schemas()` 与 `execute()` 使用同一状态，并补启用、禁用、状态切换和禁用执行测试。

#### S06-P1-02 — 同步 handler 可阻塞事件循环并绕过 S05 deadline

- **位置**：`agent_mini/tools/registry.py:111-116`，`ToolRegistry.execute`
- **问题描述**：同步 handler 在异步方法内直接调用。探针给外层 10ms timeout，handler 使用 50ms 阻塞调用时仍正常成功并耗时 50.4ms；Runtime 的 `asyncio.timeout` 无法在事件循环被阻塞时取消它。
- **判定依据**：OpenSpec 工程规范 `异步、并发与阻塞 I/O` 要求阻塞同步调用使用 `asyncio.to_thread()`；FR-RT-05/NFR-REL-02 要求硬 deadline 和最坏情况收敛。
- **建议方向**：明确 handler 分为 async 与 sync；async 直接 await，sync 放到受控线程并保留取消/超时语义，或禁止同步 handler。增加 Agent 级同步阻塞 handler deadline 回归。

#### S06-P1-03 — 额外模型参数被静默接受，无法承接可信会话边界

- **位置**：`agent_mini/tools/registry.py:103-110`，`ToolRegistry.execute`；`tests/unit/test_tool_registry.py:22-23`
- **问题描述**：统一注册表直接调用任意 `params_model.model_validate()`；普通 pydantic 模型默认 `extra=ignore`。探针传入伪造 `session_id` 后仍成功，额外字段被静默删除。
- **判定依据**：`Docs/DESIGN.md:304` 明确要求 session_id 不在模型参数 Schema，伪造额外字段必须拒绝；FR-TOOL-01 要求统一参数校验，S09 隔离建立在此边界上。
- **建议方向**：注册时强制或验证 params_model 使用 `extra="forbid"`，或由 Registry 在 model_validate 前统一拒绝未声明键；补额外普通字段和伪造上下文字段测试。

#### S06-P1-04 — 非法 handler 返回值被包装成成功结果

- **位置**：`agent_mini/tools/registry.py:117-121`，`ToolRegistry.execute`
- **问题描述**：只有 ToolResult 和 str 被显式识别，其余任何对象都执行 `str(raw)` 并返回成功；handler 漏写 return 时会得到成功内容 `"None"`，掩盖工具缺陷并污染模型判断。
- **判定依据**：`Docs/DESIGN.md:303` 与归档 OpenSpec design 明确 `handler(**validated_args) -> ToolResult`；所有异常/失败必须结构化，不能静默转成功。
- **建议方向**：收紧为 ToolResult 唯一返回类型；若要兼容 str，需正式写入设计并只允许明确集合。非法返回统一转 `tool_execution_error`，补 None/数字/错误类型回归。

#### S06-P1-05 — 需求、OpenSpec 与测试追溯被缩窄，必需边界未覆盖

- **位置**：`Docs/TESTING.md:100-102,172-181`；`tests/unit/test_tool_registry.py:36-118`；`openspec/specs/tool-registry/spec.md:9-53`
- **问题描述**：TC-L1-007/008/009 没有启停场景，却被 FR-TOOL-01 用作完整验收；S04 覆盖边界把真实 unknown/参数/ToolResult 回填交给 S06，但 S06 没有 unknown 测试。启停、额外参数、同步取消、非法返回也均无测试。
- **判定依据**：`AGENT.md` §1 要求每条验收标准映射测试；§2 禁止以不完整断言宣称完成；`PLAN.md` §5.1 要求阶段全部测试项与文档一致。
- **建议方向**：补 S06 覆盖边界表并拆分可执行子场景；至少覆盖启停、unknown、额外字段拒绝、同步 handler deadline、非法返回，再据实更新完成状态。

#### S06-P1-06 — OpenSpec change 和设计文档晚于实现提交

- **位置**：Git 提交 `dcffea5`、`371f982`、`0a96631`；`AGENT.md:14-35,262-275`
- **问题描述**：功能代码/测试在 21:44:37 提交，S06 proposal/design/tasks/spec 到 21:44:41 才创建；无法证明编码前已有 change 且 strict validate 通过。
- **判定依据**：`AGENT.md` §1/§6.1 要求任何新功能先建 change、评审/校验后编码；禁止绕过 change 直接改行为。
- **建议方向**：不重写历史；以新修复 change 记录偏差并承接修复。从 S07 起先提交并 strict validate change，再进入代码。

#### S06-P1-07 — Prompt 原文与有效 TDD 红灯证据缺失

- **位置**：`Docs/PROMPT.md:1396-1414`；归档 `tasks.md:7-13`；提交 `dcffea5`
- **问题描述**：所谓“原始 Prompt”只有三行摘要，第 1406 行承认完整内容在别处；tasks 勾选全部 TDD 红，但没有命令/失败原因。历史重建只产生缺模块的收集错误，不符合有效红灯定义。
- **判定依据**：`AGENT.md` §2 要求红因正确且不是环境/import 错误；§3 要求 Prompt 逐字保存；`PLAN.md:309` 要求先提交失败测试。
- **建议方向**：如实登记历史不可补证，不伪造红灯或原文；修复项先写能进入执行阶段的断言失败测试，记录红/绿命令与原因。

### P2

#### S06-P2-01 — ToolCallTrace 只做到浅层只读

- **位置**：`agent_mini/runtime/result.py:23-42`，`ToolCallTrace.model_post_init`
- **问题描述**：MappingProxyType 只保护最外层字典，嵌套 dict/list 仍可原地修改。定向探针成功修改 `args["nested"]["value"]`；ISSUE-032 与 MEMORY 将该债务描述为已解决，表述过强。
- **判定依据**：`Docs/DESIGN.md` §3.2 的冻结结果契约；S05 报告 M1-P2-02 的深不可变技术债。
- **建议方向**：递归冻结嵌套容器或在读取/序列化边界返回深防御副本，并补嵌套 dict/list 修改测试；同步修正文档状态。

#### S06-P2-02 — 工具元数据在注册边界缺少最小校验

- **位置**：`agent_mini/tools/registry.py:51-80`，`ToolSpec`、`ToolRegistry.register`
- **问题描述**：空 name/description、错误 params_model/handler 可先注册；空名直到 RegistryExecutor 转 ToolSchema 才失败，错误定位晚且注册表已进入非法状态。
- **判定依据**：PLAN 要求生成合法 Schema；全局“入口校验、尽早失败”错误规范。
- **建议方向**：注册时校验非空名称/描述、名称格式、BaseModel 子类与 callable；失败使用明确 ToolRegistrationError，保证原表不变。

#### S06-P2-03 — ToolResult 没有保证失败说明可读

- **位置**：`agent_mini/tools/registry.py:35-48`，`ToolResult.__post_init__`
- **问题描述**：只校验 ok/error_code 组合；空 content 和运行时错误类型仍可构造。探针确认 `ToolResult(False, "", "bad")` 被接受。
- **判定依据**：`Docs/DESIGN.md:303` 要求失败内容为可读说明；FR-RT-06 要求结构化、可供模型纠正。
- **建议方向**：校验 content 为非空字符串、error_code 为非空稳定标识，并补空白/错误类型负例。

#### S06-P2-04 — `schemas()` 的公开类型在规格和实现间不统一

- **位置**：`agent_mini/tools/registry.py:89-91`；`runtime/registry_adapter.py:14-16`；`openspec/specs/tool-registry/spec.md:11`
- **问题描述**：注册表实际返回 provider-neutral `dict`，适配器再转 `ToolSchema`；主规格却写 `ToolRegistry.schemas()` 直接返回 ToolSchema 列表，容易误导调用方。
- **判定依据**：归档 design 的 Tool 层不得依赖 LLM 决策、类型注解与主规格应一致。
- **建议方向**：明确 Tool 层返回的 schema DTO/字典类型与 Runtime 适配后的 ToolSchema 类型，统一命名和文档。

### Info

#### S06-INFO-01 — 阶段范围和依赖控制良好

- **位置**：`1c8f29a..0a96631` diff、`pyproject.toml`
- **观察**：未实现 S07～S12 内置工具、S10 沙箱、Memory、Context、HTTP 或真实 API；未新增依赖或禁用框架。
- **建议**：继续保持阶段隔离。

#### S06-INFO-02 — 核心注册主路径与分发可用

- **位置**：`tests/unit/test_tool_registry.py`、wheel 验证
- **观察**：注册/查找、pydantic Schema、重复拒绝、缺参错误、handler 普通异常和 Agent 适配主路径均可运行；wheel 与仓库外导入通过。
- **建议**：保留这些用例，在修复 P1 时扩充边界而非替换或弱化。

## 5. 需求—实现—测试追溯

| 需求/TC | 实现位置 | 测试位置 | 覆盖结论 | 越界 |
| --- | --- | --- | --- | --- |
| FR-TOOL-01：装饰器注册/查找 | `registry.py` `ToolSpec/ToolRegistry/tool` | `test_register_and_lookup` | 覆盖 | 否 |
| FR-TOOL-01：Schema 同源 | `ToolSpec.to_json_schema` | `test_pydantic_schema_matches_openai_contract` | 覆盖 object/properties/required | 否 |
| FR-TOOL-01：重复拒绝 | `ToolRegistry.register` | `test_duplicate_registration_is_rejected` | 覆盖且断言原项未变 | 否 |
| FR-TOOL-01：启停 | 仅 `ToolSpec.enabled_key` 字段 | 无 | **未覆盖、未实现** | 否 |
| FR-RT-06：invalid_arguments | `ToolRegistry.execute` | `test_invalid_arguments_do_not_execute_handler` | 部分覆盖缺必填字段 | 属 S06 集成回填 |
| FR-RT-06：unknown_tool | `ToolRegistry.execute` | 无真实注册表测试；S04 仅测试替身 | 实现存在、自动化缺失 | 属 S06 集成回填 |
| FR-RT-06：handler 异常 | `ToolRegistry.execute` | `test_handler_exception_becomes_tool_error` | 普通 RuntimeError 覆盖；同步阻塞/非法返回未覆盖 | 属 S06 集成回填 |
| NFR-MAINT-01 / AC-15 | `RegistryExecutor` + registry | `test_registry_drives_runtime_without_runtime_changes` | echo 可不改循环接入；启停和具体工具仍待后续 | 否 |
| TC-L1-007 | 注册/get/schemas/decorator | `test_register_and_lookup` | 通过，但未承载 FR 中启停 | 否 |
| TC-L1-008 | pydantic Schema | `test_pydantic_schema_matches_openai_contract` | 通过 | 否 |
| TC-L1-009 | DuplicateToolError | `test_duplicate_registration_is_rejected` | 通过 | 否 |
| TC-L1-028 / TC-L2-009 S06 回填 | Registry execute、adapter | invalid/异常/Agent 集成测试 | **部分覆盖**；unknown 与额外字段缺失 | 否 |
| TC-L3-006 | RegistryExecutor 可驱动 echo 替身 | `test_registry_drives_runtime_without_runtime_changes` | 注册表部分覆盖；真实 calculator 留 S07/S18 | 否 |
| TC-L3-013 | ToolContext 仅预留 | `test_tool_context_reserved` | S09 正式执行；当前额外 session_id 拒绝前提未满足 | 否，按计划延后 |

## 6. 边界抽查

- **是否实现任何具体内置工具：否。** calculator/time/todo/read/write/search 均未实现。
- **是否实现沙箱、Memory、Context、HTTP、配置加载或真实 API：否。** ToolContext 只有冻结数据结构且明确预留 S09。
- **是否新增依赖或禁用 Agent 框架：否。** `pyproject.toml` 在 S06 无差异。
- **装饰器注册、查找、Schema、重复拒绝是否工作：是。** 三条计划 TC 均有有效断言并通过。
- **启停是否工作：否。** `enabled_key` 不影响 Schema 或 execute。
- **参数是否严格拒绝额外字段：否。** 默认 pydantic 模型静默忽略，伪造 session_id 探针成功。
- **所有 handler 失败是否结构化：普通异常是；同步阻塞无法被 deadline 取消，非法返回会被误报成功。**
- **新增工具是否需要修改主循环：不需要。** 但接入时需构造 `RegistryExecutor`，S21 DI 容器尚未实现。
- **ToolCallTrace 是否真正深不可变：否。** 顶层只读，嵌套容器仍可变。
- **S06 OpenSpec 是否先于实现并有效红灯：否。** change 晚于代码；历史重建只得到收集错误。

## 7. 技术债与后续阶段影响

| 后续阶段 | 风险/技术债 | 触发条件 | 建议时机 |
| --- | --- | --- | --- |
| S07 calculator | sync handler 可阻塞事件循环；非法返回被包装成功 | 计算复杂或 handler 漏 return | S07 开工前修 P1-02/04 |
| S08 time | 启停没有行为 | 配置关闭 time 或切换工具快照 | S07 前先修 P1-01，避免每个工具重复绕行 |
| S09 todo | 伪造 session_id 被静默忽略，可信上下文注入尚未落地 | 模型参数携带其他会话 ID | S09 前必须修 P1-03，并补 TC-L3-013 |
| S10 文件工具 | 同步文件 I/O 会直接阻塞事件循环和 deadline | read/write 使用同步 Path API | S10 前确保 sync handler 在线程执行或工具全 async |
| S11 search | 同步 provider/网络调用可能无限阻塞 | provider 使用同步 SDK | S11 前复核 async/timeout 契约 |
| S12 集成 | 禁用工具仍出现在 Schema 并可调用 | 六工具按配置启停 | S12 前完成启停快照与禁用错误语义 |
| S16 Context | ToolCallTrace 嵌套可变影响裁剪/审计快照 | trace 被缓存或序列化前被修改 | S16 前处理 P2-01 |
| S18 HTTP/真实 API | 非法工具返回、空错误说明和元数据迟校验会进入公开响应 | provider 产生异常调用或工具实现缺陷 | S18 前收紧 ToolResult/ToolSpec 不变量 |
| S20 错误体系 | ToolError 当前仅继承 Exception，无 code/http_status | 统一 AgentError 层次 | 按既定 S20 迁移，并补异常层次测试 |

## 8. 总体结论

### 8.1 是否可以进入 S07

**暂不可进入 S07。** S06 的注册、Schema、重复拒绝和 Runtime 适配主路径已经建立，120 个现有测试及静态/打包门禁均通过；但 FR-TOOL-01 的启停能力缺失，同步 handler 会破坏 S05 deadline，额外参数未严格拒绝，非法返回被误判成功，测试/规格/流程也未闭环。

进入 S07 前必须处理：

1. S06-P1-01：实现可注入、Schema/执行一致的工具启停状态。
2. S06-P1-02：保证同步 handler 不阻塞事件循环且 deadline 可生效。
3. S06-P1-03：统一拒绝未声明参数，固化可信上下文边界。
4. S06-P1-04：收紧 handler 返回类型，禁止 `None` 等被转成成功。
5. S06-P1-05：补完整需求—测试映射与真实 Registry 边界测试。
6. S06-P1-06：以新 change 承接修复并记录历史 Docs First 偏差。
7. S06-P1-07：如实补流程记录；修复测试保留有效红绿证据。

可选建议：完成 trace 深不可变、注册元数据早校验、ToolResult 可读内容不变量与 schema DTO 类型统一。

## 9. 工作区状态与副作用

### 9.1 状态对比

- 评估开始前：`git status --short --branch` 仅输出 `## main...origin/main`。
- 所有只读测试、探针、wheel 完成后且报告写入前：状态仍干净。
- 本轮按全局评估规则新增 `Docs/S06-report.md`，并在 `Docs/PROMPT.md` 追加本轮原始 Prompt；未修改实现、测试、OpenSpec、PLAN、Issue、README、MEMORY 或远程状态。

### 9.2 评估副作用

- coverage 数据：`C:\Users\Ryan\AppData\Local\Temp\agent-mini-s06.coverage`。
- wheel/临时 target：`C:\Users\Ryan\AppData\Local\Temp\agent-mini-s06-audit-8ebcc5839fa74380bec374cbd09ea5fb`。
- 历史红灯重建：`C:\Users\Ryan\AppData\Local\Temp\agent-mini-s06-red-f4fb10b85fd14c6fbccf14535fefa4c8`，以及同前缀 base/test zip。
- wheel 构建可能刷新仓库内被忽略的 `agent_mini.egg-info/`；测试会刷新 `__pycache__/` 等缓存。
- 结束前 ignored 快照显示 `.coverage`、`.mypy_cache/`、`.pytest_cache/`、`.ruff_cache/`、`agent_mini.egg-info/` 和各包/测试的 `__pycache__/`。开始时未记录 ignored 基线，无法严谨区分既有与本轮刷新项。
- 上述产物未自动删除；如需清理，请人工确认路径后处理。

## 10. 修复记录（2026-10-22）

| 报告项 | 修复 | 证据 |
| --- | --- | --- |
| S06-P1-01 启停 | `ToolRegistry(enabled=...)`；禁用工具不出现在 schemas，execute 返回 `tool_disabled` | 禁用/启用测试 |
| S06-P1-02 同步 handler | 同步 handler 走 `asyncio.to_thread`；async 直接 await | 50ms handler + 10ms wait_for 超时测试 |
| S06-P1-03 额外参数 | 顶层字段白名单，未声明字段返回 `invalid_arguments` | 伪造 session_id 测试 |
| S06-P1-04 返回类型 | 只接受 `ToolResult`，其他返回 `invalid_tool_result` | 返回 None 测试 |
| S06-P1-05 追溯 | 补 unknown_tool/启停/同步/额外参数/返回类型测试；FR-TOOL-01 启停映射到测试 | 13 个 registry 测试 |
| S06-P1-06 Docs First | 新 change `s06-report-fixes` 承接；记录历史时序偏差 | 归档 change |
| S06-P1-07 Prompt/TDD | 本轮修复测试先红后绿；历史 Prompt 缺证不伪造 | 14 个红灯、129 passed |
| S06-P2-01 深只读 | ToolCallTrace.args 递归 mappingproxy/tuple | 嵌套 dict 修改测试 |
| S06-P2-02 元数据校验 | ToolSpec 注册期校验 name/description/params_model/handler/enabled_key | 空 name 测试 |
| S06-P2-03 失败内容 | ToolResult 内容非空校验 | 空失败内容测试 |
| S06-P2-04 Schema 类型 | 保留 ToolRegistry dict DTO，RegistryExecutor 转 ToolSchema；在 Tool 层不引入 LLM 依赖 | 规格/适配器 |

**复验**：129 passed；覆盖率 95.25%；unit 65、contract 64；mypy 51 files 0 errors；ruff/format/OpenSpec/wheel 通过。S06 可进入 S07；历史 Prompt 缺证仍如实保留。
