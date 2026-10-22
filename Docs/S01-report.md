# S01「模型接入：单轮调用」只读评估报告

> 评估日期：2026-10-22  
> 基准提交：`906901c`（`main`，与 `origin/main` 一致）  
> 评估性质：独立只读代码评估；未修复代码、未修改 OpenSpec、未提交、未推送  
> 总体结论：**不建议直接进入 S02**

## 1. 评估范围与基准

### 1.1 实际读取范围

| 类别 | 路径与章节 |
| --- | --- |
| 全局规范 | `AGENT.md` 全文；`openspec/specs/engineering-standards/spec.md`；`openspec/specs/engineering-baseline/spec.md` |
| 阶段计划 | `Docs/PLAN.md` S01、S02、阶段状态与里程碑 DoD |
| 功能需求 | `Docs/REQUIREMENT.md` FR-LLM-01、FR-LLM-02、FR-LLM-04 |
| 设计契约 | `Docs/DESIGN.md` §1.1、§1.3、§3.1、§3.2.4、§4、§6、§7、§8 |
| 测试定义 | `Docs/TESTING.md` TC-L2-001、002、003、007、008、009、010 及准出标准 |
| 过程记录 | `Docs/PROMPT.md` Prompt 21；`Docs/ISSUE.md` ISSUE-017、018、019、020；`MEMORY.md` S01 记录 |
| 实现与测试 | `agent_mini/llm/`；`tests/contract/test_llm_*.py`；S00 单元测试；`pyproject.toml` |
| OpenSpec | `openspec/specs/llm-client/spec.md`；`openspec/changes/archive/2026-10-22-s01-llm-single-turn/` |
| 流程证据 | `git log/show/diff/status`；S01 相关提交 `a0142ca`、`4fef560`、`4f6ad29`、`8ecb5df`、`906901c` |

### 1.2 文档间不一致与缺口

1. `Docs/PLAN.md:62` 将 S01 输出限定为 `llm/client.py`、`llm/models.py`，但实现新增了 `agent_mini/llm/errors.py`；`Docs/PLAN.md:73` 又把该文件列为 S02 输出。`Docs/DESIGN.md:154` 和 ISSUE-020 虽解释为 S01 协议错误最小集合，但阶段计划的“输出”没有同步。
2. `Docs/TESTING.md:133-136` 的 TC-L2-007、009、010 包含 Memory/裁剪、Runtime 回灌、工具执行、trace 和两步循环，超出 S01 单轮客户端范围；PLAN 只对 TC-L2-010 明示“循环部分在 S04 集成”，没有同等清楚地拆分 007/009。
3. 用户指定核对 `Docs/DESIGN.md` §3.1 判别表；实际完整判别表位于 §3.2.4（`Docs/DESIGN.md:249-253`）。§3.1 只有边界摘要，引用锚点存在偏差。
4. `Docs/DESIGN.md:313` 的全局异常体系使用 `AgentError → ConfigError / LLMError ...`，而 S01 的具体异常全部采用 `*Error` 后缀且直接继承 `Exception`。文档没有同步解释这一阶段性差异。
5. `Docs/ISSUE.md:233` 仍记录无 `Error` 后缀的 `LLMEmptyResponse`、`LLMOutputTruncated`、`LLMOutputRejected`，与实现和 Ruff 规则变更后的命名不一致。

## 2. 复核命令与结果

### 2.1 已复跑命令

| 命令 | 关键结果 | 结论 |
| --- | --- | --- |
| `git status --short` | 评估前无输出 | 通过，评估起点干净 |
| `pytest -q` | `36 passed` | 通过 |
| `pytest -q -m unit` | `7 passed, 29 deselected` | 通过 |
| `pytest -q -m contract` | `29 passed, 7 deselected` | 通过 |
| `pytest --cov=agent_mini --cov-report=term-missing` | `36 passed`，总覆盖率 `91.96%` | 测试通过；暴露 `pytest-cov` 未声明问题 |
| `ruff check .` | `All checks passed!` | 通过 |
| `ruff format --check .` | 全部文件已格式化 | 通过 |
| `mypy agent_mini` | `Success: no issues found in 34 source files` | 通过 |
| `openspec validate --all --strict` | `3 passed, 0 failed` | 通过 |
| `pip wheel . --no-deps --wheel-dir <临时目录>` | wheel 构建成功；包含 `agent_mini/llm/*.py` 与 `agent_mini/systemdb/schema.sql` | 通过 |
| 临时 venv 安装 wheel 后仓库外导入 | Python 3.11 与 3.13 均可导入 `agent_mini.llm.client/models/errors` | 通过 |
| `git log/show/diff` | OpenSpec 规划先于实现；归档早于最后的测试 marker 提交 | 部分通过 |
| 定向 Python 探针 | 顶层 JSON 数组触发 `AttributeError`；`params` 可覆盖 `model/thinking`；user 消息可携带 reasoning | 三项缺陷复现 |

