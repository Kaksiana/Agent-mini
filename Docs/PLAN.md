# PLAN <!-- omit in toc -->

> **Agent-mini 执行计划**。规则见 `AGENT.md` §8（阶段执行粒度）与 §7（需求驱动开发）。
> 上位文档：`Docs/REQUIREMENT.md`、`Docs/DESIGN.md`、`Docs/TESTING.md`。

| 项目 | 内容 |
| --- | --- |
| 版本 | v0.6（解析契约、Schema 预算与验收补充） |
| 日期 | 2026-10-21 |
| 阶段总数 | 22（S00–S21） |
| 里程碑 | 4（M1–M4） |

---

## 1. 阶段划分原则

1. **单功能单阶段**：一个阶段只交付**一个**可独立验收的功能，不做"顺手带上"。
2. **可独立验收**：每个阶段结束时，必须能用该阶段新增的测试用例证明功能可用，且全量测试不回归。
3. **禁止跨功能并行**：同一时间只允许推进一个阶段；未达验收标准不得开启下一阶段。
4. **依赖单向**：阶段只依赖更早的阶段（例外必须显式标注并说明原因）。
5. **测试先行**：阶段开始即写该阶段用例（红），实现到绿，再重构。
6. **阶段收口**：每阶段结束必须完成——文档同步、`Docs/PROMPT.md` 记录、`Docs/ISSUE.md` 更新、测试全绿、推送。
7. **粒度控制**：单阶段工作量控制在 1–3 人日；超出则继续拆分，拆分依据是**独立验收单元**而非文件数。
8. **顺序服从需求**：阶段的模块顺序严格遵循 `Docs/REQUIREMENT.md` §4 的八层开发顺序。

## 2. 模块分层与阶段映射

| 需求层 | 阶段 | 阶段数 |
| --- | --- | --- |
| 工程基线（前置） | S00 | 1 |
| 1. 模型接入层 | S01–S02 | 2 |
| 2. Agent Runtime | S03–S05 | 3 |
| 3. Tool 能力层 | S06–S12 | 7 |
| 4. Memory 记忆 | S13–S14 | 2 |
| 5. Context 管线、压缩策略 | S15–S16 | 2 |
| 支撑组件：系统数据库（MySQL） | S17 | 1 |
| 6. 交互接口层 | S18 | 1 |
| 7. 可观测与治理 | S19–S20 | 2 |
| 8. 配置与依赖注入 | S21 | 1 |

---

## 3. 阶段详细计划

### S00 — 工程基线

- **模块**：工程基线
- **对应需求**：NFR-TEST-01（支撑所有 FR 的工程前置）。
- **目标**：建立可安装、可测试、可静态检查的包骨架，后续所有阶段都在此之上增量开发。
- **输入**：现有仓库（文档已就绪）。
- **输出**：`pyproject.toml`、`agent_mini/` 包结构、`tests/` 目录、pytest/ruff 配置、`README.md` 中的测试命令。
- **验收标准**：`pip install -e .` 成功；`pytest` 通过 S00 smoke/结构/打包测试（7 个）；`ruff check` 零告警；wheel 构建成功且 `agent_mini/` 35/35 文件（含 `schema.sql`）进入 wheel。
- **测试项**：TC-SMOKE-001（新增：导入包并运行版本查询）。
- **前置阶段**：无。

### S01 — 模型接入：单轮调用

- **模块**：模型接入层
- **对应需求**：FR-LLM-01、FR-LLM-02、FR-LLM-04。
- **目标**：用 OpenAI Chat Completions 协议完成一次真实可替换的单轮调用，并解析文本响应。
- **输入**：`ModelConfig`（base_url、model、超时；S01 临时位于 `llm/models.py`，S21 迁移）。
- **输出**：`llm/client.py`、`llm/models.py`（含可选 reasoning_content 的 LLMResponse）、`llm/errors.py`（仅 S01 判别错误）；tools 参数 JSON 严格解析与响应判别规则。
- **验收标准**：文本、reasoning、tools 分开归一；非法响应、空/截断输出明确错误；工具 ID 唯一，JSON 参数严格解析；默认显式禁用 thinking，启用时正确回传保留历史的私有字段。
- **测试项**：TC-L2-001、TC-L2-002、TC-L2-003、TC-L2-007、TC-L2-008、TC-L2-009、TC-L2-010（循环部分在 S04 集成）；真实客户端能力在 S18 以 TC-LIVE-001 验收。
- **S01 覆盖边界**：TC-L2-007 的 Memory/裁剪部分留 S15/S16；TC-L2-009 的 Runtime/ToolResult 部分留 S04/S06；TC-L2-010 的循环/消息配对/trace 留 S04。详见 `Docs/TESTING.md` §4.2.1。
- **前置阶段**：S00。

