# S05 与 M1 独立评估报告

> 评估日期：2026-10-22  
> 基准提交：`69ae57e`（`main` 与 `origin/main` 一致）  
> 评估性质：只读代码、测试、规范、流程与里程碑复核  
> 总体结论：**S05 不通过，暂不可进入 S06；M1 不满足里程碑 DoD，不能维持“已达成”结论**

## 1. 评估范围与基准

### 1.1 实际读取范围

| 基准 | 实际读取位置 | 核对重点 |
| --- | --- | --- |
| 阶段计划与 DoD | `Docs/PLAN.md` S05、§4、§5 | S05 输出、TC 映射、M1 达成标志、阶段/里程碑准出条件 |
| 功能需求 | `Docs/REQUIREMENT.md` FR-RT-04/05/06、§5.2/§5.3、AC-10 | 硬边界、协议配对、工具异常结构化、固定终止语义 |
| 设计契约 | `Docs/DESIGN.md` §3.2.0、§3.2.2～§3.2.4、§6、§7、§8 | `steps`、trace、deadline 起点/取消、重复签名、阶段边界 |
| 测试定义 | `Docs/TESTING.md` TC-L1-015/015A～C/016/024/028/029/030、S04/S05 覆盖边界、TC-L4-008 | S00～S05 累积回归及 S05 完整断言 |
| 全局规范 | `AGENT.md` §1～§11；`openspec/specs/engineering-standards/spec.md` | Docs First、TDD、Prompt、提交、OpenSpec、代码/测试/依赖规范 |
| 过程记录 | `Docs/PROMPT.md` S05 条目；`Docs/ISSUE.md` ISSUE-024/025/029/030 与 S05 记录；`MEMORY.md` S05；S01～S04 报告修复记录 | 红绿证据、历史债务、声明与事实一致性 |
| OpenSpec | `openspec/changes/archive/2026-10-22-s05-runtime-safety-valve/`；`openspec/specs/runtime/spec.md` | change 时序、归档内容、累计主规格语义 |
| 实现与测试 | `agent_mini/runtime/agent.py`、`loop.py`、`result.py`；`tests/unit/test_agent.py`、`test_react_loop.py`、`test_safety_valve.py`；全量 tests | 安全阀行为、结果模型、边界测试、回归 |
| 构建与依赖 | `pyproject.toml`、`README.md`、wheel 内容 | 依赖变化、可复现命令、包文件、仓库外导入 |

### 1.2 文档之间的一致性

- `PLAN` S05、`DESIGN` §3.2.4 与 `TESTING` TC-L1-016 对 `max_steps=3`、固定提示、`truncated=true` 的定义一致。
- 三者对重复检测的核心语义一致：同一 `name + 规范化 JSON arguments` 连续 3 次中断。
- `PLAN` 将 TC-L4-008 明确留给 S18，`TESTING` §4.2.5 同样标记“不覆盖”，没有要求 S05 提前实现 HTTP 映射。
- `TESTING` TC-L1-029 要求“可注入单调时钟和 async timeout”“steps 等于实际步骤”“不依赖长时间 sleep”；当前测试只注入时钟参数表面，硬编码使用 `asyncio.wait_for`，且未覆盖 LLM 挂起，因此文档定义与测试落地不一致。
- OpenSpec 主规格不是有效的 S03～S05 累计契约：Purpose 仍只写 S03/S04；第 11、21、63 行仍声明 `truncated` 不存在或 S04 不得实现安全阀，却又在第 35、125～151 行定义 S05 字段与行为。
- `PLAN`、`README`、`MEMORY`、`ISSUE` 均声明 M1 已完成，但未提供 M1 专用可运行演示命令/复现步骤，且本报告发现未关闭 P1，和 `PLAN` §5.2 的里程碑 DoD 冲突。

## 2. 复核命令与结果

### 2.1 实际复跑

