# S04「Runtime：工具调用循环（ReAct 核心）」产出评估报告

> 评估日期：2026-10-22  
> 基准提交：`16973e2`（`main`，与 `origin/main` 一致）  
> 阶段基线：`45b63b4`（S03 评估修复收口）  
> 评估性质：独立代码评估；除本报告与 Prompt 记录外，不修改实现、测试、Issue、PLAN 或 OpenSpec  
> 总体结论：**不通过；修复 P0/P1 后方可进入 S05**（后续修复见 §10；修复后 S04 可进入 S05）

## 1. 评估范围与基准

### 1.1 实际读取内容

| 类别 | 路径与章节 |
| --- | --- |
| 全局规范 | `AGENT.md` 全文；`openspec/specs/engineering-standards/spec.md` 的代码、可读性、注释、命名、目录、测试、错误、日志、依赖、导入与门禁条款 |
| 阶段范围 | `Docs/PLAN.md` S03–S06、S18、§5 DoD、§6 进度记录 |
| 功能需求 | `Docs/REQUIREMENT.md` FR-RT-02、FR-RT-03、FR-RT-04、FR-RT-06、FR-RT-08、AC-09、AC-22 |
| 设计契约 | `Docs/DESIGN.md` §1、§2.2、§3.1、§3.2 全部子节、§3.3、§3.7、§4、§6–§8、§10 |
| 测试定义 | `Docs/TESTING.md` §1–§3、TC-L1-015/024/028/030、TC-L2-009/010、TC-L3-006、§4.2.4、§6 |
| 过程记录 | `Docs/PROMPT.md` S04 Prompt 与执行摘要；`Docs/ISSUE.md` ISSUE-029/S04 记录；`MEMORY.md`、`README.md` |
| 实现与测试 | `agent_mini/runtime/`；相关 `agent_mini/llm/` 模型；`tests/unit/test_agent.py`、`tests/unit/test_react_loop.py`、包结构测试；`pyproject.toml` |
| OpenSpec | `openspec/specs/runtime/spec.md`；归档 change `2026-10-22-s04-runtime-react-loop` 的 proposal/design/tasks/spec |
| 流程证据 | 提交 `34c9758`、`ffd5ce6`、`a69ec1f`、`78e9aee`、`20807ce`、`16973e2` 及 `45b63b4..16973e2` diff |

本次使用 `code-review-and-quality` 技能，以正确性、测试、架构、安全、性能五个维度交叉复核；其中安全维度直接促成了独立工具结果密钥探针。

### 1.2 PLAN、DESIGN、TESTING 的一致性与缺口

1. 三份基准对 S04 的核心边界基本一致：本阶段实现 Runtime 工具往返、消息配对、公开 trace 与错误回灌；S05 安全阀、S06 真实注册表、S13–S16 Memory/Context、S18 HTTP/真实 API均后置。
2. PLAN 要求“参数错误可回灌修正”，TESTING TC-L1-028/TC-L2-009 要求“非法调用→合法调用→最终答案”，OpenSpec 也写明第 2 步合法；现有测试却在非法调用后直接返回最终文本，验收链存在实质缺口。
3. TESTING TC-L3-006 的完整定义要求真实 calculator，但 PLAN S04 与 §4.2.4 又明确本阶段仅用协议替身、真实 calculator 留 S06/S18；应明确标成“部分覆盖”，不能把替身测试写成 TC-L3-006 已完成。
4. OpenSpec 主规格同时保留 S03 的“只包含 reply/steps/usage、无 trace/tool_calls”与 S04 的增量字段要求，Purpose 也仍只描述 S03；结构校验通过，但累计规格语义自相矛盾。

## 2. 复核命令与结果