### 2.2 未复跑项

| 验收项 | 原因 | 判定 |
| --- | --- | --- |
| `pip install -e .` | 为避免可编辑安装在仓库生成或刷新元数据，采用 wheel + 临时 venv 的更强隔离验证替代 | 不影响打包结论 |
| 真实 DeepSeek API | S01 明确禁止真实调用，且 TC-LIVE-001 留待 S18 | 合理未执行 |
| 429/5xx 重试 | 属 S02，S01 不应实现 | 合理未执行 |
| Runtime/Memory/Tool 闭环 | 属 S04/S06/S13/S16 | 合理未执行，但对应 TC 只能判为部分覆盖 |

### 2.3 关键探针结果

- `HttpLLMClient.chat()` 收到 HTTP 200、JSON 顶层为数组时，`LLMResponse.from_openai()` 在调用 `payload.get` 前没有运行时类型保护，实际抛出 `AttributeError`，没有归一为 `LLMProtocolError`。
- `payload.update(params)` 允许调用方覆盖配置确定的 `model` 和客户端模式确定的 `thinking`。
- `Message(role="user", reasoning_content="...")` 可通过验证；思考模式开启时会把该字段发给供应商，没有限制为 assistant 私有协议字段。

## 3. 维度结论

| 维度 | 结论 | 一句话理由 | 证据位置 |
| --- | --- | --- | --- |
| 11. 需求与范围合规 | 不通过 | 核心单轮能力已实现，但 `errors.py` 与临时 `ModelConfig` 超出 PLAN 明列输出，且计划未同步 | `Docs/PLAN.md:62-73`；`Docs/DESIGN.md:154`；`agent_mini/llm/errors.py`；`agent_mini/llm/models.py:22` |
| 12. 协议契约正确性 | 不通过 | 常规请求与响应归一正确，但非 object 顶层响应泄漏 `AttributeError`，保留参数可被覆盖 | `agent_mini/llm/client.py:54-68`；`agent_mini/llm/models.py:124` |
| 13. tools 参数严格解析 | 通过 | 调用 ID、结构、严格 JSON object、重复键及 NaN 均被校验，未发现 `eval` 或正文猜测 | `agent_mini/llm/models.py:186-247`；`tests/contract/test_llm_tool_arguments.py` |
| 14. 错误边界 | 不通过 | 未提前实现重试，但异常体系未接入 `AgentError`，文档与实现命名不一致，且存在未归一异常 | `agent_mini/llm/errors.py:4`；`Docs/DESIGN.md:313`；`Docs/ISSUE.md:233` |
| 15. 数据模型 | 有条件通过 | reasoning 可保留并再序列化，模型足以支撑后续阶段；但缺角色约束和状态不变量 | `agent_mini/llm/models.py:32-121` |
| 16. 测试质量 | 不通过 | 29 个契约测试有效覆盖 S01 子集，但 007/008/009/010 没有完整兑现 TESTING 原定义，且缺三项关键负例 | `Docs/TESTING.md:133-136`；`tests/contract/test_llm_*.py` |
| 17. 全局规范符合性 | 不通过 | Ruff/mypy/格式均通过；但错误体系、文档同步、魔法默认值与 docstring 完整性仍有违反 | `AGENT.md` §1、§3、§4；`openspec/specs/engineering-standards/spec.md` |
| 18. 打包与分发 | 通过 | wheel 含新增 llm 模块和 schema.sql，隔离环境安装后仓库外导入成功 | `pyproject.toml:25-33`；wheel/venv 复核结果 |
| 19. 依赖审计 | 不通过 | 运行依赖与设计一致、未触碰禁用框架；但验收使用的 `pytest-cov` 未声明，dev 依赖均只有下界 | `pyproject.toml:11-23`；`Docs/DESIGN.md` §1.1、§1.3、§6.1 |
| 20. 流程与文档闭环 | 不通过 | 规划提交先于实现且 OpenSpec 严格校验通过，但归档早于最终测试变更，多处文档仍与代码不一致 | `git log`；`Docs/PLAN.md:62-73`；`README.md`；OpenSpec 主规格 |
| 21. 可复现性 | 有条件通过 | 当前环境和两个临时 Python 环境均可复现；无锁文件且工具只设下界，未来解析结果可能漂移 | `pyproject.toml:11-23`；临时 wheel 安装结果 |
| 22. 隐性风险与后续影响 | 不通过 | 当前接口会把 S01 的异常、消息合法性和保留参数覆盖问题传递到 S02/S04/S13/S16/S18 | `HttpLLMClient.chat`；`Message.to_provider`；异常层次 |