| 命令/验证 | 结果 |
| --- | --- |
| `git status --short --branch`、`git log --oneline origin/main..HEAD` | 评估前工作区干净；`main` 与 `origin/main` 一致，无未推送提交 |
| `git log/show/diff` 核对 `1a9bdb3`、`770fda7`、`92127b8`、`69ae57e` | 代码提交先于 S05 change/文档提交；`1a9bdb3` 仅含实现文件 |
| `python -m pytest -q -m unit -p no:cacheprovider` | **39 passed，64 deselected，0.29s** |
| `python -m pytest -q -m contract -p no:cacheprovider` | **64 passed，39 deselected，40.59s** |
| `python -m pytest --cov=agent_mini --cov-report=term-missing`（coverage 文件定向到仓库外） | **103 passed，42.10s；总覆盖率 94.51%，`runtime/loop.py` 91%** |
| 代表性 M1 演示：直答、两步工具循环、max_steps、deadline 四个指定测试 | **4 passed，0.21s**；功能可由测试替身演示，但仓库文档未给出该步骤 |
| `ruff check .` | 通过 |
| `ruff format --check .` | **52 files already formatted** |
| `ruff check --select PLR0915,PLR0912 agent_mini/runtime/loop.py` | 通过 |
| `mypy agent_mini tests` | **Success: no issues found in 49 source files** |
| `openspec validate --all --strict` | **4 passed，0 failed**；仅证明结构校验通过，不会识别累计规格中的语义矛盾 |
| `python -m pip check` | **No broken requirements found** |
| `pip wheel --no-deps` 到仓库外临时目录，再安装到临时 target 并从仓库外导入 | wheel 构建成功；包含 `runtime/loop.py` 与 `systemdb/schema.sql`；可导入 `Agent`、`LoopPolicy`、`AgentResult`；默认值为 8/120.0/3 |
| 被禁框架扫描与 `698a515..HEAD -- pyproject.toml` | S05 未改依赖；源码/配置未引入 LangChain/LangGraph/AutoGen/CrewAI/Semantic Kernel 等框架 |
| 在 `1a9bdb3` 临时基线叠加 `770fda7` 的 S05 测试后复跑 | **4 failed，2.42s**，可证明最终四个测试在功能实现前确实为红；但仓库历史仍没有“测试先提交”和逐 TC 红证据 |

### 2.2 定向行为探针

| 探针 | 实际结果 | 判定 |
| --- | --- | --- |
| 工具执行器自身抛 `TimeoutError("tool-local-timeout")` | `termination_reason=deadline`、`truncated=true`、仅 1 次 LLM 请求 | 失败：工具内部异常被误判为全局 deadline |
| 连续两个不同非法参数后，模型修正为合法空对象 `{}` | 第 3 次请求直接以 `termination_reason=repeat` 中止 | 失败：非法 `None` 与合法 `{}` 的签名碰撞 |
| 首次 LLM 返回工具，第二次 LLM 挂起 | 实际请求 2 次，但 `result.steps=1`、trace 仅 1 条 | 失败：`steps` 少计一次真实 LLM 调用 |
| `LoopPolicy(deadline_seconds=math.inf)` + 挂起工具 | 策略被接受；只能由探针外层超时取消 | 失败：非有限值可关闭 deadline 硬边界 |

### 2.3 未复跑项

- 未调用真实 provider、未读取 API Key：S05 的 TC-L4-008 按计划归 S18。
- 未运行 HTTP `/chat`：接口层归 S18，当前仓库尚无该入口。
- 未对远程仓库、Issue、OpenSpec、实现或测试做任何修改。

## 3. 维度结论