| 命令/检查 | 关键结果 | 结论 |
| --- | --- | --- |
| `git status --short --branch` | 评估前 `main...origin/main`，无 tracked 变更 | 通过 |
| `ruff format --check .` | 51 files already formatted | 通过 |
| `ruff check .` | All checks passed | 通过 |
| `mypy agent_mini tests` | 48 个源文件无错误 | 通过 |
| `pytest -m unit` | 33 passed、64 deselected，0.28s | 通过 |
| `pytest -m contract` | 64 passed、33 deselected，35.41s | 通过 |
| `pytest` | 97 passed，36.25s | 通过 |
| `pytest --cov=agent_mini --cov-report=term-missing --cov-fail-under=80` | 97 passed；总覆盖率 95.70%；runtime loop 93% | 门禁通过；工具执行异常分支未覆盖 |
| `openspec validate --all --strict` | 4 passed、0 failed；仅有长 Requirement 提示 | 结构校验通过，未发现语义冲突 |
| `python -m pip check` | No broken requirements found | 通过 |
| `python -m pip wheel . --no-deps` + 临时 target 安装 | wheel 构建/安装成功；runtime 四个模块与 `schema.sql` 均存在 | 通过 |
| 仓库外导入与资源读取 | `Agent`、循环 Protocol/模型均可导入；`schema.sql` 可读 | 通过 |
| 禁止项扫描 | runtime/相关测试未发现 `eval/exec/__import__`、shell=True、裸 noqa/type-ignore、相对导入、skip/xfail | 通过 |
| 独立工具结果密钥探针 | `independent_secret_in_public_result=True` | **失败；公开 trace 泄密** |
| 非法参数后合法修正探针 | 3 步、仅合法调用执行、失败/成功 trace 顺序正确 | 实现可工作，但正式测试未固化 |
| 工具执行异常探针 | 异常转 `tool_execution_error`，模型随后收敛 | 实现可工作，但正式测试未固化 |
| schemas 每步透传探针 | 每次 LLM 请求均有 tools | 通过；正式测试未显式断言 |
| 冻结深度探针 | `ToolCallTrace.args` 仍可原地修改 | 浅冻结技术债 |

### 2.1 未复跑项目

- 未调用真实 DeepSeek API、HTTP、MySQL、日志、Memory、Context 或真实 calculator：分别属于 S06、S13–S19；S04 明确只使用测试替身。
- 未执行 `pip install -e .`：会在仓库写入安装元数据；本次以 wheel 构建、临时 target 安装和仓库外导入替代。
- 未复建 S04 红灯：仓库只保存“基线 + 当前测试且替身去除 ToolOutcome 依赖”的文字摘要，没有保存可直接执行的测试快照或逐 TC 红因；不能在不自行改写测试的情况下原样复现。
- 未在 Linux 复跑：当前环境为 Windows/Python 3.13.9；跨平台门禁属于项目最终 DoD。

## 3. 维度结论

| 维度 | 结论 | 一句话理由与证据 |
| --- | --- | --- |
| 需求与阶段范围 | 通过 | diff 只扩展 runtime、测试与文档；未实现 S05/S06/S13–S18 职责，见 `45b63b4..HEAD` |
| ReAct 循环与收敛 | 通过 | 两步/三步、混合正文、多工具顺序均通过，见 `run_react_loop` 与 3 个对应单测 |
| assistant/tool 协议配对 | 通过 | assistant 先入历史、每个 call_id 按序生成 tool 消息；现有断言与探针一致 |
| 工具错误边界 | 有条件通过 | JSON 参数错误、未知工具、执行异常实现可回灌；正式测试未覆盖“修正后合法执行”和执行异常 |
| ThoughtStep 与隐私 | 不通过 | reasoning 未公开且字段契约正确，但独立存在于工具结果中的假密钥会进入公开 `AgentResult` |
| AgentResult/数据模型 | 有条件通过 | usage 聚合、字段增量、基础校验正确；嵌套 args 可变且 ToolOutcome 允许矛盾状态 |
| 测试质量与 TDD | 不通过 | 97 个测试全绿且覆盖率达标，但两个必验错误分支缺有效回归，红灯证据仅为归档后汇总 |
| 全局代码规范 | 有条件通过 | 自动门禁全绿；主循环超过 50 行、测试未镜像 runtime 目录、公共 API docstring 契约不完整 |
| 打包与分发 | 通过 | wheel 含 runtime 新模块与 `systemdb/schema.sql`，临时 target 外部导入成功 |
| 依赖与禁框架 | 通过 | S04 未修改依赖；仅 httpx/pydantic 与已 pin 的开发工具，无禁用 Agent 框架 |
| OpenSpec、Git 与流程 | 不通过 | change 先于实现且 strict 通过，但归档后又增加阶段验收测试且未新建 change/记录例外 |
| 文档闭环与可复现性 | 不通过 | 测试数量/命令可复现；TC 覆盖声明、累计 runtime 规格和 TDD 记录与事实不完全一致 |