## 4. 问题清单

### P0

#### S01-P0-01：非 object JSON 响应绕过协议错误边界

- **位置**：`agent_mini/llm/client.py:64-68`，`agent_mini/llm/models.py:124-126`，符号 `HttpLLMClient.chat`、`LLMResponse.from_openai`
- **问题描述**：HTTP 200 且 JSON 合法、但顶层为数组、字符串、数字或 null 时，`response.json()` 成功，随后直接调用 `payload.get`；实际可抛 `AttributeError`，不会得到规定的 `LLMProtocolError/LLM_PROTOCOL_ERROR/502`。这会越过统一错误映射，并可能在后续 Runtime/API 层表现为内部错误。
- **判定依据**：`Docs/DESIGN.md:153` 要求非法响应结构抛 `LLMProtocolError`；§3.2.4 判别表要求结构错误归一为协议错误；FR-LLM-04 与 TC-L2-008 要求空/非法响应不得当正常答案。
- **建议修复方向**：在客户端 JSON 解码后或 `from_openai` 入口先验证顶层为 mapping，并把所有非 object 顶层统一转换为 `LLMProtocolError`；增加列表、字符串、数字、null 四类参数化契约测试。

### P1

#### S01-P1-01：任意参数可覆盖受控请求字段

- **位置**：`agent_mini/llm/client.py:54-62`，符号 `HttpLLMClient.chat`
- **问题描述**：`payload.update(params)` 位于 `model/messages/thinking/tools` 组装之后，调用者可通过 `model`、`messages`、`thinking` 或 `tools` 覆盖受配置和类型模型控制的字段，使“默认 thinking.disabled”“配置指定模型”“严格工具 schema”契约失效。
- **判定依据**：`Docs/DESIGN.md:151` 要求默认显式禁用 thinking、模型由配置指定；FR-LLM-01/02 要求协议请求与 tools 透传契约稳定；OpenSpec `llm-client` 请求契约要求受控字段正确。
- **建议修复方向**：明确可透传参数白名单，或在合并前拒绝保留键；为每个保留键添加不得覆盖的契约测试。

#### S01-P1-02：异常层次和命名没有与设计契约闭环

- **位置**：`agent_mini/llm/errors.py:4-37`；`Docs/DESIGN.md:313`；`Docs/ISSUE.md:233`
- **问题描述**：`LLMError` 直接继承 `Exception`，没有接入设计中的 `AgentError`；ISSUE-020 仍使用无 `Error` 后缀名称，而代码采用 `LLMEmptyResponseError` 等名称。后续 S02/S19 统一映射时可能产生迁移和捕获兼容成本。
- **判定依据**：`Docs/DESIGN.md` §3.7 明确异常体系；全局规范要求异常统一继承项目基础异常并具有稳定错误码；文档优先要求设计、Issue 与实现一致。
- **建议修复方向**：先在设计中明确阶段性基类方案和最终名称，再统一实现、OpenSpec、Issue、测试导入及后续阶段接口。

#### S01-P1-03：S01 输出范围与实际新增文件未同步

- **位置**：`Docs/PLAN.md:62-73`；`agent_mini/llm/errors.py`；`agent_mini/llm/models.py:22-29`
- **问题描述**：PLAN 的 S01 输出没有 `errors.py` 或 `ModelConfig`，S02/S21 才声明对应职责；DESIGN 与 ISSUE 做了局部裁决，但权威阶段计划仍保持冲突。
- **判定依据**：`AGENT.md` §1 文档优先、§8 单功能单阶段；用户评估基准要求严格按 PLAN S01 输出判断边界。
- **建议修复方向**：选择并统一一种边界：要么修订 PLAN 明列 S01 所需的最小临时类型及迁移策略，要么把相应实现退回所属阶段；同步 TESTING、DESIGN 和 OpenSpec。