| 维度 | 结论 | 理由与证据 |
| --- | --- | --- |
| 需求与范围合规 | 有条件通过 | 产出集中在 Runtime 安全阀，未实现 S06/S13～S18；`PLAN.md:105-114` 与 `agent_mini/runtime/` 对应。但 deadline 起点/有限性未满足硬边界。 |
| max_steps 与终止结果 | 通过 | `loop.py:117-140`、`result.py:48-67`；TC-L1-016 在 `test_safety_valve.py:80-91` 精确断言 3 次、固定文案、原因和 `truncated`。 |
| deadline 与取消 | 不通过 | `loop.py:110-122,185-199`；探针证实工具本地 `TimeoutError` 误分类、非有限 deadline 绕过，且 `schemas()` 在计时前执行。 |
| 重复调用检测 | 不通过 | `loop.py:296-308` 使用 `call.arguments or {}`，把非法参数与合法空对象归为同一签名；探针可稳定误杀纠正流程。 |
| 错误边界与消息配对 | 有条件通过 | 批次中断补齐逻辑位于 `loop.py:163-180,267-276`，现有 deadline 测试验证两个 call_id；但工具内部 `TimeoutError` 被错误升级为全局终止。 |
| 数据模型与可观察性 | 有条件通过 | `AgentResult` 对终止状态有一致性校验；但 LLM deadline 分支回退 `step`，违背 `DESIGN.md:179,238-248` 与 TC-L1-029 的实际步数语义。 |
| 测试质量与 TDD | 不通过 | 全量 103 通过且历史红可重建；但 S05 只有 4 个测试，未覆盖 LLM deadline、有限值校验、签名纠错/规范化/重置等关键边界，且提交历史不满足测试先行/同提交要求。 |
| 全局代码规范 | 有条件通过 | Ruff、format、mypy、PLR 门禁通过，无 noqa/type-ignore/注释代码；流程、Prompt 与 OpenSpec 顺序违反 `AGENT.md`。 |
| 打包与分发 | 通过 | wheel 含新增 Runtime 模块和 `systemdb/schema.sql`，仓库外 target 导入成功，未发现未声明依赖。 |
| 依赖与禁用清单 | 通过 | S05 未修改 `pyproject.toml`，`pip check` 通过，未引入被禁 Agent 框架；运行依赖仅下界为已登记 ISSUE-025。 |
| 流程与文档闭环 | 不通过 | 实现提交先于 OpenSpec change；Prompt 只保存摘要；累计主规格矛盾；M1 文档声明超前。 |
| M1 可复现与准出 | 不通过 | 累积 103 测试、覆盖率、wheel、静态门禁、代表性测试替身链路均通过；但缺专用演示步骤且存在 P1，不满足 `PLAN.md:317-324`。 |

## 4. 问题清单

### P0

无。

### P1

#### S05-P1-01 — 工具自身 `TimeoutError` 被误判为全局 deadline

- **位置**：`agent_mini/runtime/loop.py:185-199`，符号 `_execute_tool`
- **问题描述**：`asyncio.wait_for` 自身超时与被调用协程主动抛出的 `TimeoutError` 落入同一分支。后者会被标记 `deadline` 并立刻截断整个 Agent，而不是作为工具执行失败回灌、允许模型纠正。定向探针得到 `termination_reason=deadline`。
- **判定依据**：`Docs/REQUIREMENT.md` §5.3 要求工具内部异常结构化而非抛出；FR-RT-06/TC-L1-028 与 S04 已建立“工具错误回灌后可继续收敛”；`DESIGN.md` §3.2.4 只允许真实剩余时间耗尽触发 deadline。
- **建议方向**：区分等待器触发的取消与协程自身异常；仅真实 deadline 终止循环，工具异常继续归一为 `tool_execution_error`，并补本地 TimeoutError 回归。

#### S05-P1-02 — 重复签名把非法参数与合法空对象视为同一调用

- **位置**：`agent_mini/runtime/loop.py:296-308`，符号 `_signature`
- **问题描述**：`call.arguments or {}` 同时把解析失败的 `None` 和合法 `{}` 规范化为 `{}`。连续两个不同非法请求后，模型修正为合法无参调用时会在执行前后被判为第三次重复并截断。
- **判定依据**：`Docs/DESIGN.md:281-285` 与 OpenSpec `runtime/spec.md:139-142` 规定相同 `name + 规范化 JSON arguments` 才计重复；`Docs/TESTING.md` TC-L1-028 要求参数错误可修正并收敛。
- **建议方向**：非法调用不进入可执行调用的重复计数，或把错误状态及原始参数标识纳入独立签名；增加“不同非法参数→合法空对象→final”回归。

#### S05-P1-03 — 非有限 deadline 可绕过硬超时

- **位置**：`agent_mini/runtime/loop.py:44-60`，符号 `LoopPolicy.__post_init__`
- **问题描述**：校验只拒绝 `<=0`，`math.inf` 被接受并传给 `asyncio.wait_for`；挂起调用不会由 120 秒策略边界终止。NaN 同样不会命中 `<=0`。
- **判定依据**：FR-RT-05、NFR-REL-02、AC-10 与 `PLAN.md:109-112` 均要求最坏情况必然收敛和 deadline 硬边界。
- **建议方向**：强制 deadline 为有限正数，并为 NaN、正负 Infinity、布尔值/错误类型补运行时负例。