### S02 — 模型接入：错误处理与重试

- **模块**：模型接入层
- **对应需求**：FR-LLM-03。
- **目标**：把超时、限流、鉴权、服务端错误分类并实现退避重试。
- **输入**：S01 的 `LLMClient`。
- **输出**：扩展 `llm/errors.py`（鉴权/限流/超时）；重试策略（次数、退避、抖动）。
- **验收标准**：429/5xx 重试后成功；4xx 不重试；超时抛 `LLMTimeoutError` 且不挂起。
- **测试项**：TC-L2-004、TC-L2-005、TC-L2-006。
- **前置阶段**：S01。
- **异常根边界**：S02–S19 继续使用 `llm/errors.py` 的临时 `LLMError` 根；S20 引入 `AgentError` 后统一迁移（ISSUE-024）。
- **开工前检查**：全新 venv 安装 dev extras 后 50 passed、覆盖率 92.52%、ruff/mypy 通过；`test_packaging_config.py` marker 为 `unit`。

### S03 — Runtime：单轮直答

- **模块**：Agent Runtime
- **对应需求**：FR-RT-01。
- **目标**：实现"用户输入 → 调模型 → 直接返回"的最小闭环，无工具。
- **输入**：S02 的 `LLMClient`。
- **输出**：`runtime/agent.py`、`runtime/result.py`（`AgentResult`）。
- **验收标准**：模型无 tool_calls 时 1 步返回；`AgentResult` 含 reply、steps、usage。
- **测试项**：TC-L1-015A（正常直答）、TC-L1-015B（空响应错误路径）、TC-L1-015C（LLM 异常传播）；TC-L1-015 的工具循环部分留 S04。
- **前置阶段**：S02。
- **接口**：`Agent(llm_client)` 构造器注入；`async def run(self, user_input: str) -> AgentResult`；`session_id` 延后 S13。

### S04 — Runtime：工具调用循环（ReAct 核心）

- **模块**：Agent Runtime
- **对应需求**：FR-RT-02、FR-RT-03、FR-RT-04、FR-RT-06、FR-RT-08。
- **目标**：实现"判断 → 调工具 → 读结果 → 再判断"的多步循环，正确处理消息配对。
- **输入**：S03 的 `Agent`、工具调用协议（`Protocol`，本阶段用测试替身实现）。
- **输出**：`runtime/loop.py`；assistant/tool 配对逻辑；每次 LLM 响应一条 ThoughtStep，含 runtime_summary 来源和工具调用结果列表。
- **验收标准**：至少 3 步可收敛；混合正文与多工具按调用优先处理；参数错误可回灌修正；公开 trace 不暴露原始 reasoning，启用思考工具模式保留必要私有字段。
- **测试项**：TC-L1-015、TC-L1-024、TC-L1-028、TC-L1-030、TC-L2-009、TC-L2-010、TC-L3-006；真实工具与 HTTP 用例 TC-L4-010/011 在 S18 回填。
- **前置阶段**：S03。
- **备注**：本阶段仅依赖"工具调用协议"，真实注册机制在 S06 落地后再做一次集成回填（避免与需求的模块顺序冲突）。

### S05 — Runtime：循环安全阀

- **模块**：Agent Runtime
- **对应需求**：FR-RT-05。
- **目标**：为循环加上硬边界，保证最坏情况必然收敛。
- **输入**：S04 的循环。
- **输出**：`max_steps`、`deadline`、重复调用检测；`truncated` 标记与提示文案。
- **验收标准**：达到上限即停止并返回明确提示；重复相同调用 3 次中断；无死循环。
- **测试项**：TC-L1-016、TC-L1-029；TC-L4-008 在 S18 集成。
- **前置阶段**：S04。

### S06 — Tool：注册机制与 Schema

