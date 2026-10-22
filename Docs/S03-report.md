# S03「Runtime：单轮直答」产出评估报告

> 评估日期：2026-10-22
> 基准提交：`31f2221`（`main`，与 `origin/main` 一致）
> 评估性质：独立只读代码评估；除本报告与 Prompt 记录外，不修改实现、测试、Issue、PLAN 或 OpenSpec
> 总体结论：**不通过；处理 P1 后方可进入 S04**（后续修复见 §10；修复后 S03 可进入 S04）

## 1. 评估范围与基准

### 1.1 实际读取内容

| 类别 | 路径与章节 |
| --- | --- |
| 全局规范 | `AGENT.md` 全文；`openspec/specs/engineering-standards/spec.md` 的测试、错误、命名、依赖与日志条款 |
| 阶段范围 | `Docs/PLAN.md` S02、S03、S04、DoD 与进度记录 |
| 功能需求 | `Docs/REQUIREMENT.md` FR-RT-01、UC-01、AC-01，并抽查 NFR-MAINT-02、NFR-TEST-01 |
| 设计契约 | `Docs/DESIGN.md` §1、§2.2、§3.1、§3.2、§3.7、§4、§5.1、§6–§8、§10 |
| 测试定义 | `Docs/TESTING.md` TDD 规则、TC-L1-015/015A/015B/015C、S03 覆盖边界、准入与准出标准 |
| 过程记录 | `Docs/PROMPT.md` Prompt 31/32；`Docs/ISSUE.md` ISSUE-024/025/027/028 与 S03 记录；`MEMORY.md`、`README.md` |
| 实现与测试 | `agent_mini/runtime/agent.py`、`result.py`、`__init__.py`；`tests/unit/test_agent.py`、`test_package_skeleton.py`；相关 LLM 协议模型与错误类型 |
| OpenSpec | `openspec/specs/runtime/spec.md`；归档 change `2026-10-22-s03-runtime-direct-reply` 的 proposal/design/tasks/spec |
| 流程证据 | 提交 `5b131b8`、`dda1a10`、`111439b`、`13fa639`、`31f2221` 及 S03 前后树 |

### 1.2 基准间的一致性与缺口

1. PLAN、DESIGN §3.2.0、OpenSpec runtime 主规格和实现对核心成功路径基本一致：构造器注入 `LLMClient`，发送一条 user 消息，不传 tools，一步返回 `reply/steps/usage`。
2. `Docs/REQUIREMENT.md` FR-RT-01 仍映射 TC-L1-015/TC-L4-003，没有映射为解决 S03 阻塞而新增的 TC-L1-015A/B/C；需求—阶段测试链未闭合。
3. `Docs/TESTING.md` 顶部仍声明 v0.6、待评审、75 个用例和“当前无测试代码、均未执行”，与 S03 已有 79 个 pytest 用例、L1 新增三个唯一 TC ID 的事实冲突。
4. DESIGN §3.2 已采用 `reply`，但 §5.1 仍写 `AgentResult(final, trace)`；这与用户确认的“reply，不用 final”及当前模型字段直接冲突。
5. OpenSpec runtime 主规格覆盖成功、字段和异常透传，但没有记录实现已加入的“意外 tool_calls → `LLMProtocolError`”与“客户端返回无 content → `LLMEmptyResponseError`”防御契约。

## 2. 复核命令与结果