#### S01-P1-04：S01 声明的 TC 未按完整定义覆盖

- **位置**：`Docs/TESTING.md:133-136`；`tests/contract/test_llm_thinking.py`；`test_llm_discrimination.py`；`test_llm_tool_arguments.py`；`test_llm_multi_call.py`
- **问题描述**：TC-L2-007 未覆盖 tools 非空情况下的 reasoning 回传和裁剪后不回传；TC-L2-008 未断言 HTTP 502、工具 handler 次数和无无限重试；TC-L2-009 未覆盖 Runtime 回灌、handler 不执行、trace 恢复；TC-L2-010 未覆盖两步循环、消息配对和 trace。现有测试是合理的 S01 子集，但文档和阶段完成状态没有把“部分覆盖”表达成可机器核对的拆分。
- **判定依据**：`AGENT.md` §1 要求验收标准逐条映射测试；`Docs/TESTING.md` 对上述 TC 的完整定义；`Docs/PLAN.md:64` 将它们列为 S01 测试项。
- **建议修复方向**：将跨阶段 TC 拆成带阶段后缀的子验收项，明确 S01 已覆盖与后续待覆盖部分；不要用同一个 TC 编号的部分断言代表完整通过。

#### S01-P1-05：TDD 红阶段证据不足以证明逐条 TC 的有效失败

- **位置**：`Docs/PROMPT.md` Prompt 21 执行摘要；`openspec/changes/archive/2026-10-22-s01-llm-single-turn/tasks.md`；提交 `4fef560`
- **问题描述**：记录只说明 6 个契约测试模块因缺少类型在“收集阶段失败”，代码和测试又在同一实现提交中，无法从提交历史核验每条 TC 均经历由行为缺失导致的红灯；收集错误也不能证明每项断言真正失败。
- **判定依据**：`AGENT.md` §2 要求逐项“红 → 绿 → 重构”，红因必须与未实现相关且不能是语法/夹具/收集问题。
- **建议修复方向**：后续阶段保留可核验的测试先行提交或逐 TC 红绿日志；红阶段至少进入测试执行并因目标行为缺失失败。

#### S01-P1-06：README 与全局状态文档存在陈旧声明

- **位置**：`README.md` 项目状态段；`MEMORY.md:17`；`agent_mini/llm/__init__.py:1`
- **问题描述**：README/历史状态仍有 S01 尚未开始或只完成 S00 的表述，`llm/__init__.py` 仍称 S01-S02 待落地；与 PLAN/MEMORY 的 S01 已完成状态冲突。
- **判定依据**：`AGENT.md` §1、§3 要求功能完成后同步 README/MEMORY/PROMPT 等事实来源；用户要求检查“代码已改、文档未更新”。
- **建议修复方向**：统一当前阶段状态和 llm 子包说明，保留历史信息时明确标注其时间点，避免把历史快照写成当前事实。

#### S01-P1-07：验收命令依赖 `pytest-cov`，但 dev 依赖未声明

- **位置**：`pyproject.toml:16-23`；覆盖率验收命令记录
- **问题描述**：项目声称并实际运行 `pytest --cov`，但 `dev` extras 没有 `pytest-cov`；在干净环境仅安装 `.[dev]` 时，该验收命令不保证可用，当前通过依赖本机已有包。
- **判定依据**：依赖管理“先声明再使用”；`AGENT.md` §2 的可复现验收要求；`Docs/TESTING.md` 准出标准包含覆盖率。
- **建议修复方向**：声明兼容范围内的 `pytest-cov`，并用仅安装项目 dev extras 的干净环境复验。

#### S01-P1-08：OpenSpec 归档早于最后一项 S01 测试变更