- **模块**：Tool 能力层
- **对应需求**：FR-TOOL-01。
- **目标**：提供统一的工具注册、Schema 生成与参数校验能力。
- **输入**：pydantic 参数模型。
- **输出**：`tools/registry.py`（`ToolSpec`、`ToolRegistry`、`@tool`）。
- **验收标准**：注册后可查、可生成合法 JSON Schema；重复注册拒绝；新增工具无需改 Runtime。
- **测试项**：TC-L1-007、TC-L1-008、TC-L1-009。
- **前置阶段**：S05。

### S07 — Tool：calculator

- **模块**：Tool 能力层
- **对应需求**：FR-TOOL-02。
- **目标**：安全地计算四则与括号表达式，杜绝任意代码执行。
- **输入**：表达式字符串。
- **输出**：`tools/builtin/calculator.py`（`ast` 白名单求值）。
- **验收标准**：正确求值；危险表达式被拒；除零/语法错误结构化返回。
- **测试项**：TC-L1-001、TC-L1-002、TC-L1-003。
- **前置阶段**：S06。

### S08 — Tool：time

- **模块**：Tool 能力层
- **对应需求**：FR-TOOL-03。
- **目标**：按时区返回当前时间。
- **输入**：可选 IANA 时区。
- **输出**：`tools/builtin/time_tool.py`。
- **验收标准**：默认时区正确；指定时区正确；非法时区返回参数错误。
- **测试项**：TC-L1-004、TC-L1-005。
- **前置阶段**：S06。

### S09 — Tool：todo

- **模块**：Tool 能力层
- **对应需求**：FR-TOOL-04。
- **目标**：提供会话级待办的增删改查。
- **输入**：会话 ID、待办内容/序号。
- **输出**：`tools/builtin/todo.py`。
- **验收标准**：增删查改在同一会话内一致；空列表返回空集合；session_id 通过可信执行上下文注入，模型参数不可覆盖。
- **测试项**：TC-L1-006、TC-L3-013；TC-L4-009/010 在 S18 回填。
- **前置阶段**：S06。

### S10 — Tool：沙箱内核与 read_file

- **模块**：Tool 能力层
- **对应需求**：FR-TOOL-05、FR-TOOL-07。
- **目标**：建立文件访问沙箱，并在此基础上提供只读文件访问。
- **输入**：沙箱根目录、相对路径。
- **输出**：`tools/sandbox.py`、`tools/builtin/read_file.py`。
- **验收标准**：`..`、绝对路径、符号链接逃逸全部阻断；大小与编码限制生效。
- **测试项**：TC-L1-010、TC-L1-011、TC-L1-012、TC-L5-003。
- **前置阶段**：S06。

### S11 — Tool：write_file

- **模块**：Tool 能力层
- **对应需求**：FR-TOOL-06。
- **目标**：在沙箱内安全写文件。
- **输入**：相对路径、内容、是否覆盖。
- **输出**：`tools/builtin/write_file.py`（原子写 + 覆盖保护）。
- **验收标准**：写入后可被 `read_file` 读回；默认不覆盖；越界与超限拒绝且不落盘。
- **测试项**：TC-L1-012（写分支）；独立文件 E2E 待 S18 新增。
- **前置阶段**：S10。

### S12 — Tool：search

- **模块**：Tool 能力层
- **对应需求**：FR-TOOL-08。
- **目标**：抽象搜索能力，未配置时显式报错而非伪造结果。
- **输入**：查询串、搜索 provider 配置。
- **输出**：`tools/builtin/search.py`（`SearchProvider` 协议 + `NullProvider`）。
- **验收标准**：未配置 provider 时返回 `not_configured`；配置后可透传结果。
- **测试项**：TC-L1-021、TC-L3-006。
- **前置阶段**：S11。

### S13 — Memory：Redis 短时会话窗口

- **模块**：Memory 记忆
- **对应需求**：FR-MEM-01、FR-MEM-02、FR-MEM-05、FR-RT-07。
- **目标**：会话消息窗口的写入、截断与读取，并落实**写回时机**（本轮结束后、响应返回前同步写）。
- **输入**：会话 ID、消息、写入时机钩子。
- **输出**：`memory/short_term.py`（完整轮次 List + 按轮 LTRIM + TTL）；Agent 的同步写回调用点。
- **验收标准**：按序恢复完整轮次，tool_call_id 与必需的私有 reasoning 字段不丢；TTL 生效；响应前同步写；不可用时降级；跨会话不串扰。
- **测试项**：TC-L3-001、TC-L3-002、TC-L3-005、TC-L3-014（Mongo/Context 部分在 S14/S16 回填）；TC-L3-011/012 在 S17/S18 全链路集成。
- **前置阶段**：S12。