#### S05-P1-04 — deadline 不是从 `Agent.run` 启动时计时

- **位置**：`agent_mini/runtime/loop.py:109-112`，符号 `run_react_loop`
- **问题描述**：同步 `tool_executor.schemas()` 在 `_deadline_at()` 之前执行；Schema 构建耗时不计入总 deadline，若该调用阻塞则硬边界完全无法介入。
- **判定依据**：`Docs/DESIGN.md:281` 明确规定 deadline “自 `Agent.run` 启动计时”；NFR-REL-02 要求全链路硬上限。
- **建议方向**：入口第一时间固定 deadline；明确同步 Schema 快照的耗时/异常契约，必要时将其纳入可取消边界。

#### S05-P1-05 — LLM deadline 分支少计实际调用步数

- **位置**：`agent_mini/runtime/loop.py:117-122,231-241`，符号 `run_react_loop`、`_truncated_result`
- **问题描述**：请求前已递增 `step`，捕获超时后又减 1；第二次 LLM 挂起时实际请求 2 次却返回 `steps=1`。这也使结果与 trace/调用事实不一致。
- **判定依据**：`Docs/DESIGN.md:179,238-248` 定义 steps/step 为 `LLMClient.chat` 调用序号；`Docs/TESTING.md:125` 明确要求 steps 等于实际步骤。
- **建议方向**：统一“尝试调用”和“收到响应”的计数定义；按正式契约保留真实调用次数，并补首次/第二次/后续 LLM deadline 用例。

#### S05-P1-06 — TC-L1-029 只覆盖了定义的一部分

- **位置**：`tests/unit/test_safety_valve.py:94-130`；`Docs/TESTING.md:125,184-190`
- **问题描述**：当前仅覆盖挂起工具和三次完全相同调用；未覆盖 LLM 挂起、规范化键序、不同签名重置、参数纠正、deadline 在下一调用前耗尽、非有限策略值，也没有按 TC 定义注入 async timeout。文档却将 TC-L1-029 标为已覆盖。
- **判定依据**：`AGENT.md` §1.3/§2 要求验收标准与有效测试一一对应；TC-L1-029 的完整前置和预期；`PLAN.md` §5.1 要求阶段全部测试项通过。
- **建议方向**：把 TC-L1-029 拆成可追溯子场景，提供可注入 timeout/cancel 控制，覆盖本报告四个失败探针和规范化/重置正反例。

#### S05-P1-07 — S05 实现早于 OpenSpec change，且首个实现提交没有测试

- **位置**：Git 提交 `1a9bdb3`、`770fda7`、`92127b8`；`AGENT.md:14-35,53-70,262-275`
- **问题描述**：`1a9bdb3` 于 20:38 修改 Agent/loop，`770fda7` 于 20:48 提交功能；S05 proposal/design/tasks/change 到 `92127b8` 20:48:52 才创建。`1a9bdb3` 也没有同提交测试。
- **判定依据**：`AGENT.md` 要求新行为先建 change 再编码，并要求新增/修改函数与测试同 commit；`PLAN.md:307-315` 要求先提交失败测试。
- **建议方向**：不重写历史；登记流程偏差并建立后续 change 修复。S06 起将 change/契约提交置于首个代码提交之前，测试与对应实现同提交并保留逐 TC 红证据。

#### S05-P1-08 — S05 Prompt 未逐字保存，TDD 执行证据缺失

- **位置**：`Docs/PROMPT.md:1338-1358`
- **问题描述**：“原始 Prompt”实际只有三行摘要，第 1348 行还明确承认完整内容未保存；执行摘要没有逐 TC 红灯命令、失败原因和转绿证据。
- **判定依据**：`AGENT.md:75-95` 要求原始 Prompt 逐字保留且只有摘要视为不合格；`PLAN.md:309` 与全局 TDD 规范要求失败测试先行。
- **建议方向**：如实标记历史不可补证，不伪造原文或时序；后续交互逐轮原样追加，TDD 记录至少包含测试标识、红因、实现提交和绿灯命令。

#### S05-P1-09 — Runtime 累计 OpenSpec 主规格自相矛盾