- **位置**：提交顺序 `8ecb5df` → `906901c`；归档 change `2026-10-22-s01-llm-single-turn`
- **问题描述**：S01 change 在 `8ecb5df` 归档后，`906901c` 又修改测试 marker。虽然不改变业务断言，但归档快照不再覆盖最终交付树，削弱“归档前实现与测试已最终稳定”的流程证据。
- **判定依据**：`AGENT.md` §6 的 OpenSpec 归档流程与 §10 提交前检查；归档应在实现、测试和文档全部完成后进行。
- **建议修复方向**：后续严格把归档作为阶段最后的规范动作；若归档后发生阶段内变更，新增 change 或按项目约定补充归档说明。

#### S01-P1-09：私有 reasoning 字段没有角色约束

- **位置**：`agent_mini/llm/models.py:88-110`，符号 `Message`、`Message.to_provider`
- **问题描述**：任意 role 都能设置 `reasoning_content`；thinking 开启时 user/system/tool 消息中的该字段也会发给上游。设计把它定义为历史 assistant 消息的私有协议状态，当前模型允许构造非法或污染协议的消息。
- **判定依据**：`Docs/DESIGN.md:152`、`:211` 规定按供应商协议回传历史 assistant reasoning，且不得作为公开或任意角色字段；TC-L2-007 关注原字段回传语义。
- **建议修复方向**：增加跨字段验证，只允许 assistant 携带 reasoning；增加各 role 的正反例以及序列化断言。

#### S01-P1-10：Ruff 规则配置变化缺少过程记录

- **位置**：`pyproject.toml:54-69`；提交 `4fef560`；`Docs/PROMPT.md` Prompt 21
- **问题描述**：实现提交同时调整了 Ruff 选择/忽略规则，但 Prompt、Issue、设计或独立提交没有清楚说明规则变化的原因与影响，无法判断是否为满足新增代码而放宽。
- **判定依据**：`AGENT.md` §1 文档优先、§4 原子提交和 §11 变更可追溯；OpenSpec 工程规范要求工具配置变更可审计。
- **建议修复方向**：补充规则 diff 的动机和等价性验证；工具链规则变更与功能实现分开提交并单独验收。

### P2

#### S01-P2-01：公共模型大量使用 `Any`，缺少边界说明

- **位置**：`agent_mini/llm/models.py:7,39,43,66,68,124`；`agent_mini/llm/client.py:6,54`
- **问题描述**：JSON 边界使用 `Any` 有现实必要，但公共字段 `ToolCall.arguments`、`ToolSchema.parameters` 和序列化返回值均未通过 JSON 类型别名约束，也没有按全局规范说明原因。
- **判定依据**：OpenSpec 工程规范的类型规则要求避免无说明的 `Any`。
- **建议修复方向**：定义递归 JSON 值类型或在边界处集中封装，并用简短中文说明保留 `Any` 的必要性。

#### S01-P2-02：默认超时为局部魔法数字

- **位置**：`agent_mini/llm/models.py:29`，符号 `ModelConfig.timeout`
- **问题描述**：`60.0` 直接写入临时模型，未引用集中常量或设计中的配置默认值；S21 迁移时容易产生双重默认。
- **判定依据**：全局规范禁止散落魔法数字；S21 负责配置边界。
- **建议修复方向**：使用命名常量并在 S21 迁移时建立唯一配置来源。

#### S01-P2-03：部分 docstring 只复述动作，未说明关键约束

- **位置**：`agent_mini/llm/client.py:37,53,71,75,84`；`agent_mini/llm/models.py:44,69,101,125`
- **问题描述**：文档字符串基本复述函数名，没有记录保留键、严格 JSON、reasoning 角色、资源所有权等容易误用的契约。
- **判定依据**：全局规范要求中文简洁 docstring，但注释应解释意图和约束，不复述代码。
- **建议修复方向**：只在关键公共边界补充短契约说明，删除纯复述式文本。

#### S01-P2-04：同一契约在多个测试文件重复，缺少清晰职责边界

- **位置**：`tests/contract/test_llm_response.py` 与 `test_llm_multi_call.py`
- **问题描述**：多 tool_calls 顺序等断言重复，而更重要的终止原因一致性和负例未覆盖；重复没有形成独立风险分层。
- **判定依据**：测试应独立、聚焦并避免用重复正常例替代边界覆盖。
- **建议修复方向**：将响应归一、判别、循环前置契约按职责拆分，共享 fixture 只承载数据构造，不共享被测逻辑。

#### S01-P2-05：依赖只设下界，存在版本漂移风险