### S14 — Memory：MongoDB 中期存储与检索

- **模块**：Memory 记忆
- **对应需求**：FR-MEM-03、FR-MEM-04、FR-RT-07。
- **目标**：消息持久化与跨会话检索。
- **输入**：会话 ID、消息、检索条件。
- **输出**：`memory/mid_term.py`（集合 + 复合索引）。
- **验收标准**：写入后可查；按会话 + 时间倒序 + 关键词检索正确；写入失败仅告警。
- **测试项**：TC-L3-003、TC-L3-004、TC-L3-014（持久化与私有字段隔离部分）。
- **前置阶段**：S13。

### S15 — Context：管线拼接与 token 预算

- **模块**：Context 管线
- **对应需求**：FR-CTX-01、FR-CTX-02。
- **目标**：按固定顺序拼接 system prompt、工具定义、记忆片段与最近 K 轮对话，并**计算 token 与预算**。
- **输入**：会话 ID、当前完整轮次、Memory 读取结果、实际 tools_snapshot、token 预算和协议结构开销。
- **输出**：`context/builder.py`、`context/token_counter.py`（本地 `tiktoken` 估算 + 安全余量）、`ContextPayload`。
- **验收标准**：拼接顺序正确；输入估算含 messages、完整 tools Schema 与开销；计数与发送复用相同快照；预算=上限−输出预留−10%上限；计数可复现，tokenizer 缺失分支仍统计 Schema。
- **测试项**：TC-L1-013、TC-L1-022、TC-L1-025、TC-L3-007。
- **前置阶段**：S14。

### S16 — Context：双触发整轮裁剪

- **模块**：Context 管线
- **对应需求**：FR-CTX-03、FR-CTX-04。
- **目标**：以「轮」为单位维护窗口；**轮次超 K 或 token 超预算**时整轮丢弃最旧对话，直至两项均满足。
- **输入**：S15 的拼接结果 + 窗口大小 K（默认 10 轮）+ token 预算。
- **输出**：`context/window.py`；`rounds_before/after`、`tokens_before/after`、`dropped_rounds`、`trim_reason`。
- **验收标准**：每次 LLM 出站前复核完整请求；最多保留 K 个完整历史轮次，不拆当前工具往返；最小集合仍超预算则本地 CONTEXT_TOO_LARGE，不重放已执行工具；裁剪分项可追溯。
- **测试项**：TC-L1-014、TC-L1-023、TC-L1-025、TC-L1-026、TC-L1-027、TC-L3-014；TC-L4-005/012 在 S18 集成。
- **前置阶段**：S15。

### S17 — 系统数据库（MySQL）：系统信息与审计

- **模块**：支撑组件：系统数据库
- **对应需求**：FR-SYS-01、FR-SYS-02、FR-SYS-03、FR-SYS-04、FR-SYS-05、FR-RT-07。
- **目标**：落地**会话管理、系统模型、工具登记**三类系统信息，以及工具调用审计与请求指标；与 Redis / MongoDB 职责隔离、互不影响。
- **输入**：`SystemDBConfig`（DSN、连接池、是否自动建表）、模型/工具注册信息、会话与调用事件。
- **输出**：`systemdb/schema.sql`（五张表）、`systemdb/repository.py`、`systemdb/models.py`。
- **验收标准**：五张表可幂等建表；启动时模型与工具登记正确 upsert；会话状态与审计正确写入；MySQL 不可用时降级且不影响对话主链路。
- **测试项**：TC-L3-009、TC-L3-010、TC-L3-011、TC-L3-012。
- **前置阶段**：S16。

### S18 — Interface：HTTP API