| 命令/检查 | 关键结果 | 结论 |
| --- | --- | --- |
| `git status -sb` | `main...origin/main`，无工作区变更 | 通过 |
| `python -m pytest -q -p no:cacheprovider -m unit` | 15 passed、64 deselected，0.23s | 通过；低于 L1 5s 目标 |
| `python -m pytest -q -p no:cacheprovider -m contract` | 64 passed、15 deselected，46.73s | 通过；低于 L2 60s 目标 |
| `python -m pytest -q -p no:cacheprovider` | 79 passed，46.92s | 通过 |
| 覆盖率门禁 | 总覆盖率 95.97%；runtime `agent.py`/`result.py` 均 100% | 通过 |
| `ruff check .` | All checks passed | 通过 |
| `ruff format --check .` | 50 files already formatted | 通过 |
| `mypy agent_mini tests` | 47 个源文件无错误 | 通过 |
| `openspec validate --all --strict` | 4 passed、0 failed | 结构校验通过 |
| `python -m pip check` | No broken requirements found | 通过 |
| wheel 构建、临时 target 安装与仓库外导入 | 成功导入 `Agent`、`AgentResult`；`schema.sql=True` | 通过 |
| wheel 内容抽查 | `agent_mini/` 35 个文件；四个 runtime 文件与 `schema.sql` 均存在 | 通过 |
| TDD 红灯重建 | 基线 `111439b^` 叠加当前 `test_agent.py`：7 failed | 通过；均进入执行阶段，红因是 Agent 行为尚不存在 |
| 空内容定向探针 | `content=""` 与纯空白均返回成功 `AgentResult` | 不符合非空文本契约 |
| AgentResult 边界探针 | `steps=-1` 被接受；额外 `trace` 被静默忽略；嵌套 usage 可修改 | 存在模型不变量技术债 |
| 禁止依赖/危险调用扫描 | runtime 与依赖声明中未发现禁用 Agent 框架、`eval/exec`、阻塞 sleep、noqa/type-ignore | 通过 |

### 2.1 未复跑项目

- 未调用真实 DeepSeek API：S03 使用注入替身完成单元验收；正式真实 API 与 HTTP 全链路按计划留 S18。
- 未执行 `pip install -e .`：可编辑安装会写回仓库元数据；本次改用仓库外源码归档、wheel 构建、临时 target 安装与导入验证，且 S03 未修改依赖声明。
- 未执行 L3–L5：这些层级不属于 PLAN S03 测试项，相关阶段尚未开始。

## 3. 维度结论

| 维度 | 结论 | 理由与证据 |
| --- | --- | --- |
| 需求与阶段范围 | 有条件通过 | 实现严格落在 Runtime 单轮直答，无工具/Memory/HTTP 越界；FR-RT-01 未映射新增 S03 TC |
| 单轮直答正确性 | 不通过 | 正常文本一步返回正确，但空字符串和纯空白可作为成功 reply 返回 |
| LLM 调用契约 | 通过 | 恰好一条 user 消息、一次 `chat`、tools 为 None；没有 Runtime 级重试 |
| 错误边界 | 有条件通过 | LLM 异常实例原样传播，tool_calls 被拒绝；Runtime 自身未完整拒绝所有空答案 |
| AgentResult 数据模型 | 有条件通过 | 顶层冻结且字段集合正确；reply/steps/extra 与嵌套 usage 不变量较弱 |
| 测试质量与 TDD | 有条件通过 | 7 个红灯可重建、现有用例全绿且新代码 100%；缺空白内容和混合 content+tool_calls 回归 |
| 全局代码规范 | 通过 | Ruff、格式、严格 mypy 通过；函数短、嵌套浅、中文 docstring，无禁用注释或魔法步骤数 |
| 安全与隐私 | 通过 | reply 不混入 reasoning，未读取密钥、未记录响应正文、未引入危险执行能力 |
| 打包与依赖 | 通过 | 无新增依赖；wheel 35/35，runtime 与 package-data 完整，仓库外导入成功 |
| OpenSpec 与流程 | 有条件通过 | 文档/change 先于实现、归档最后、strict 通过；Prompt/Issue 记录不满足全局格式要求 |
| 文档闭环 | 不通过 | REQUIREMENT、TESTING 元数据与 DESIGN §5.1 均存在可核对的不一致 |
| 可复现性与性能 | 通过 | 79 tests、覆盖率、静态门禁、wheel 均可复现；unit 0.23s |

## 4. 问题清单

### P0

无。

### P1

#### S03-P1-01：空字符串与纯空白被当作成功直答