- **位置**：`openspec/specs/runtime/spec.md:5,11,21,35,63,125-151`
- **问题描述**：Purpose 未纳入 S05；同一当前规格既说结果不存在 `truncated`、S04 不实现安全阀，又把它列为必备字段并定义 S05 安全阀。`openspec validate --all --strict` 仍通过，说明结构校验不能替代语义审查。
- **判定依据**：`AGENT.md` §1、§6.1 要求文档与实现同步；`PLAN.md:312` 要求相关文档与实现一致。
- **建议方向**：通过新的修复 change 把主规格改为明确的 S03～S05 累计契约；历史阶段限制移到注释/归档，而不是保留为当前 MUST/MUST NOT。

#### M1-P1-01 — M1 “已达成”声明不满足自身 DoD

- **位置**：`Docs/PLAN.md:296-324`、`README.md:3-42`、`MEMORY.md:3-8`、`Docs/ISSUE.md:385-391`
- **问题描述**：多处声明 M1 已收口，但本报告仍有 P1；README 只有通用测试命令，没有“提问→调工具→回答”的专用命令、输入、预期输出与复现步骤。代表性测试替身链路虽可运行，尚未形成里程碑演示资产。
- **判定依据**：`PLAN.md` §5.2 要求覆盖阶段全部满足 DoD、存在可运行命令/可复现步骤且无 P0/P1。
- **建议方向**：在 S05 P1 修复并复验后再恢复“已达成”；补一条稳定、离线、明确预期的 M1 演示命令或示例脚本/文档步骤。

### P2

#### S05-P2-01 — deadline 代码保留不可达的“无限制”分支

- **位置**：`agent_mini/runtime/loop.py:88,145-153,188-195,311-320`
- **问题描述**：最终 `LoopPolicy.deadline_seconds` 是非可选 float，但 `_deadline_at`、`_remaining`、`_request`、`_execute_tool` 仍保留 `None` 分支；这是 `1a9bdb3` 过渡设计残留，增加安全逻辑分支和误读风险。
- **判定依据**：OpenSpec 工程规范的最小复杂度/无死代码要求；当前 PLR 虽通过，但分支与公开模型不一致。
- **建议方向**：在修复 deadline 时删除不可达路径，或若确需无 deadline，正式写入类型、需求与安全例外。

#### S05-P2-02 — 模块与 docstring 仍停留在 S04 叙述

- **位置**：`agent_mini/runtime/agent.py:1,9-24`、`agent_mini/runtime/loop.py:64-80`
- **问题描述**：S05 已加入策略和安全终止，但入口模块仍标为“S04”，公开类说明没有解释 policy/终止语义；降低公共 API 的自描述性。
- **判定依据**：全局中文简洁 docstring、文档与实现同步要求。
- **建议方向**：使用当前累计职责描述，不在长期模块说明中绑定过期阶段号；补 policy 与截断结果的简洁契约。

#### M1-P2-01 — 运行依赖缺少兼容上界/锁定仍影响后续可复现性

- **位置**：`pyproject.toml` 依赖声明；`Docs/ISSUE.md:288-296`（ISSUE-025）
- **问题描述**：`httpx`、`pydantic`、`pytest` 仍只有下界；本机环境通过不等于未来解析同样版本。该项已登记，不是 S05 新增回归。
- **判定依据**：M1 可复现性与依赖审计要求；ISSUE-025 明确计划在 S18/S21 处理。
- **建议方向**：S18 前验证上界，S21 引入 constraints/lock 策略；CI 记录解析版本。

#### M1-P2-02 — 冻结结果仍允许嵌套参数被外部原地修改

- **位置**：`agent_mini/runtime/result.py:15-25`，字段 `ToolCallTrace.args`
- **问题描述**：Pydantic `frozen=True` 只阻止字段重赋值，`dict` 内部仍可修改；该 S04 遗留债务会影响 M1 轨迹可信度。
- **判定依据**：`DESIGN.md` §3.2 的不可变结果约定；S04 报告保留的 P2 技术债。
- **建议方向**：在 S06 工具模型稳定后改用深不可变表示或返回防御性副本，并补嵌套修改测试。

### Info

#### S05-INFO-01 — S05 范围控制良好

- **位置**：`agent_mini/runtime/`、`pyproject.toml`、提交 `698a515..69ae57e`
- **观察**：未实现 S06 注册表、Memory、Context、HTTP 或真实 API；未新增依赖、重试、HTTP 状态分类或禁用框架。
- **依据**：`PLAN.md` S05 阶段边界、`DESIGN.md` §6 禁止清单。
- **建议**：继续维持阶段隔离。