- **位置**：`pyproject.toml:11-23`
- **问题描述**：`httpx`、`pydantic`、`pytest`、`pytest-asyncio`、`respx`、`ruff`、`mypy` 均无上界或锁文件；未来主版本/行为变化会影响请求、Pydantic 验证及工具规则。
- **判定依据**：可复现性和依赖审计要求；设计只给出最低版本，不等同于可重复解析。
- **建议修复方向**：为发布依赖设置兼容上界，为开发/CI 维护锁定结果或约束文件，并定期升级验证。

#### S01-P2-06：数据模型允许相互矛盾的状态

- **位置**：`agent_mini/llm/models.py:32-41,88-121`
- **问题描述**：`ToolCall` 可同时具有 `arguments`、`raw_arguments`、`error_code` 的矛盾组合；`Message` 也可构造与 role 不匹配的 `tool_calls/tool_call_id`。当前解析器通常生成合理对象，但后续 S04 可直接构造非法状态。
- **判定依据**：S04 消息配对和 S13/S16 回传依赖这些公共模型保持不变量。
- **建议修复方向**：在模型层加入跨字段验证，或拆分成功/失败工具调用类型并明确角色消息类型。

#### S01-P2-07：llm 子包说明已过时

- **位置**：`agent_mini/llm/__init__.py:1`
- **问题描述**：模块仍标注“待 S01-S02 落地”，但 S01 已实现。
- **判定依据**：注释和文档必须与当前实现一致。
- **建议修复方向**：更新为当前职责说明，并仅保留 S02 尚未实现的边界。

### Info

#### S01-INFO-01：未发现阶段越界的重试、退避或 HTTP 状态分类

- **位置**：`agent_mini/llm/client.py:62-68`
- **观察**：当前仅依赖 `httpx.raise_for_status()`，没有 S02 的 retry/backoff/jitter，也没有 400/401/429/5xx 细分。
- **依据**：`Docs/PLAN.md:67-76` 将上述能力分配给 S02。
- **建议**：S02 在不改变 S01 归一契约的前提下引入分类与策略，并补齐独立测试。

#### S01-INFO-02：严格工具参数解析实现方向正确

- **位置**：`agent_mini/llm/models.py:186-247`
- **观察**：重复 ID、空 ID、非 function、空名称、非字符串 arguments 均作为协议错误；破损 JSON、数组、字符串、重复键、NaN 归一为 `invalid_arguments` 并保留 call_id；未发现 `eval`、代码块提取或正则猜测 reasoning。
- **依据**：FR-LLM-02；`Docs/DESIGN.md:149-154`；TC-L2-002/008/009。
- **建议**：补充 Infinity、`-Infinity` 和嵌套重复键的显式测试，巩固既有行为。

#### S01-INFO-03：S00 占位测试采用显式名单跳过，而非删除 llm 条目

- **位置**：`tests/unit/test_package_skeleton.py:65-76`
- **观察**：设计子包完整性名单仍保留 llm；已实现模块通过 `NON_PLACEHOLDER_MODULES` 从“仅 docstring”断言中排除，不是删除目录条目。
- **依据**：S00 骨架回归应持续验证目录存在，同时允许阶段模块落地。
- **建议**：后续每个占位模块实现时延续显式迁移方式。

## 5. 需求—实现—测试追溯

### 5.1 FR 追溯

| FR | 实现位置 | 测试位置 | 覆盖结论 | 越界判断 |
| --- | --- | --- | --- | --- |
| FR-LLM-01 | `agent_mini/llm/client.py` 的 `LLMClient`、`HttpLLMClient.chat` | `tests/contract/test_llm_request.py` | 部分覆盖：OpenAI 兼容路径、Header、请求体已测；真实 API 留 S18 | 无真实调用；符合阶段边界 |
| FR-LLM-02 | `ToolSchema.to_provider`、`_parse_tool_calls`、`_parse_arguments` | `test_llm_request.py`、`test_llm_response.py`、`test_llm_discrimination.py`、`test_llm_tool_arguments.py`、`test_llm_multi_call.py` | S01 解析子集覆盖较好；Runtime 执行/回灌/恢复未覆盖 | Runtime 部分留 S04/S06，现实现未越界 |
| FR-LLM-04 | `LLMResponse.from_openai`、`_parse_usage`、`Message.to_provider` | `test_llm_response.py`、`test_llm_thinking.py`、`test_llm_discrimination.py` | 常规字段、空值、截断/过滤覆盖；非 object 顶层缺失 | reasoning 回传已做到客户端层，但角色约束不足 |