- **位置**：`agent_mini/runtime/agent.py:18-28`，符号 `Agent.run`；`tests/unit/test_agent.py:144-149`。
- **问题描述**：Runtime 只判断 `response.content is None`。定向探针表明 `""` 和 `"   "` 均会返回 `AgentResult`，形成空成功响应。虽然 `HttpLLMClient` 的标准解析路径会拒绝空白，但 S03 明确通过 Protocol 支持构造器注入，其他合法实现或替身可直接返回可构造的 `LLMResponse`，Runtime 不能依赖某个具体客户端的私有不变量。
- **判定依据**：`openspec/specs/runtime/spec.md:15-16` 要求无 tool_calls 的**非空文本**才成功；`Docs/DESIGN.md:172-184` 要求 content 非空，否则抛 `LLMEmptyResponseError`；FR-RT-01 不允许空回复伪成功。
- **建议方向**：在 Runtime 边界统一拒绝 None、空字符串和纯空白，并增加参数化回归；保留原始非空文本，不擅自改写模型内容。

#### S03-P1-02：FR-RT-01 与新增 S03 测试没有形成正式追溯

- **位置**：`Docs/REQUIREMENT.md:175-186`，FR-RT-01；`Docs/PLAN.md:81-91`；`Docs/TESTING.md:108-111,163-169`。
- **问题描述**：PLAN 和 TESTING 已把 S03 验收拆为 TC-L1-015A/B/C，但上位需求 FR-RT-01 仍只指向属于 S04 工具循环的 TC-L1-015 和未来 S18 的 TC-L4-003。ISSUE-028 所解决的阻塞在需求层仍存在。
- **判定依据**：`AGENT.md` §1、§7 要求每条验收标准映射测试，需求变更按需求→设计→测试→实现回溯；无 TC 映射的需求不得视为完成。
- **建议方向**：把 FR-RT-01 的 S03 验收映射补为 TC-L1-015A/B/C，并明确 TC-L1-015 与 TC-L4-003 分别由 S04/S18 接管；同步需求版本和变更记录。

#### S03-P1-03：TESTING 状态、数量和执行声明与仓库事实冲突

- **位置**：`Docs/TESTING.md:7-14,84-86,108-111`。
- **问题描述**：文档顶部仍称 v0.6、待评审、L1×30/总计 75，并声明“当前无测试代码；75 个用例均未执行”。同一文件后部却声明 S03 已实现，仓库实际有 79 个 pytest 用例；新增 015A/B/C 也是三个唯一测试 ID，未计入 L1 与总数。
- **判定依据**：`AGENT.md` 文档优先和阶段收口五件套；TESTING 准出要求文档与实现一致；虚假的执行状态会误导后续阶段准入与覆盖统计。
- **建议方向**：更新版本、日期、评审/执行状态和用例计数；将“均未执行”改为按阶段列出已实现/未实现范围，避免把 pytest 函数数量与设计 TC 数量混为一谈。

#### S03-P1-04：DESIGN 仍保留被用户否决的 `final` 字段

- **位置**：`Docs/DESIGN.md:404-415`，§5.1 单轮直答；关联 §3.2.0 与 Prompt 32。
- **问题描述**：用户已明确 `AgentResult` 使用 `reply` 而非 `final`，Prompt 32 也声明伪代码已同步；但单轮数据流仍写 `AgentResult(final, trace)`。该表述还在 S03 结果中提前放入 trace，与当前模型及阶段边界冲突。
- **判定依据**：用户方向 A 决策；`Docs/DESIGN.md:174-184`；PLAN S03；OpenSpec runtime 的仅 reply/steps/usage 契约；`AGENT.md` 禁止文档与实现长期不一致。
- **建议方向**：把 §5.1 的阶段数据流改为 S03 当前字段，并用明确注释标出 session/trace/Memory/HTTP 为后续阶段；同时复核同节调用链的阶段标签。

#### S03-P1-05：Prompt 与 Issue 过程记录未满足全局必填格式

- **位置**：`Docs/PROMPT.md:1023-1058`，Prompt 31/32；`Docs/ISSUE.md:325-344`，ISSUE-028。
- **问题描述**：Prompt 31 只用一句引述概括长 Prompt，Prompt 32 明示为“原始 Prompt（要点）”，均非逐字原文；ISSUE-028 缺少全局规范要求的“根因、解决方案、验证方式、验证结果”完整字段，仍直接标记 Resolved。
- **判定依据**：`AGENT.md` §3 要求每次 AI 交互逐字保留原始 Prompt；§4 要求每条 Issue 包含固定字段，Resolved 必须有可复现验证步骤。
- **建议方向**：能从聊天记录恢复时补录完整原文；不能恢复时如实标注历史证据缺失，不得伪造。按 ISSUE 模板补齐根因、方案与可复验命令，再保持或调整状态。