#### M1-INFO-01 — M1 主干能力已具备但尚不能正式验收

- **位置**：`tests/unit/test_agent.py`、`test_react_loop.py`、`test_safety_valve.py`
- **观察**：离线测试替身已可演示直答、工具往返、正常收敛和两个安全阀；全量回归、覆盖率、wheel 与静态门禁均通过。
- **依据**：本报告 §2 的实跑结果。
- **建议**：修完 P1 后，这些现有资产可直接组成 M1 演示与回归门禁。

## 5. 需求—实现—测试追溯

### 5.1 S05

| 需求/TC | 实现位置 | 测试位置 | 覆盖结论 | 越界 |
| --- | --- | --- | --- | --- |
| FR-RT-05：max_steps | `runtime/loop.py` `LoopPolicy`、`run_react_loop` | `test_safety_valve.py::test_max_steps_stops_exactly_at_limit` | 完整覆盖默认以外的 3 步精确停止、固定文案、原因、调用次数 | 否 |
| FR-RT-05：deadline | `runtime/loop.py` `_deadline_at`、`_remaining`、`_request`、`_execute_tool` | `test_deadline_cancels_hanging_tool_and_fills_batch` | 部分覆盖；工具等待取消/批次补齐有效，但存在起点、有限值、误分类和 LLM steps 缺陷 | 否 |
| FR-RT-05：重复调用 | `runtime/loop.py` `_repeat_count`、`_signature` | `test_repeat_same_call_stops_at_threshold` | 部分覆盖；完全相同调用 3 次有效，非法参数纠正与重置边界缺失且存在签名碰撞 | 否 |
| FR-RT-05：truncated/固定提示 | `runtime/result.py` `AgentResult`；`runtime/loop.py` `_truncated_result` | S05 四个测试 | 三种原因的数据模型存在；max/repeat/工具 deadline 文案有断言，模型 deadline 计数不正确 | 否 |
| TC-L1-016 | 同 max_steps 行 | `test_max_steps_stops_exactly_at_limit` | 是 | 否 |
| TC-L1-029 | deadline、repeat、补齐逻辑 | `test_deadline_cancels_hanging_tool_and_fills_batch`；`test_repeat_same_call_stops_at_threshold` | **部分覆盖，不能标整条通过** | 否 |
| TC-L4-008 | 未实现 | 未实现 | 按计划留 S18 | 否，延后符合计划 |

### 5.2 M1（S00～S05）

| DoD/能力 | 实现/证据 | 验证结果 |
| --- | --- | --- |
| S00 工程与打包基线 | wheel、package-data、smoke/结构测试 | 通过；wheel 含 `schema.sql` 且仓库外可导入 |
| S01 单轮 Chat Completions | `agent_mini/llm/`、L2 契约测试 | 累积 contract 64 通过；S01 报告 P0/P1 已有修复记录 |
| S02 错误分类与重试 | `llm/client.py`、错误/重试测试 | 累积测试通过；已登记 S20 异常根迁移债务 |
| S03 单轮直答 | `Agent.run`、`test_agent.py` | 代表性直答测试通过 |
| S04 工具循环与配对 | `run_react_loop`、`test_react_loop.py` | 代表性两步工具链通过；S04 P0/P1 修复已记录 |
| S05 安全阀 | `LoopPolicy`、`AgentResult`、S05 四测 | 主路径通过，但本报告发现多个 P1 |
| 全量回归 | 103 tests | 通过 |
| 覆盖率 ≥80% | 94.51% | 通过 |
| wheel 完整 | 临时 wheel/target 验证 | 通过 |
| 无禁用框架 | 依赖 diff 与扫描 | 通过 |
| 可运行演示步骤 | 评估临时选取 4 个 pytest 节点 | 功能可演示；仓库文档未交付正式步骤 |
| 无 P0/P1 | 本报告问题清单 | **不通过** |
| 覆盖阶段全部满足 DoD | S05 流程/规格/TDD 缺陷 | **不通过** |

## 6. 边界抽查