## 4. 问题清单

### P0

#### S04-P0-01：公开工具结果摘要可泄露未出现在调用参数中的密钥

- **位置**：`agent_mini/runtime/loop.py:137-146`，符号 `_tool_trace`；`agent_mini/runtime/loop.py:177-195`，符号 `_secret_values`/`_redact_text`；`tests/unit/test_react_loop.py:264-280`。
- **问题描述**：observation 只替换从调用参数敏感键收集到的值。若工具自身返回凭据、Cookie、下游 token 或其他未出现在输入参数中的秘密，该原文会进入 `ToolCallTrace.observation`，继而出现在公开 `AgentResult`。定向探针以安全参数调用工具、让结果单独包含唯一假密钥，得到 `independent_secret_in_public_result=True`。现有测试使用同一个 `api_key` 同时出现在参数和工具回显中，只覆盖“从参数推导 secret 后替换”的窄路径。
- **判定依据**：`Docs/DESIGN.md` §3.2.3 要求“结果摘要先脱敏再截断”；FR-RT-08、TC-L1-030、AC-22 要求公开 trace 不泄密；工程规范“日志规范/脱敏”禁止响应出现完整 token/secret；TESTING §6.3 将密钥泄露定义为 P0。
- **建议方向**：建立统一、可复用的公开载荷脱敏器，对参数与独立工具结果都执行字段/模式/已知敏感值过滤后再截断；增加结果独立含假密钥、cookie/authorization/token 变体及嵌套参数回归。S19 Formatter 不能替代 Runtime 公共结果边界的脱敏。

### P1

#### S04-P1-01：TC-L1-028/TC-L2-009 的“修正后合法执行”没有被正式测试

- **位置**：`tests/unit/test_react_loop.py:223-245`，符号 `test_invalid_arguments_are_not_executed_and_are_refed`；`Docs/TESTING.md:124,140,177,179`；`Docs/PLAN.md:100`。
- **问题描述**：脚本第 1 步返回非法参数，第 2 步直接返回字符串“修正后完成”，并没有产生合法 tool_call、执行 handler、回灌成功结果后再收敛。因此测试名称和固定回复文本不能证明模型修正路径，文档却声明 TC-L1-028/TC-L2-009 已覆盖“修正收敛”。定向探针表明当前实现恰好可工作，但回归保障缺失。
- **判定依据**：TC-L1-028 要求“错误→合法调用→最终答案”及 handler 副作用次数；TC-L2-009 要求修正后正常执行且 trace 记录失败与恢复；OpenSpec runtime spec:97-104 同样要求第 2 步合法；AGENT §2 禁止弱化断言。
- **建议方向**：将测试改为至少三次 LLM 响应，显式断言非法调用未执行、合法调用恰好执行一次、两条 tool trace 分别失败/成功、最终第三步收敛；分别覆盖未知工具与参数错误。

#### S04-P1-02：工具执行异常的强制回灌契约没有回归测试