### P2

#### S03-P2-01：AgentResult 未约束基础不变量且静默忽略额外字段

- **位置**：`agent_mini/runtime/result.py:8-15`，符号 `AgentResult`。
- **问题描述**：模型接受空 reply、负数 steps，并按 Pydantic 默认行为静默忽略额外字段。定向探针中 `steps=-1` 成功，传入 trace 不报错却被丢弃；这会掩盖 S04 扩展时的字段拼写或版本不匹配。
- **判定依据**：DESIGN 规定 S03 steps 固定为 1、reply 为最终文本；外部/跨层数据模型应在边界拒绝矛盾状态。
- **建议方向**：对 reply/steps 建立最小约束，并考虑 `extra="forbid"`；若 S04 需要新增字段，应以显式模型变更完成，而不是依赖额外字段静默丢弃。

#### S03-P2-02：关键边界测试不足且动态 Any 降低类型门禁价值

- **位置**：`tests/unit/test_agent.py:50-53,60-149`。
- **问题描述**：空响应测试只覆盖 None，不覆盖空字符串/纯空白；意外工具测试只覆盖 content=None，没有覆盖 S01 已支持的 content+tool_calls 混合响应。`_agent_class() -> Any` 让 Agent 构造与调用退出严格 mypy 检查，适合红灯阶段但在绿后继续削弱测试静态约束。
- **判定依据**：TESTING 要求边界与错误路径有效覆盖，S01/S04 设计明确存在混合 content+tool_calls；S03 起 `mypy agent_mini tests` 是正式门禁。
- **建议方向**：增加空内容参数化和混合响应回归；绿灯后直接导入强类型 Agent，或用仅在红灯重建脚本中的动态加载方式保留历史证据。

#### S03-P2-03：Runtime 主规格没有覆盖已实现的防御分支

- **位置**：`openspec/specs/runtime/spec.md:9-44`；`agent_mini/runtime/agent.py:21-24`。
- **问题描述**：主规格只定义正常直答、字段和客户端异常透传，没有定义 Runtime 收到意外 tool_calls 或自行发现无 content 时的异常类型；这些行为仅存在于 DESIGN、归档 design、实现和测试中。
- **判定依据**：OpenSpec 主规格应描述归档后仍生效的外部行为；AGENT 要求验收标准与测试一一对应。
- **建议方向**：补充防御分支 Requirement/Scenario，明确 tool_calls 优先于 content 判定，以及空字符串/纯空白的处理。

#### S03-P2-04：DESIGN 调用链存在重复步骤与阶段标签混排

- **位置**：`Docs/DESIGN.md:186-205`，§3.2.1。
- **问题描述**：调用链同时列出 “0/1” 的 S13/S07 占位和重复的 “1/2” SystemDB/Context 步骤，随后直接进入完整 ReAct/Memory/HTTP 流程；S03 当前路径与未来总链路没有清晰分层。
- **判定依据**：全局注释与文档应准确、不重复代码或形成歧义；S03 非目标必须显式。
- **建议方向**：拆成“S03 当前链路”和“最终目标链路”，或统一编号并在每一步标出首次落地阶段。

### Info

#### S03-INFO-01：TDD 红灯证据有效

- 在仓库外以 `111439b^` 的实现叠加当前 `test_agent.py`，7 个测试全部进入执行阶段并因 Agent 尚未实现而失败；不是收集、语法或夹具错误。实现与测试同在 `111439b`，符合项目同提交规则。

#### S03-INFO-02：冻结模型是浅冻结

- 归档 design 已明确记录 `Usage` 仍可变的权衡。探针证实可通过 `result.usage.total_tokens = ...` 改变嵌套对象；S03 自身不修改 usage，暂不判缺陷。S04/S18 若把 AgentResult 当不可变跨层对象，应决定复制或冻结 Usage。

#### S03-INFO-03：未发现范围蔓延或依赖变化