- **模块**：交互接口层
- **对应需求**：FR-IF-01、FR-IF-02、FR-IF-03、FR-IF-04；联合验收 FR-RT-03、FR-RT-08、FR-MEM-02 与 AC-23。
- **目标**：提供 `POST /chat` 与健康检查，作为**唯一对外入口**（不实现 CLI）。
- **输入**：JSON 请求（session_id、message）。
- **输出**：`interface/http.py`（FastAPI 应用）。
- **验收标准**：双窗口交替恢复、纯对话与工具追问均可用；返回 trace/truncated 和工具次数；本地上下文过大 400；健康检查不泄密；真实 API 直答与自主工具闭环具备正式验收记录。
- **测试项**：TC-L4-001~012（含前序阶段 HTTP 回填）、TC-L3-008、TC-LIVE-001、TC-LIVE-002；启用思考模式时加 TC-LIVE-003。真实密钥仅从 DEEPSEEK_API_KEY 读取，禁止写入 Prompt、夹具或源码。
- **前置阶段**：S17。

### S19 — Observability：结构化日志与 trace_id

- **模块**：可观测与治理
- **对应需求**：FR-OBS-01、FR-OBS-02、FR-OBS-04。
- **目标**：输出可检索的 JSON 日志，并让 trace_id 贯穿一次请求。
- **输入**：各层日志事件。
- **输出**：`observability/logging.py`（JSON Formatter + contextvars）、脱敏过滤器。
- **验收标准**：日志为合法 JSON；trace_id 一致；密钥不外泄。
- **测试项**：TC-L1-020、TC-L5-004。
- **前置阶段**：S18。

### S20 — Observability：异常分类与统一错误响应

- **模块**：可观测与治理
- **对应需求**：FR-OBS-03、FR-IF-04。
- **目标**：建立异常体系与统一错误对象，保证任何异常都有明确出处。
- **输入**：各模块抛出的异常。
- **输出**：`observability/errors.py`（`AgentError` 及子类、错误码映射）。
- **验收标准**：各类异常映射到稳定错误码与 HTTP 状态；未知异常兜底 500；工具异常不影响进程。
- **测试项**：TC-L1-019、TC-L4-007。
- **前置阶段**：S19。

### S21 — Config：配置与依赖注入

- **模块**：配置与依赖注入
- **对应需求**：FR-CFG-01、FR-CFG-02、FR-CFG-03、FR-CFG-04、FR-LLM-05。
- **目标**：把散落的配置与对象装配集中化，完成最终收口。
- **输入**：配置文件 + 环境变量。
- **输出**：`config/models.py`、`config/loader.py`、`config/container.py`。
- **验收标准**：模型/工具/Prompt 三类配置可加载并校验；缺失必填项启动即失败；容器可装配全链路且测试可替换实现。
- **测试项**：TC-L1-017、TC-L1-018、TC-L4-006。
- **前置阶段**：S20。

---

## 4. 里程碑

| 里程碑 | 覆盖阶段 | 达成标志 | 可演示能力 |
| --- | --- | --- | --- |
| **M1 可对话骨架** | S00–S05 | **已达成（2026-10-22）**：单轮直答 + 工具循环 + 安全阀全绿 | 用测试替身工具完成"提问 → 调工具 → 回答" |
| **M2 工具完备** | S06–S12 | 六个工具注册可用、沙箱用例全过 | 真实执行计算、时间、待办、文件读写 |
| **M3 有记忆有上下文** | S13–S16 | 多轮记忆 + 压缩策略全绿 | 跨轮引用、长对话不溢出 |
| **M4 可交付** | S17–S21 | MySQL 系统库 + HTTP 单入口 + 可观测 + 配置收口 + 真实 API 验收 | v0.1 全量验收（AC-01 ~ AC-23） |

## 5. 完成定义（Definition of Done）

### 5.1 单个阶段的 DoD

- [ ] 需求条目（FR）与本阶段一一对应，且已评审
- [ ] 测试用例已写入 `Docs/TESTING.md`（或已存在）
- [ ] 先提交失败测试，再实现到全绿
- [ ] 该阶段全部测试项通过，且未造成既有用例回归
- [ ] `ruff` 零告警；`mypy` 无新增错误
- [ ] 相关文档与实现一致（`REQUIREMENT` / `DESIGN` / `TESTING`）
- [ ] `Docs/PROMPT.md` 已追加本轮记录；`Docs/ISSUE.md` 已更新
- [ ] OpenSpec 归档在实现、测试、文档全部完成后执行；归档后阶段内变更必须新建 change 或记录例外
- [ ] commit 信息符合 `AGENT.md` §5.2，并已推送

### 5.2 里程碑的 DoD