- **位置**：`agent_mini/runtime/loop.py:117-134`，符号 `_execute_call`；`tests/unit/test_react_loop.py`；覆盖率缺口 `loop.py:129-130`。
- **问题描述**：实现会把 executor 抛出的异常转换为 `tool_execution_error`，定向探针也验证能继续收敛，但正式测试没有任何 executor 抛异常场景。该分支是 FR-RT-06/OpenSpec 的 MUST，而归档 tasks 3.3 和文档已标记完成。
- **判定依据**：FR-RT-06；DESIGN §3.3；OpenSpec “工具错误结构化回灌”；工程规范错误边界；AGENT §2“新增或修改的每个函数/模块必须有对应测试”。
- **建议方向**：增加会抛异常的执行器替身，断言异常不逃逸、原 call_id 配对、错误码/可读内容正确、模型获得错误结果后仍可继续并收敛；同时确认取消信号不被吞。

#### S04-P1-03：runtime 主规格保留了与 S04 当前接口冲突的 S03 排他性要求

- **位置**：`openspec/specs/runtime/spec.md:3-5,9-21,33-40` 与 `:56-103`。
- **问题描述**：主规格 Purpose 仍只描述 S03；S03 Requirement 仍声称结果“不包含 tool_calls/trace”且 AgentResult“只包含 reply/steps/usage”，后续 S04 Requirement 又要求这些字段存在。OpenSpec strict 只验证结构，没有识别累计规格语义冲突。
- **判定依据**：AGENT §1/§6/§7 要求归档后的主规格与实现一致；OpenSpec 全局规范“发现上下位文档冲突时停止并登记”；当前 `AgentResult` 的字段事实见 `runtime/result.py:46-56`。
- **建议方向**：通过新的修复 change 修改主规格，把 S03 条款表述为“无 executor 的直答场景/历史阶段基线”，删除当前时态的排他性字段断言，并更新 Purpose 为覆盖 S03+S04 的累计 Runtime 契约。

#### S04-P1-04：OpenSpec 归档后继续增加 S04 验收测试，未建新 change 或记录例外

- **位置**：提交序列 `78e9aee` → `20807ce` → `16973e2`；`Docs/PLAN.md:303-315`。
- **问题描述**：S04 change 在 `78e9aee` 归档，随后 `20807ce` 才加入“至少 3 步收敛”验收测试并修改 PLAN/TESTING/ISSUE/MEMORY，`16973e2` 又补 TDD 红证据。归档 change 的 tasks 仍显示此前全部完成，仓库没有后续 change 或例外记录。
- **判定依据**：PLAN DoD 明确“归档在实现、测试、文档全部完成后执行；归档后阶段内变更必须新建 change 或记录例外”；AGENT §6 要求验证完成后再归档。
- **建议方向**：以后在所有验收测试与记录齐全后归档；本次通过独立修复 change 处理本报告缺陷并记录为何发生归档后变更，禁止改写已归档目录。

#### S04-P1-05：TDD 红灯证据不可逐 TC 复核，且在阶段归档后才补记

- **位置**：`Docs/PROMPT.md:1290-1299`；提交 `16973e2`；归档 tasks §2。
- **问题描述**：记录只称“基线叠加当前测试、替身去 ToolOutcome 依赖，8 failed/1 passed”，没有保存替身改法、命令输出或 TC 逐项红因；该记录在实现、文档和 OpenSpec 归档之后才提交。当前无法不改写测试地原样重建，且与原 Prompt “不得只给总数、逐 TC 红因”直接冲突。
- **判定依据**：AGENT §2 红→绿→重构；TESTING §2.1 红证据规则；S04 原 Prompt 第 19 条与输出第 7 条；OpenSpec tasks 2.1–2.5。
- **建议方向**：修复阶段保留可直接运行的失败测试提交或仓库外只读重建脚本/完整命令摘要，逐 TC 记录失败节点和预期红因；不得把归档后的汇总当成先红证据。

### P2

#### S04-P2-01：主循环超过全局 50 行函数上限