- `runtime/loop.py` 仍为占位；未实现工具注册/执行、安全阀、Memory、Context、HTTP、日志或配置容器；`pyproject.toml` 无 S03 依赖变化，也没有禁用 Agent 框架。

## 5. 需求—实现—测试追溯

| 需求/TC | 实现位置 | 测试位置 | 覆盖结论 | 越界情况 |
| --- | --- | --- | --- | --- |
| FR-RT-01 | `Agent.run`、`AgentResult` | `tests/unit/test_agent.py` | 行为大体覆盖；REQUIREMENT 未映射 A/B/C，空白回复未覆盖 | 无 |
| AC-01 | `Agent.run` 一步返回、tools=None | `test_direct_reply_returns_one_step_result` | S03 单元子集已覆盖；正式 AC 仍由 S18 TC-L4-003 完成 | 无真实 HTTP |
| TC-L1-015A | 单条 user 消息、一次 chat、一步结果、usage 透传 | 直答、冻结、签名三个测试 | 正常路径覆盖；空字符串/纯空白缺失 | 无工具路径 |
| TC-L1-015B | LLM 异常自然传播；Runtime 对 None 防御 | 空响应传播、None 响应测试 | 同一客户端异常实例已覆盖；Runtime 空白判断不完整 | HTTP 映射留 S18 |
| TC-L1-015C | 不捕获/包装 `LLMTimeoutError` | 超时异常传播测试 | 类型、实例、调用次数均覆盖 | 安全阀留 S05，真实超时留 S18 |
| TC-L1-015 | 未实现 | 无 S03 实现 | 正确留 S04 | 工具循环未越界 |

## 6. 边界抽查

- **是否只调用模型一次：是。** `Agent.run` 只有一次 `chat`；异常不做 Runtime 重试。
- **是否只发送单条 user 消息：是。** 测试断言消息数量、role 与 content。
- **是否不传 tools：是。** 调用省略 tools，替身观察到 None。
- **是否实现 S04 工具循环或执行工具：否。** 意外 tool_calls 直接抛协议错误，`runtime/loop.py` 保持占位。
- **是否实现 S05 安全阀：否。** 无 max_steps、deadline、重复调用逻辑。
- **是否越界到 S07/S13 Memory/Context/session_id：否。** run 签名只有 user_input。
- **是否越界到 S18 HTTP/真实 API：否。** 无 Interface 调用，本次也未调用真实 API。
- **是否泄露 reasoning：未发现。** reply 直接取 content，结果模型没有 reasoning/trace 字段。
- **是否新增依赖或 Agent 框架：否。** S03 diff 未改 pyproject，机械扫描无命中。

## 7. 技术债与后续阶段影响

| 后续阶段 | 风险 | 触发条件 | 建议处理时机 |
| --- | --- | --- | --- |
| S04 | 空白 reply 被视为正常收敛，工具循环可能提前返回空答案 | S04 复用 `Agent.run` 判定最终分支 | 进入 S04 前修复 S03-P1-01 |
| S04 | 混合 content+tool_calls 未由 S03 回归锁定 | S04 开始支持伴随文本与工具优先级 | S04 开工前补边界测试 |
| S04/S05 | AgentResult 不变量弱，新增 trace/truncated 拼写错误可能被静默忽略 | 扩展结果模型 | S04 模型扩展时启用显式约束与 extra 策略 |
| S13 | run 签名将增加 session_id，现有调用方会发生接口变化 | Memory/会话落地 | S13 通过新 OpenSpec change 迁移并保留类型测试 |
| S18 | REQUIREMENT/TESTING/DESIGN 字段不一致会传导到 HTTP 响应 | TC-L4-003 与接口模型落地 | S04 前先完成文档闭环，S18 再核对公开 Schema |
| S18/S20 | LLMError 临时根与 HTTP 映射尚未统一 | HTTP 错误响应和 AgentError 落地 | 按 ISSUE-024 计划处理 |

## 8. 总体结论

S03 的最小结构和正常路径实现简洁，范围控制、依赖注入、异常原样传播、冻结结果、TDD 红灯、覆盖率、静态检查、OpenSpec 归档与 wheel 均有可靠证据；但 Runtime 仍可返回空白成功结果，且需求追溯、TESTING 当前状态、DESIGN 单轮数据流和 Prompt/Issue 记录未完成闭环。