- [ ] 覆盖阶段全部满足单阶段 DoD
- [ ] 里程碑可演示（有可运行的命令与可复现的演示步骤）
- [ ] wheel 构建成功，且 wheel 内 `agent_mini/` 与 `DESIGN.md` §2.2 清单一致（含 package-data）
- [ ] 新增代码覆盖率 ≥ 80%
- [ ] 无 P0 / P1 缺陷
- [ ] 依赖清单复核：未引入被禁 Agent 框架（`AC-18`）

### 5.3 项目 v0.1 的 DoD

- [ ] `Docs/REQUIREMENT.md` §9 的 AC-01 ~ AC-23 全部满足
- [ ] `Docs/TESTING.md` §6.2 准出标准全部满足
- [ ] HTTP 单入口可用（不提供 CLI），文档给出真实可执行命令
- [ ] `README.md` 补齐安装、配置、运行、测试命令
- [ ] 全量测试在 Linux 与 Windows 均通过
- [ ] LIVE-001/002 使用真实 API 通过并留存脱敏验收记录；启用思考模式时 LIVE-003 也通过

## 6. 进度记录

| 阶段 | 状态 | 完成日期 | 备注 |
| --- | --- | --- | --- |
| S00 | 已完成 | 2026-10-22 | 2026-10-22 修正：补齐 DESIGN §2.2 骨架（ISSUE-017）；补 schema.sql package-data 与 wheel/结构/占位测试（ISSUE-018），复验通过 |
| S01 | 已完成 | 2026-10-22 | 2026-10-22 评估修复：P0-01/P1-01/P1-09 已修，依赖 pin 与文档闭环完成（S01-report、ISSUE-021/022） |
| S02 | 已完成 | 2026-10-22 | 错误分类、429/5xx 退避重试、超时不重试；复验修复完成：默认 `retry_events`、具体异常断言、thinking+tools+reasoning 组合、`mypy agent_mini tests` 门禁；72 passed、覆盖率 95.69%；临时 LLMError 根 S20 迁移（ISSUE-024/026/027） |
| S03 | 已完成 | 2026-10-22 | 单轮直答：`Agent(llm_client).run(user_input)` 返回冻结 `AgentResult(reply/steps/usage)`；TC-L1-015A/B/C 通过；88 passed、覆盖率 96.03%；session_id 延后 S13（ISSUE-028） |
| S04 | 已完成 | 2026-10-22 | ReAct 工具循环：ToolExecutor Protocol、assistant/tool 配对、ThoughtStep/ToolCallTrace、错误回灌与独立结果脱敏；99 passed、覆盖率 96.17%；S05 安全阀未实现 |
| S05 | 已完成 | 2026-10-22 | 循环安全阀：max_steps/deadline/repeat、truncated/终止原因、固定文案、中断补齐；112 passed、覆盖率 95.72%；M1 S00–S05 收口 |
| S06 | 已完成 | 2026-10-22 | ToolRegistry/pydantic Schema/ToolResult/ToolContext 预留；RegistryExecutor 集成回填；129 passed、覆盖率 95.25%；内置工具留 S07–S12 |
| S07 | 已完成 | 2026-10-23 | calculator：ast 白名单四则/括号/取负、危险表达式拒绝、结构化错误与阈值；164 passed、覆盖率 95.81% |
| S08 | 已完成 | 2026-10-23 | time：默认 Asia/Shanghai、指定 IANA、tz 兼容、now_provider 注入、invalid_timezone；176 passed、覆盖率 95.97% |
| S09 | 已完成 | 2026-10-23 | todo：ToolContext 注入、进程内 MemoryTodoStore、1-based 稳定序号、会话隔离、伪造 session_id 拒绝；192 passed、覆盖率 96.34% |
| S10 | 已完成 | 2026-10-23 | 沙箱四步校验 + read_file：.. / 绝对路径 / 符号链接阻断、大小/扩展名/隐藏/路径长度限制、结构化编码/二进制错误；224 passed、覆盖率 96.76% |
| S11 | 已完成 | 2026-10-23 | write_file：复用沙箱、同目录临时文件+fsync+os.replace、默认不覆盖、失败无残留、read_file 往返；247 passed、覆盖率 97.06% |
| S12–S21 | 未开始 | — | 后续阶段 |

> 每完成一个阶段，在此表更新状态与日期，并在 `Docs/ISSUE.md` 记录遇到的问题。