- **位置**：`agent_mini/runtime/loop.py:38-114`，符号 `run_react_loop`。
- **问题描述**：函数从初始化、请求、分支、工具执行、trace 组装到最终结果均在同一函数，物理行数明显超过 50；S05 加入步数、deadline、重复检测后会继续膨胀。
- **判定依据**：OpenSpec 工程规范 D-02、R-04/R-05；CR-03。
- **建议方向**：在 S05 前后按“处理工具响应/构造最终结果/执行并配对工具”拆分，不改变消息顺序和异常边界。

#### S04-P2-02：Runtime 单测未遵守目录镜像规范

- **位置**：`tests/unit/test_react_loop.py`、`tests/unit/test_agent.py`；对应实现 `agent_mini/runtime/`。
- **问题描述**：新增 S04 测试继续放在 unit 根目录，而 TESTING §2.2 和全局目录规范要求按包镜像，目标位置应为 `tests/unit/runtime/`。后续 S05 会进一步增加同层测试，平铺目录将持续恶化。
- **判定依据**：`Docs/TESTING.md:62-68`；OpenSpec 工程规范“目录镜像规则”和 CR-06。
- **建议方向**：在独立整理提交中迁移 runtime 测试目录并确保 marker、导入与收集数量不变。

#### S04-P2-03：公共 Protocol/循环 docstring 未完整说明副作用与异常

- **位置**：`agent_mini/runtime/loop.py:17-43`，`ToolOutcome`、`ToolExecutor`、`run_react_loop`；`agent_mini/runtime/agent.py:9-26`。
- **问题描述**：docstring 简洁但只复述用途，没有说明 messages 会被原地追加、无 executor 收到 tool_calls 的异常、空最终响应异常、执行器异常回灌和无安全阀边界。
- **判定依据**：OpenSpec 工程规范“注释规范”要求公共 API 写清前置条件、返回语义、可能异常与副作用；CR-04。
- **建议方向**：补充契约型中文 docstring，避免重复逐行实现。

#### S04-P2-04：结果模型仅浅冻结，ToolOutcome 可表达矛盾状态

- **位置**：`agent_mini/runtime/result.py:13-56`；`agent_mini/runtime/loop.py:17-23`。
- **问题描述**：`frozen=True` 不阻止 `ToolCallTrace.args` 字典原地修改；探针已确认可变。`ToolOutcome` 还允许 `ok=True` 携带 error_code 或 `ok=False` 无 error_code，使 S06 适配器错误可生成自相矛盾 trace。
- **判定依据**：OpenSpec 将 ThoughtStep/ToolCallTrace 称为冻结模型；DESIGN §3.2.3/§3.3 要求结构化且稳定的公开结果。归档 design 已记录浅冻结风险，因此当前列为技术债而非 P1。
- **建议方向**：S06 适配前决定深不可变策略，并为 ToolOutcome 建立成功/失败不变量或工厂方法；增加非法组合测试。

#### S04-P2-05：S05 接入点只存在于注释，没有可组合的循环策略钩子

- **位置**：`agent_mini/runtime/loop.py:38-50`；归档 design “循环”决策。
- **问题描述**：当前是无参数 `while True`，注释称 S05 在外层接入。总超时可由外层包裹，但 max_steps 与重复签名检测必须观察循环内部状态，因此 S05 仍需改动核心函数与消息补齐路径。
- **判定依据**：S04 原 Prompt 要求为 S05 预留接入点；PLAN S05 以 S04 循环为输入；DESIGN §3.2.4 要求安全阀与未完成 call_id 配对。
- **建议方向**：S05 通过显式策略/配置参数接入，并先补中断时消息配对回归；不要仅用外层 timeout 冒充全部安全阀。

#### S04-P2-06：观察长度常量重复且关键传参断言不足