**结论：暂不建议进入 S04。**

进入 S04 前必须处理：

1. S03-P1-01：拒绝空字符串与纯空白模型回复，并补回归测试。
2. S03-P1-02：把 FR-RT-01 正式映射到 TC-L1-015A/B/C，明确后续 TC 边界。
3. S03-P1-03：修正 TESTING 版本、状态、数量与“均未执行”声明。
4. S03-P1-04：将 DESIGN §5.1 的 `final/trace` 修正为 S03 当前契约并标注后续字段。
5. S03-P1-05：补齐或如实标注 Prompt 原文证据，并按模板完善 ISSUE-028 的解决与验证字段。

P2 可在同一修复 change 中处理，也可登记后由 S04 承接；其中 AgentResult 约束与混合响应测试建议在扩展模型前完成。

## 9. 工作区状态与副作用

### 9.1 状态

- 评估开始前与复核命令结束后，`git status --short` 均无输出；`git status -sb` 为 `main...origin/main`，无 ahead/behind。
- 按 `AGENT.md` 归档规则，本次新增 `Docs/S03-report.md` 并向 `Docs/PROMPT.md` 追加本轮记录；未修改实现、测试、Issue、PLAN、OpenSpec 或远程状态。

### 9.2 副作用

- pytest 使用 `-p no:cacheprovider` 且设置 `PYTHONDONTWRITEBYTECODE=1`；coverage 数据写入仓库外 TEMP，仓库内没有可见测试产物。
- 仓库外 TDD 红灯重建：`C:\Users\Ryan\AppData\Local\Temp\agent-mini-s03-red-fd0e91a810e8491eaa8fd5fd1c627a36` 及同名 `.zip`。
- 仓库外 wheel/安装验证：`C:\Users\Ryan\AppData\Local\Temp\agent-mini-s03-wheel-6b277a82f4944585b52fde40d1611da9`。
- 仓库外 coverage 文件：`C:\Users\Ryan\AppData\Local\Temp\agent-mini-s03-coverage`。
- 上述 TEMP 产物未自动删除；如需清理，请人工确认路径后删除。

## 10. 修复记录（2026-10-22）

| 报告项 | 修复 | 证据 |
| --- | --- | --- |
| S03-P1-01 空白 reply 成功 | `Agent.run` 拒绝 None、空字符串、纯空白；`AgentResult.reply` 非空校验 | 3 个空白参数化用例先红后绿 |
| S03-P1-02 FR-RT-01 未映射 015A/B/C | REQUIREMENT v0.8 更新 FR-RT-01/AC-01，明确 S04/S18 边界 | REQUIREMENT 追溯表 |
| S03-P1-03 TESTING 状态陈旧 | v0.7、执行中、设计 78 / 自动化 82，删除“均未执行” | TESTING 顶部与 4.2.3 |
| S03-P1-04 DESIGN §5.1 final/trace | §5.1 改为 `AgentResult(reply, steps, usage)`；§3.2.1 拆分 S03/最终链路 | DESIGN v0.13 |
| S03-P1-05 Prompt/Issue 格式 | Prompt 31/32 逐字原文与模板字段；ISSUE-028 补根因/方案/验证/提交 | PROMPT、ISSUE |
| S03-P2-01 结果不变量 | `reply` 非空非空白、`steps≥1`、`extra=forbid` | 5 个非法模型用例 |
| S03-P2-02 边界/Any 测试 | 补混合 content+tool_calls；绿后直接导入 `Agent`/`AgentResult` | test_agent.py |
| S03-P2-03 规格防御分支 | runtime 主规格补空内容、意外 tool_calls、结果不变量场景 | openspec runtime spec |
| S03-P2-04 调用链混排 | DESIGN §3.2.1 分为 S03 当前链路与最终目标链路 | DESIGN v0.13 |

**复验**：全量 88 passed；覆盖率 96.03%；unit 24、contract 64；`mypy agent_mini tests` 47 files 0 errors；ruff/format/openspec 通过。S03 可进入 S04。