### 5.2 TC 追溯

| TC | 实现位置 | 测试位置 | 是否覆盖 | 是否越界 |
| --- | --- | --- | --- | --- |
| TC-L2-001 | `HttpLLMClient.chat`、`ToolSchema.to_provider` | `tests/contract/test_llm_request.py` | 是：路径、鉴权、model/messages/tools/thinking 均断言 | 否；真实 API 留 S18 |
| TC-L2-002 | `LLMResponse.from_openai`、`_parse_tool_calls` | `tests/contract/test_llm_response.py` | 是：单调用 ID/name/arguments/finish_reason | 否 |
| TC-L2-003 | `_parse_usage`、响应模型默认值 | `tests/contract/test_llm_response.py` | 是：文本、空调用、usage 三项 | 否 |
| TC-L2-007 | reasoning 解析、`Message.to_provider`、thinking 请求模式 | `tests/contract/test_llm_thinking.py` | 部分：缺失/null/字符串、默认禁用、手工历史回传；未测 tools 非空和裁剪 | 测试没有从 Memory 读回；裁剪/持久化属于 S13/S16 |
| TC-L2-008 | `from_openai` 的结构与 finish_reason 判别 | `tests/contract/test_llm_discrimination.py` | 部分：主要解析分支已测；未测 HTTP 502、handler=0、无重试和顶层非 object | 429/5xx 重试断言未出现，符合 S01/S02 边界 |
| TC-L2-009 | `_parse_arguments`、`ToolCall.error_code` | `tests/contract/test_llm_tool_arguments.py` | 部分：破损/非 object/重复键/NaN 和后续合法解析；未测 Runtime 回灌、handler、trace | Runtime/Tool 部分留 S04/S06；当前没有越界实现 |
| TC-L2-010 | content 与多调用并存、列表顺序 | `tests/contract/test_llm_multi_call.py`、`test_llm_response.py` | 部分：只覆盖第一步归一；未覆盖第二步循环、消息配对、trace | PLAN 明确循环部分在 S04；当前没有越界实现 |

## 6. 边界抽查结论

1. **是否存在越界实现重试/退避/状态分类：否。** `HttpLLMClient.chat` 只发送一次请求并调用 `raise_for_status()`；未发现重试次数、退避、抖动或 400/401/429/5xx 分类。
2. **是否存在 TC-L2-007 越界到 S13（从 Memory 读回 reasoning）：否。** 测试在本地列表中手工追加 assistant 消息，再调用客户端；没有访问 Memory、Redis、Mongo 或上下文裁剪器。但“后续轮次”表象容易被误读，应标明仅验证序列化契约。
3. **TC-L2-008 是否包含 429/5xx 重试断言：否。** 该文件只调用 `LLMResponse.from_openai`，没有 HTTP 请求或重试次数断言。
4. **S00 占位测试如何处理已实现 llm 模块：显式跳过占位断言，不是删除条目。** `tests/unit/test_package_skeleton.py` 仍保留设计目录清单，并通过 `NON_PLACEHOLDER_MODULES` 排除已实现文件。
5. **`*Error` 后缀是否同步到 DESIGN §3.7 并与 Ruff 规则变更记录一致：否。** 实现已使用后缀，但 DESIGN 只列宽泛异常体系，ISSUE-020 仍使用旧名；Prompt 也没有解释同一实现提交中的 Ruff 规则变化。

## 7. 技术债与后续阶段影响