- **是否越界实现 S06 工具注册、S13 Memory、S16 Context、S18 HTTP/真实 API：否。** 仅保留 S04 `ToolExecutor` 协议替身。
- **是否新增 S02 重试、退避或 HTTP 状态分类：否。** S05 未修改 LLM 层或依赖。
- **是否执行 TC-L4-008：否。** 明确、正确地延后至 S18。
- **安全阀是否都会返回结果而非抛专用异常：主路径是。** 但工具本地 `TimeoutError` 被误认为安全阀，属于错误终止。
- **deadline 是否覆盖每次 LLM/工具调用：形式上使用 `asyncio.wait_for`，但未覆盖计时前的 `schemas()`，且 Infinity/NaN 可绕过。**
- **中断时是否补齐本批 tool_call_id：已覆盖工具 deadline；repeat 分支代码也补齐，但没有多调用 repeat 测试。**
- **重复是否按规范化 JSON 键序：实现使用 `sort_keys=True`；没有测试证明键序等价、不同签名重置和错误参数隔离。**
- **M1 是否依赖真实网络/本机密钥：否。** 现有演示使用离线替身；TC-L4-008 正确留待 S18。
- **M1 是否已有可复现专用演示：否。** 通用 `pytest` 命令存在，但没有里程碑场景的输入、指定节点和预期输出说明。

## 7. 技术债与后续阶段影响

| 后续阶段 | 风险/技术债 | 触发条件 | 建议时机 |
| --- | --- | --- | --- |
| S06 | 工具 handler 抛内置 `TimeoutError` 会被当成全局 deadline | 注册真实工具或第三方 handler | S06 开工前修 S05-P1-01，并固化工具异常边界 |
| S06 | 非有限/起点滞后的 deadline 无法保证注册表 Schema/handler 总时限 | Schema 构建变复杂或工具挂起 | S06 前修 S05-P1-03/04 |
| S06 | `ToolCallTrace.args` 浅冻结 | 真实注册表返回嵌套参数并被下游缓存 | S06 模型稳定时处理 M1-P2-02 |
| S13 | invalid arguments 与空对象签名碰撞会把跨轮纠正误判为死循环 | Memory 恢复后模型进行参数纠错 | S13 前修 S05-P1-02，并确保计数只在当前 run 内 |
| S13/S16 | `steps` 与 trace/实际请求数不一致，影响持久化、裁剪和预算核对 | 保存 AgentResult 或按步数统计 | S13 前修 S05-P1-05 |
| S18 | HTTP 需要把安全阀稳定映射为成功响应与可观测元数据 | 实现 TC-L4-008 | S18 前确保三种终止原因、步数和 tool 配对回归完整 |
| S18/S21 | 依赖只有下界可能导致干净环境漂移 | CI/发布重新解析依赖 | 按 ISSUE-025 在 S18 验证上界、S21 收口锁定 |
| 所有后续阶段 | 当前累计 OpenSpec 含相互冲突的 MUST/MUST NOT | S06 基于主规格继续追加 | 下一个功能 change 前先修 S05-P1-09 |

## 8. 总体结论

### 8.1 S05 是否可进入 S06

**不可进入。** 现有 `max_steps` 主路径、工具 deadline 取消、重复 3 次与正常收敛测试均通过，但 deadline 和重复检测存在可复现的协议/硬边界缺陷，TC-L1-029 未完整覆盖，流程与累计规格未闭环。

进入 S06 前必须处理：

1. S05-P1-01：区分工具本地 `TimeoutError` 与全局 deadline。
2. S05-P1-02：消除非法参数与合法空对象的重复签名碰撞。
3. S05-P1-03：拒绝 NaN/Infinity 等非有限 deadline。
4. S05-P1-04：从 `Agent.run` 启动时建立 deadline 边界。
5. S05-P1-05：让 `steps` 与实际 LLM 调用次数一致。
6. S05-P1-06：补齐 TC-L1-029 的可控、可追溯测试矩阵。
7. S05-P1-07：如实登记 OpenSpec/TDD 提交时序偏差，并从 S06 起执行正确顺序。
8. S05-P1-08：修正 Prompt/TDD 记录规则的实际执行，历史缺证不得伪造。
9. S05-P1-09：通过新 change 修复累计 runtime 主规格。

### 8.2 M1 是否达成

**当前不达成。** 可对话骨架的主要能力、全量回归、覆盖率、wheel 与禁用框架检查均已具备；但 M1-P1-01 和上述 S05 P1 直接违反“所有阶段 DoD”“可复现演示”“无 P0/P1”三项里程碑准出条件。