- **位置**：`agent_mini/runtime/loop.py:11-14,137-146`；`agent_mini/runtime/result.py:9,25-29`；`tests/unit/test_react_loop.py:84-180`。
- **问题描述**：200 字符上限在两个模块重复定义和重复截断；测试只断言总 token，没有断言 prompt/completion 分项，也未显式断言每一次请求收到同一 tools 快照。
- **判定依据**：全局规范禁止重复业务逻辑；FR-RT-03/08 与 OpenSpec 要求所有调用 usage 求和、每次请求传 schemas。
- **建议方向**：建立单一公开常量/单一截断边界，增加 usage 三分项与逐请求 schemas 快照断言。

### Info

#### S04-INFO-01：未发现阶段越界

- Runtime 没有实现重试/退避/HTTP 状态分类、max_steps/deadline/重复检测、工具注册表、Memory、Context、HTTP、配置容器或真实 API；S02 客户端已有重试不属于本阶段新增。

#### S04-INFO-02：核心正常路径实现清晰且顺序正确

- schemas 本轮只取一次并传给每次模型调用；多工具串行执行并保持声明顺序；伴随 content 不提前返回；usage 按调用累计；reasoning 只保留在 assistant 私有消息，公开 trace 仅保留布尔值。

#### S04-INFO-03：无新增依赖

- `45b63b4..HEAD` 未修改 `pyproject.toml`。当前运行依赖为 httpx/pydantic；pytest-asyncio、pytest-cov、respx、ruff、mypy 均有受限 dev 版本范围；未命中禁用 Agent 框架。运行依赖只有最低版本的既有漂移风险继续由既有债务管理，不是 S04 新增问题。

## 5. 需求—实现—测试追溯

### 5.1 功能需求

| FR | 实现位置 | 测试位置 | 覆盖结论 | 越界 |
| --- | --- | --- | --- | --- |
| FR-RT-02 工具调用决策 | `run_react_loop` 工具分支、`ToolExecutor` | 两步、多工具、未知工具测试 | 覆盖 | 无真实注册表 |
| FR-RT-03 多步循环 | `run_react_loop` 循环与 usage/steps 聚合 | `test_three_steps_converge` | S04 子集覆盖；带会话追问留后续 | 无安全阀/会话 |
| FR-RT-04 消息顺序 | assistant append + 逐 call_id tool append | 两步配对、多工具顺序测试 | 覆盖 | 无中断补齐；属 S05 |
| FR-RT-06 工具错误回灌 | `_execute_call`、call.error_code 分支 | 非法参数、未知工具测试 | **部分**；合法修正和执行异常未正式覆盖 | 真实 Schema/handler 留 S06 |
| FR-RT-08 公开 trace/私有 reasoning | `ThoughtStep`、`ToolCallTrace`、assistant reasoning | reasoning、脱敏、trace 字段测试 | **部分失败**；独立工具结果密钥泄露 | 日志/MySQL/Memory 留后续 |

### 5.2 测试用例

| TC | 实现与测试位置 | 是否覆盖 | 是否越界/后续边界 |
| --- | --- | --- | --- |
| TC-L1-015 | `run_react_loop`；`test_two_step_tool_loop_pairs_messages` | 是：两步、最终 reply、配对 | 安全阀 S05、session S13 |
| TC-L1-024 | ThoughtStep/ToolCallTrace；trace 与 reasoning 测试 | S04 字段子集覆盖 | `react.step` 日志 S19 |
| TC-L1-028 | `_execute_call`；非法/未知工具测试 | **不完整**：没有合法修正执行，未测 executor 异常 | 真实 registry/Schema S06 |
| TC-L1-030 | reasoning 私有回传、公开 trace 脱敏 | **不通过**：独立结果秘密可泄露 | HTTP/MySQL/log/Memory 扫描留 S17–S19 |
| TC-L2-009 | ToolCall.error_code 回灌 | **不完整**：保留 call_id，但未测失败→成功恢复 trace | 严格 JSON 解析已由 S01 覆盖，真实工具 S06 |
| TC-L2-010 | 混合 content + 两调用；消息/trace 顺序 | 是 | 真实 provider S18 |
| TC-L3-006 | `ToolExecutor` 替身、tool_traces | 仅替身子集 | 真实 calculator/注册表按文档留 S06/S18；不应记为 L3 已执行 |
| TC-L4-010/011 | 无 | 未覆盖，符合阶段边界 | S18 HTTP/真实工具回填 |