| 后续阶段 | 技术债/风险 | 触发条件 | 建议处理时机 |
| --- | --- | --- | --- |
| S02 | 非 object JSON 泄漏 `AttributeError`，异常基类未统一 | 开始做 HTTP 状态分类和统一错误映射 | S02 开工前先修复 P0-01，并确定异常层次/名称 |
| S02 | `**params` 可覆盖 model/thinking/tools | S02 增加 retry、timeout 或供应商参数透传 | 在扩展参数表面前建立白名单/保留键策略 |
| S04 | `ToolCall`、`Message` 可构造矛盾状态 | Runtime 开始配对 assistant/tool 消息并执行多个调用 | S04 数据流设计前加入跨字段不变量 |
| S04 | TC-L2-009/010 当前只完成解析子集 | Runtime 将非法参数映射为 ToolResult、形成两步循环 | S04 明确接管剩余断言并保留原 TC 追溯 |
| S13/S16 | reasoning 未限制 assistant role | Memory 恢复任意消息或裁剪后重新序列化 | S13 持久化模型确定前修复；S16 增加裁剪后不回传测试 |
| S13/S16 | 客户端接受调用方已组装的历史，但没有完整轮次语义 | 从存储恢复不完整 assistant/tool 配对 | 在 Memory/裁剪边界建立“完整轮次”类型或验证器 |
| S18 | 请求保留字段可被覆盖，真实服务可能拒绝非法 reasoning | 启用真实 DeepSeek API 或外部调用方传入 params | S18 live 验收前完成保留键与角色负例测试 |
| S18 | 无依赖锁定，httpx/pydantic 行为可能漂移 | CI 或部署重新解析较新版本 | 在进入真实 API 验收前建立约束/锁定策略 |

## 8. 总体结论

### 8.1 是否可进入 S02

**不建议直接进入 S02。** S01 的主路径和严格工具参数解析已经成形，所有现有测试、静态检查、OpenSpec 校验与打包验证均通过；但协议错误边界存在一个 P0，且阶段范围、异常体系、测试完整性、依赖声明与文档闭环存在多项 P1。直接进入 S02 会把错误基类和参数覆盖问题固化进重试/分类层。

### 8.2 进入 S02 前必须处理

1. S01-P0-01：所有合法 JSON 的非法顶层结构必须归一为 `LLMProtocolError`。
2. S01-P1-01：禁止 `**params` 覆盖 `model/messages/thinking/tools` 等受控字段。
3. S01-P1-02：统一异常基类、具体类型名称和设计/Issue/OpenSpec 表述。
4. S01-P1-03：同步 PLAN 的 S01/S02/S21 输出边界。
5. S01-P1-04：将跨阶段 TC 拆分为可追溯的阶段子断言，不能把部分覆盖标记为整条通过。
6. S01-P1-05：建立可核验的逐 TC TDD 红绿证据规则；本阶段至少如实修正文档声明。
7. S01-P1-06：清理 README、MEMORY 历史表述和 llm 包说明中的当前状态冲突。
8. S01-P1-07：声明 `pytest-cov`，保证准出命令能由项目依赖复现。
9. S01-P1-08：明确归档后测试变更的处理规则，保证最终树与 OpenSpec 归档一致。
10. S01-P1-09：把 `reasoning_content` 限制为 assistant 私有协议字段。
11. S01-P1-10：补齐 Ruff 配置变更的原因、影响和验证记录。

### 8.3 可选改进

- 用 JSON 值类型别名收紧公共模型边界。
- 将 60 秒默认超时迁移到单一配置来源。
- 减少重复正常路径测试，增加非法顶层、Infinity、角色/字段组合等负例。
- 为运行与开发依赖建立兼容上界及可重复的约束文件。

## 9. 工作区状态与副作用

### 9.1 状态对比

- 评估开始前：`git status --short` 无输出。
- 只读评估完成后：被跟踪文件无变化。
- 本报告归档动作会新增 `Docs/S01-report.md`，并按用户要求修改 `AGENT.md`；依照 `AGENT.md` 自身规则同步追加 `Docs/PROMPT.md`。这些是报告归档变更，不是 S01 实现修复。

### 9.2 评估过程产生的副作用

- `pip wheel` 刷新了仓库内被 `.gitignore` 忽略的 `agent_mini.egg-info/` 元数据；因此 `git status --short` 不显示，但文件时间可能变化。若需彻底还原，建议人工确认后删除该目录，勿在自动评估中执行清理。
- 仓库外临时目录：
  - `C:\Users\Ryan\AppData\Local\Temp\agent-mini-wheel-eval-2db6d56001c94360806d7df95d8be84a`
  - `C:\Users\Ryan\AppData\Local\Temp\agent-mini-mypy-2af3e4b7054b4b5c97449098f06308e0`
  - `C:\Users\Ryan\AppData\Local\Temp\agent-mini-coverage-f1f8da5f4e7d4fd59a9ae11f30301bdb`
- 上述临时目录位于仓库外，可由人工在确认不再需要复核证据后清理。