M1 恢复验收前必须：

1. 完成并复验全部 S05 P1。
2. 将 `PLAN`/README/MEMORY/ISSUE 的 M1 状态与事实同步。
3. 提供一条离线、稳定、指定输入与预期结果的“提问→调工具→回答→安全阀”演示命令/步骤。

可选建议：删除不可达 deadline 分支、更新过期 docstring、后续处理依赖锁定与深不可变 trace。

## 9. 工作区状态与副作用

### 9.1 状态对比

- 评估开始前：`git status --short --branch` 仅输出 `## main...origin/main`。
- 只读检查结束后、报告写入前：状态仍干净。
- 本轮按全局评估规则新增 `Docs/S05-report.md`，并在 `Docs/PROMPT.md` 追加本轮原始 Prompt；没有修改实现、测试、OpenSpec、PLAN、Issue、README、MEMORY 或远程状态。

### 9.2 评估副作用

- coverage 数据定向写入仓库外：`C:\Users\Ryan\AppData\Local\Temp\agent-mini-s05-m1.coverage`。
- wheel/临时 target：`C:\Users\Ryan\AppData\Local\Temp\agent-mini-s05-m1-audit-b428cb8d0f134dc389cbc5a818ddfd90`。
- 历史红灯重建目录：`C:\Users\Ryan\AppData\Local\Temp\agent-mini-s05-red-dfd91c55a3cf4fb0962b65dc152ce34a`，并生成同前缀的 base/test zip 临时文件。
- wheel 构建可能刷新仓库内被忽略的 `agent_mini.egg-info/` 元数据；它不出现在普通 `git status`，未由评估 Agent 自动删除。
- 评估结束时 `git status --short --ignored` 还显示仓库内 `.coverage`、`.mypy_cache/`、`.pytest_cache/`、`.ruff_cache/`、各包/测试的 `__pycache__/` 与 `agent_mini.egg-info/`。评估开始时只记录了普通 status，未记录 ignored 基线，因此无法严谨区分哪些是既有产物、哪些在本轮被刷新。
- 上述临时文件均为评估证据或被忽略构建元数据。需要清理时，请人工确认路径后删除；本轮未执行任何删除命令。

## 10. 修复记录（2026-10-22）

| 报告项 | 修复 | 证据 |
| --- | --- | --- |
| S05-P1-01 工具本地 TimeoutError | 使用 `asyncio.timeout` 的 `expired()` 区分等待器与 coroutine 异常；本地异常归 `tool_execution_error` | `test_tool_local_timeout...` |
| S05-P1-02 签名碰撞 | 仅成功调用参与重复签名；invalid_arguments/失败调用重置计数 | 非法→合法 `{}` 测试 |
| S05-P1-03 非有限 deadline | `math.isfinite` + bool/正数校验 | inf/nan/True/0 参数化测试 |
| S05-P1-04 deadline 起点 | `run_react_loop` 先建立 deadline，再取 schemas | 代码顺序 + 测试矩阵 |
| S05-P1-05 steps 少计 | LLM 超时保留已尝试 step，不再回退 | LLM 挂起测试 steps=2 |
| S05-P1-06 TC-L1-029 覆盖 | 补工具/LLM deadline、非有限值、签名纠正/重置、空对象 | 11 个 S05 测试 |
| S05-P1-07/08 流程/Prompt | 新 change 记录历史时序偏差；不伪造历史 Prompt/红灯 | ISSUE-031、本表 |
| S05-P1-09 累计规格 | 新 change MODIFIED S03/AgentResult；Purpose 改 S03–S05 | runtime 主规格 |
| M1-P1-01 | P1 修复复验；M1 恢复条件与离线演示命令 | README M1 演示命令 |
| S05-P2-01 死分支 | 删除 deadline None 分支 | loop.py |
| S05-P2-02 docstring | 更新 S05 职责与 policy/终止语义 | agent/loop 模块说明 |

**复验**：112 passed；覆盖率 95.72%；unit 48、contract 64；`mypy agent_mini tests` 49 files 0 errors；ruff/format/openspec/wheel 通过。S05 可进入 S06；历史 Prompt 红灯证据缺失仍如实保留，不伪造。