## 6. 边界抽查

- **是否存在越界实现重试/退避/HTTP 状态分类：否。** 这些逻辑仍在 S02 的 LLM 层，S04 diff 未新增。
- **是否存在越界实现 S05 安全阀：否。** 没有 max_steps、deadline、重复调用检测或 truncated；当前无限循环是明确的阶段性风险。
- **是否存在越界实现 S06 注册表/Schema 生成：否。** runtime 只定义 Protocol/ToolOutcome，未导入 `agent_mini.tools`。
- **是否越界到 Memory/Context/HTTP/配置/真实 API：否。** 未读取环境变量或访问外部网络。
- **混合正文是否被提前返回：否。** 有 tool_calls 时 content 只进入 assistant 历史，最终 reply 取无调用的后续响应。
- **每个 call_id 是否成对：正常收敛路径是。** 多调用按声明顺序产生 tool 消息；S05 中断补齐尚未实现。
- **非法参数是否执行 handler：否。** `call.error_code` 在调用 executor 前返回；正式测试有断言。
- **未知工具是否证明未执行 handler：未完全证明。** 替身把 registry 路由和 handler 合并为一个 `execute`，没有独立副作用计数。
- **执行异常是否结构化回灌：实现和定向探针是；正式用例否。**
- **公开 trace 是否暴露 reasoning：未发现。** 私有原文只随 assistant 消息回传，公开结构只含 `reasoning_present`。
- **公开 trace 是否可能泄露工具结果密钥：是。** 见 S04-P0-01。
- **是否存在 429/5xx 重试断言混入 S04：否。** 这些仍由 S02 contract 测试负责。

## 7. 技术债与后续阶段影响

| 后续阶段 | 风险 | 触发条件 | 建议处理时机 |
| --- | --- | --- | --- |
| S05 | P0 泄密会随安全阀结果继续对外传播 | 安全阀返回已有 tool_traces | **进入 S05 前**修复并回归 |
| S05 | 无内部策略钩子，max_steps/repeat 必须重构主循环 | 加入步数、deadline、重复检测 | S05 开工时先稳定循环状态模型 |
| S05 | 中断时未完成 call_id 的配对尚无测试 | 工具超时/取消发生在批次中间 | S05 首批红灯覆盖 |
| S06 | ToolOutcome 状态可矛盾、未知工具未区分 registry 与 handler | 注册表实现 Protocol | S06 适配前建立结果不变量与副作用测试 |
| S06 | S04 对 Schema 错误只复用 error_code，没有真实校验路径 | Pydantic 参数模型落地 | S06 回填 TC-L1-028/TC-L3-006 |
| S13/S16 | reasoning 私有历史目前只在单次 run 内存列表中存在 | 跨轮存储/裁剪落地 | 按完整轮次保存，不把公开 trace 回灌上下文 |
| S18 | observation 泄密会直接进入 HTTP JSON | AgentResult 映射为响应 | 必须在 S18 前已有统一脱敏回归 |
| S18 | OpenSpec 字段冲突会误导 HTTP Schema | 生成/手写响应模型 | 在 S05 前修复累计 runtime 主规格 |
| S19 | Runtime 与 Formatter 各自脱敏可能产生规则漂移 | 结构化日志接入 | 抽单一脱敏策略，分清公共结果与日志边界 |

## 8. 总体结论

S04 的核心工具循环、三步收敛、assistant/tool 配对、混合正文优先级、usage 聚合和 reasoning 私有回传均已实现，97 个测试、静态门禁、OpenSpec 结构校验与 wheel 验证也可复现。但公开工具结果仍存在真实密钥泄露路径，错误修正/执行异常两条强制契约没有被正式测试，累计 OpenSpec 规格与当前接口冲突，且阶段在归档后才补验收测试与红灯摘要。

**结论：S04 暂不可进入 S05。**

进入 S05 前必须处理：

1. **S04-P0-01**：修复独立工具结果秘密进入公开 trace 的泄漏，并增加安全回归。
2. **S04-P1-01**：补全非法参数/未知工具后合法调用并最终收敛的真实测试链。
3. **S04-P1-02**：补工具执行异常结构化回灌与继续收敛测试。
4. **S04-P1-03**：通过新 change 消除 runtime 主规格的 S03/S04 累计语义冲突。
5. **S04-P1-04**：为归档后变更补流程说明，并让本轮修复走独立 OpenSpec change。
6. **S04-P1-05**：在修复 change 中留下可逐 TC 复核的红→绿证据。

可选建议：S05 同步处理主循环拆分、测试目录镜像、公共 API docstring、深冻结/ToolOutcome 不变量、统一观察长度常量及循环策略钩子。

## 9. 工作区状态与副作用

### 9.1 状态对比

- 评估开始前：`git status --short --branch` 为 `## main...origin/main`，无 tracked 变更。
- 门禁与探针结束后：仍为 `## main...origin/main`，无 tracked 变更。
- 报告落盘后：仅新增 `Docs/S04-report.md`、修改 `Docs/PROMPT.md`；未修改实现、测试、Issue、PLAN、OpenSpec 或远程状态，未提交、未推送。

### 9.2 副作用与清理提示

- 覆盖率命令刷新仓库根 `.coverage`；wheel 构建刷新 `agent_mini.egg-info/`；pytest/import 可能刷新各级 `__pycache__/`。这些路径均被忽略，故 `git status` 仍干净，但属于本次可见副作用。
- `.pytest_cache/`、`.mypy_cache/`、`.ruff_cache/`、`build/` 在评估前已存在或无法仅凭状态区分，本次工具可能复用；未删除，避免误删用户既有产物。
- 仓库外 wheel/target 临时目录：`C:\Users\Ryan\AppData\Local\Temp\agent-mini-s04-audit-8e9355d776f34b07b399d7325e33e364`。自动清理命令被执行策略拦截，目录仍可能存在。
- 如需清理，请人工确认上述精确路径后删除；不要对仓库根执行递归清理命令。

## 10. 修复记录（2026-10-22）

| 报告项 | 修复 | 证据 |
| --- | --- | --- |
| S04-P0-01 独立结果密钥泄露 | observation 统一处理敏感键值、`sk-*`、Bearer 与已知 secret，再截断 | 独立 `token=...`/`sk-*` 用例先红后绿 |
| S04-P1-01 失败→合法链缺失 | 非法参数/未知工具均改为三步：失败调用→合法调用→final，断言 handler 仅合法调用执行 | 两条测试更新 |
| S04-P1-02 执行异常无回归 | executor 抛异常→tool_execution_error 回灌→final | 新增异常测试 |
| S04-P1-03 累计规格冲突 | 新 change MODIFIED S03/AgentResult 条款；主规格 Purpose 改为 S03+S04 | runtime 规格/change |
| S04-P1-04 归档后变更 | 新建 `s04-report-fixes` change，记录归档后测试/证据例外；不改归档目录 | OpenSpec change |
| S04-P1-05 红证据不可复核 | 本轮测试先写；P0 用例 1 failed 红因明确；P1-01/02 为既有实现补回归，首次运行即绿，如实记录 | PROMPT/Issue |
| S04-P2-06 常量/断言 | 统一 `MAX_OBSERVATION_CHARS`；补 usage prompt/completion 与每次 tools 快照断言 | test_react_loop |

**复验**：全量 99 passed；覆盖率 96.17%；unit 35、contract 64；`mypy agent_mini tests` 48 files 0 errors；ruff/format/openspec/wheel 通过。S04 可进入 S05；P2-01/02/03/04/05 保留为后续技术债。
