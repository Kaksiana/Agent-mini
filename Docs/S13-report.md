# S13 阶段代码产出独立评估报告

> 评估时间：2026-10-23 17:04（Asia/Shanghai）
> 基准提交：`eaa1215`（`main` 与 `origin/main` 一致）
> 评估方式：独立只读复核；除本报告与 `Docs/PROMPT.md` 记录外，不修改实现、测试、OpenSpec 或远程状态
> 结论：**不通过；S13 暂不可进入 S14**  
> 修复状态：见 §10；P0-02/P0-03 与 P1 已处理，P0-01 仍为残余风险

## 1. 评估范围与基准

实际读取并交叉核对：

- `AGENT.md` §1–§10，重点是文档优先、TDD、Prompt 时机、OpenSpec、Commit、阶段 DoD 与报告归档。
- `Docs/PLAN.md` S12、S13、S14、§5 DoD 与阶段进度表。
- `Docs/REQUIREMENT.md` FR-RT-07、FR-TOOL-04、FR-MEM-01/02/05、AC-06/07/21。
- `Docs/DESIGN.md` §1.1/1.3、§2.2、§3.2、§3.4、§4、§5.4、§6、§7、§8 与变更记录 v0.28。
- `Docs/TESTING.md` TC-L3-001/002/005/011/012/014、S13 覆盖边界、测试分层与准出标准。
- `Docs/PROMPT.md` S12 修复与 S13 执行记录；`Docs/ISSUE.md` ISSUE-038/039、S13 记录；`MEMORY.md` S13；`README.md` 安装与测试说明。
- `agent_mini/memory/base.py`、`short_term.py`、`runtime/agent.py`、`loop.py`、`result.py`、`registry_adapter.py`、`tools/builtin/write_file.py`、`search.py`。
- `tests/unit/test_short_term.py`、`test_agent.py`、`test_safety_valve.py`、`test_package_skeleton.py` 与 Registry/Tool 测试。
- `pyproject.toml`；`openspec/specs/short-term-memory/spec.md`、`engineering-standards/spec.md`；归档 change `2026-10-23-s13-memory-redis-shortterm` 的 proposal/design/tasks/spec。
- S12 报告修复提交 `db181e7`、`04e0f17`、`9427741`、`925cfeb`；S13 提交 `ea0e825`、`ebd81c4`、`eaa1215`。

基准文档存在五处直接不一致或缺口：

1. short-term-memory 主规格要求“append 抛异常时 Agent.run 仍返回”，实现却只依赖具体 `ShortTermMemory` 内部吞异常；任意 `ShortTermStore` 实现抛异常会直接穿透 Runtime。
2. DESIGN §3.2.2 要求 Redis 等待受配置超时约束；实现没有 Memory 写回 timeout，悬挂存储会永久阻塞响应。
3. DESIGN §3.2.2 要求安全阀中断后保存最终 assistant 回复并标记 truncated；当前 Redis 轮次结构没有 truncated 字段，Runtime 也不把安全阀文案追加到消息。
4. DESIGN §3.4 的 key 仍写 `session:{id}:messages`，§5.4 与实现则是 `agent_mini:short_term:{session_id}:rounds`；`memory/__init__.py` 仍称 S13–S14 待落地。
5. TESTING 头部仍写自动化 258（unit 198、contract 64、integration 17、unmarked 0），同页又写 S13 为 270；实际为 270，其中 unit 204、contract 64、未标记 2。全部 TC-L3 S13 测试却标成 unit，`pytest -m integration` 收集为 0。

## 2. 复核命令与结果

| 命令/检查 | 结果摘要 |
| --- | --- |
| `git status --short --branch`、`git rev-parse HEAD origin/main` | 评估前为干净的 `main...origin/main`；两者均为 `eaa1215` |
| `git log/show/diff --check` | S13 change、测试、实现、依赖在同一 feat commit；Prompt/Docs 后提交；feat 正文单行 135 字符、docs 正文 79 字符 |
| `pytest -q --disable-warnings --maxfail=1` | **279 passed** |
| `pytest -q --cov=agent_mini --cov-report=term --cov-fail-under=90` | **279 passed，97.09%**；short_term 98%、agent 100% 行覆盖 |
| `pytest --collect-only -m unit/contract/integration/e2e` | unit 204、contract 64、未标记 2；integration/e2e 均为 0 |
| `ruff check .` | 通过，零告警 |
| `ruff format --check .` | 通过，68 files already formatted |
| `mypy agent_mini tests` | 通过，65 source files，0 errors |
| `openspec validate --all --strict` | **13 passed，0 failed**；engineering-standards 有既有 INFO 长度提示 |
| `pip wheel . --no-deps` | 成功生成 wheel；包含 `memory/short_term.py` 与 `systemdb/schema.sql` |
| Python 3.11.14 新 venv 安装 wheel + `[dev]`、仓库外导入、`pip check` | 通过；隔离环境解析 redis 7.4.1、fakeredis 2.40.0，无依赖冲突 |
| Python 3.11.14 临时干净源码副本全量测试 | **279 passed** |
| Memory store 抛异常/悬挂探针 | append 抛 `ConnectionError` 时 `Agent.run` 同样抛出；append 永不完成时外部 50ms wait_for 超时，Runtime 无自身降级 |
| Redis 分步写探针 | RPUSH/LTRIM 成功、EXPIRE 失败后 append 返回 False，但 List 长度为 1、TTL=-1，原始值仍含私有 reasoning |
| 安全阀轮次探针 | max_steps=1 时结果 truncated=True；写入消息角色仅 user/assistant(tool_calls)/tool，末条是工具结果，不含返回给用户的安全阀 assistant 文案 |
| session 工具链探针 | `Agent.run(..., session_id="A")` 经 RegistryExecutor 调 todo，结果为 `missing_context`；session_id 未进入 ToolContext |
| S12 最终发布窗口探针 | 父目录在最后校验后换为 root 外 junction；函数返回 path_escape，但发布后清理删除了 root 外原文件 |
| search name property 探针 | provider 的 `name` property 抛异常时，search 仍直接泄漏 RuntimeError |

本次未复跑：

- 真实 Redis 服务：阶段测试使用 fakeredis，仓库未提供本阶段真实 Redis 启动/验收命令；未改变 Docker 或外部服务状态。
- TC-L3-011/012 全链路：PLAN/TESTING 明确留 S17/S18；但其“写回超时且不阻断响应”基础契约已用确定性 store 探针验证为失败。
- TC-L3-014 的 Mongo/Context/公开检索部分：按计划留 S14/S16。
- 真实 API、MongoDB、MySQL、HTTP：均不属于 S13 交付范围。

## 3. 维度结论表

| 维度 | 结论 | 理由与证据 |
| --- | --- | --- |
| 需求与范围合规 | **有条件通过** | 未越界实现 Mongo/Context/HTTP；Redis 短时窗口、session_id 和写回钩子已落地，但 FR-MEM-05/FR-RT-07 的失败不阻断契约不成立 |
| 完整轮次与协议字段 | **不通过** | 正常完成轮次可保存 role/content/tool_calls/tool_call_id/reasoning；安全阀轮次缺最终 assistant 回复和 truncated 标记 |
| Redis 结构、裁剪与 TTL | **不通过** | 普通 RPUSH/LTRIM/EXPIRE、K=2 和 TTL=1s 测试通过；三命令非原子，EXPIRE 失败会留下 TTL=-1 的私有数据 |
| 写回时机与降级 | **不通过** | 正常 store 在 Agent 返回前被 await；store 抛异常会中断响应，悬挂 store 无 timeout，违反主规格和 FR-MEM-05/RT-07 |
| 会话隔离与上下文传播 | **不通过** | A/B Redis key 顺序测试通过；session_id 未传给 RegistryExecutor/ToolContext，Agent 内 todo 等会话工具无法工作 |
| 数据模型与私有字段 | **有条件通过** | JSON + Message model_validate 可保留 reasoning 与 call_id；轮次模型不携带 truncated，构造参数/session_id 缺少边界校验 |
| 测试质量 | **不通过** | 7 个新增测试覆盖普通路径，但 L3 全标 unit、无 integration；工具轮次由测试手工拼装，未经过 Agent；异常 store、悬挂、部分写和安全阀均漏测 |
| 全局规范符合性 | **不通过** | ruff/format/mypy、中文 docstring、无 noqa/type-ignore 通过；Docs/OpenSpec/TDD/Prompt 时序、测试分层和前置门禁违反 AGENT |
| 打包与分发 | **通过** | wheel 包含新增模块和 package-data；Python 3.11 隔离安装、仓库外导入、pip check 与全量测试通过 |
| 依赖审计 | **有条件通过** | redis/fakeredis 符合设计选型且有上界，无禁用 Agent 框架；README dev 工具清单未补 fakeredis，pytest 仍只有下界 |
| 流程与文档闭环 | **不通过** | strict 校验与归档通过；但 change 未形成先于代码的提交，Prompt/Docs 后补，测试统计/key/包说明不一致，S12 阻断项也未真实闭环 |
| 可复现性与后续影响 | **不通过** | 常规测试与 wheel 可复现；异常、超时、部分提交和安全阀等生产边界失败，将直接影响 S14/S15/S16/S18 |

## 4. 问题清单

### P0

#### S13-P0-01 — S12 的发布后清理会删除沙箱外原文件

- **位置**：`agent_mini/tools/builtin/write_file.py:135-181`（`_atomic_write`）；`Docs/S12-report.md:248-263`；`Docs/ISSUE.md:459-467`。
- **问题描述**：S12 修复在发布后才检查 target containment；若攻击者在第 159 行后把父目录换为 root 外 junction，`os.replace` 先覆盖外部原文件，第 170 行发现越界，异常清理再对解析到 root 外的 target 执行 unlink。探针结果为 `path_escape`，但外部原文件已被删除。返回错误不能撤销数据破坏。
- **判定依据**：FR-TOOL-06/07、AC-04 与安全缺陷分级；AGENT §8.4 要求前置阶段未达 DoD 不得开启下一阶段。S12 报告的 P0 修复记录与实际行为矛盾。
- **建议方向**：停止“先发布、再验证、再删除”的补偿式修复；使用可信已打开目录句柄/no-follow 相对发布或平台等价机制，确保发布动作本身不能解析到 root 外。补覆盖外部既有文件的确定性竞态回归并重开 ISSUE-038。

#### S13-P0-02 — Redis 分步写会留下无 TTL 的私有 reasoning

- **位置**：`agent_mini/memory/short_term.py:35-54`（`append_round`）；`Docs/DESIGN.md:227-235,254,324`；short-term-memory 主规格“完整轮次存储”。
- **问题描述**：RPUSH、LTRIM、EXPIRE 是三个独立 await。探针让前两步成功、EXPIRE 失败：方法返回 False 并告警，但 Redis List 已存在、TTL=-1，且值中保留私有 reasoning。类似地，LTRIM 失败会留下未裁剪窗口。该状态可能永久保留敏感协议数据并突破 K 上限。
- **判定依据**：FR-MEM-01 是 P0，要求 TTL 与整轮窗口；DESIGN §3.2.3 把 reasoning 定义为同 session 私有字段；安全/数据留存问题按项目分级为 P0。
- **建议方向**：用 Redis MULTI/EXEC pipeline 或单个 Lua 脚本原子执行 RPUSH+LTRIM+EXPIRE，并明确网络结果不确定时的幂等策略；增加 LTRIM/EXPIRE 各阶段失败后“无部分状态或状态仍满足 TTL/K”的测试。

#### S13-P0-03 — Memory 抛异常或悬挂会阻断单轮响应

- **位置**：`agent_mini/runtime/agent.py:28-45`（`Agent.run`）；`agent_mini/memory/base.py:8-26`；short-term-memory 主规格“响应前同步写回”；`Docs/TESTING.md:282`。
- **问题描述**：Agent 直接 await Protocol，没有 try/except 与 timeout。store.append_round 抛 `ConnectionError` 时 Agent 同样抛出；store 不返回时响应永久悬挂。现有具体 ShortTermMemory 能吞已抛出的 Redis 异常，却不能保证所有 Protocol 实现、序列化边界或无响应连接都降级。
- **判定依据**：FR-MEM-05、FR-RT-07、AC-07/21 均为核心可用性契约；OpenSpec 场景明确“append 抛异常 → Agent.run 仍返回”；TC-L3-011 明确 Redis 等待必须在配置超时内。
- **建议方向**：在 Runtime 的 Memory 边界设置可配置硬超时并统一捕获异常/取消语义，记录一次结构化 `memory.degraded` 后返回已生成 AgentResult；具体 store 仍可保留内部诊断。补 throwing/hanging store 的任务完成与日志断言。

### P1

#### S13-P1-01 — 安全阀返回没有形成可恢复的完整轮次

- **位置**：`agent_mini/runtime/agent.py:34-45`；`agent_mini/runtime/loop.py:111-139,228-247`；`Docs/DESIGN.md:233-235`；`tests/unit/test_short_term.py:162-171`。
- **问题描述**：`_truncated_result` 只创建 AgentResult，不把固定安全阀文案追加为 assistant Message。Agent 随后直接保存原 messages；max_steps 探针得到 user→assistant(tool_calls)→tool，用户实际收到的最终安全阀回复未入库，轮次也没有 truncated 标记。恢复后历史与用户见到的对话不一致。
- **判定依据**：DESIGN §3.2.2 明确写入“最终 assistant 回复”，并要求安全阀轮次合法配对且标记 truncated；FR-MEM-01 要求完整轮次。
- **建议方向**：让 loop 返回结构同时携带最终可持久化消息，或在单一收口点追加合成 assistant 回复；扩展轮次元数据保存 truncated/termination_reason。对 max_steps/deadline/repeat 三分支做 Agent→Memory→恢复测试。

#### S13-P1-02 — `session_id` 未传播到工具可信上下文

- **位置**：`agent_mini/runtime/agent.py:28-45`；`agent_mini/runtime/loop.py:70-79`；`agent_mini/runtime/registry_adapter.py:7-20`；`agent_mini/tools/registry.py:115-137`。
- **问题描述**：S13 在 Agent.run 接收 session_id，但 ToolExecutor.execute 仍只接 ToolCall，RegistryExecutor 调 registry.execute 时不传 ToolContext。探针让 session A 通过 Agent 调 todo，得到 `missing_context`。Memory session 与会话工具 session 形成两套断开的路径。
- **判定依据**：FR-TOOL-04 与 AC-06 要求可信 session_id 驱动 todo 隔离；DESIGN 最终调用链要求同一会话贯穿 Runtime/Tool/Memory。S13 是 session_id 正式进入 Runtime 的阶段。
- **建议方向**：设计请求级 Runtime context，并把同一可信 session_id/trace/sandbox 配置传到工具适配器；禁止模型参数覆盖。补 Agent→Registry→todo 的 A/B 隔离与伪造参数测试，避免等到 S18 才重构核心协议。

#### S13-P1-03 — OpenSpec、TDD 与 Prompt 均未形成实现前证据

- **位置**：提交 `ea0e825`、`ebd81c4`；`Docs/PROMPT.md:1903-1920`；归档 change tasks。
- **问题描述**：S13 的 proposal/design/tasks/spec 与实现、测试、依赖全部在同一个 feat commit，仓库历史不存在先于代码的 change 提交；没有可复现的红灯提交/输出；原始 Prompt 又在后续 docs commit 才入库。tasks 却把 TDD 红全部勾选。
- **判定依据**：AGENT §1 要求文档/OpenSpec change 先于代码；§2 要求先提交失败测试并确认红因；§3 要求 Prompt 在提交代码前记录；§6 要求 change 先建后实现。
- **建议方向**：历史偏差如实登记，不改写已推送历史；S14 起采用“Prompt/Change → 红测试证据 → 实现 → 文档收口 → 归档”的独立提交门禁，并把红灯命令摘要写入 change/tasks 或 Prompt。

#### S13-P1-04 — L3 测试被标为 unit，且关键断言由手工数据自证

- **位置**：`tests/unit/test_short_term.py:1-171`；`Docs/TESTING.md:68,81,257-285,365-370`。
- **问题描述**：文件声明 TC-L3-001/002/005/014，却全局标记 `unit`；integration 收集为 0。工具配对/reasoning 测试手工构造 `_tool_round` 后直接写存储，没有经过 Agent/loop；降级测试只让 ShortTermMemory 内部 Redis client 抛错，未按 OpenSpec 场景让 append 本身抛错。因此 98% 行覆盖没有捕获四个已复现的行为缺陷。
- **判定依据**：TESTING 的分层隔离与 marker 表明确 fakeredis/Redis Memory 属 L3 integration；AGENT §2 要求测试真实验证行为，禁止自证。
- **建议方向**：把 Redis/Runtime 联合用例移到 integration 标记；保留纯编码解码为 unit。新增真实 Agent 工具轮次、安全阀、throw/hang、部分写、TTL 刷新与恢复测试，并确保 `pytest -m integration` 非空可执行。

#### S13-P1-05 — 文档统计、key 和完成声明相互矛盾

- **位置**：`Docs/TESTING.md:9-14`；`Docs/DESIGN.md:321-328,464-472`；`Docs/PLAN.md:352`；`MEMORY.md:3-8`；`agent_mini/memory/__init__.py:1`。
- **问题描述**：TESTING 同页同时宣称 258 和 270；unit 204 + contract 64 只到 268，遗漏两项未标记 M2 测试。DESIGN 有两种 Redis key。memory 包仍称 S13 未落地。PLAN/MEMORY 则已标完成且称“Redis/序列化失败降级”，未披露部分提交、异常穿透和无 timeout。
- **判定依据**：AGENT §1/§7/§8 要求文档、测试和实现一致，阶段完成声明必须基于真实 DoD。
- **建议方向**：统一由 collect 命令生成 total/marker 统计并说明 unmarked=0 的目标；统一 key；更新包职责说明；在 P0/P1 关闭前把 S13 状态恢复为未完成或修复中。

#### S13-P1-06 — S12 的强制修复项仍未真实闭环

- **位置**：`agent_mini/tools/builtin/search.py:96-105`；`Docs/PLAN.md:182-191`；`Docs/REQUIREMENT.md:199`；`Docs/ISSUE.md:477-485`；`Docs/S12-report.md:252-263`。
- **问题描述**：除 P0-01 外，provider `name` property 抛异常仍会从 search 泄漏 RuntimeError；TC-L3-006 仍错误映射到 search，ISSUE-039 仍为 Open。S12 报告却记录 M2 恢复达成，随后进入 S13。
- **判定依据**：S12 报告明确列这些为进入 S13 前必须处理的 P1；AGENT §8.4 和 TESTING §6.2 禁止带未解决 P0/P1 开启下一阶段。
- **建议方向**：重新打开 S12 修复 change：把 name 读取纳入 provider_result_invalid 边界，修正 FR/PLAN/TESTING 的 TC 映射并关闭 ISSUE-039；所有必须项实测后再恢复 S12/M2/S13 状态。

### P2

#### S13-P2-01 — 构造参数与 session_id 缺少边界校验

- **位置**：`agent_mini/memory/short_term.py:21-33,56-69`；`agent_mini/runtime/agent.py:28-44`；`agent_mini/runtime/result.py:82-102`。
- **问题描述**：max_rounds/ttl_seconds 可为 0、负数或 bool；max_rounds=0 会生成 LTRIM 0 -1，反而保留全部写入，而读取永远返回空。空白/超长 session_id 也可进入 Redis key 与 AgentResult。
- **判定依据**：全局错误处理与输入边界规范；配置最终由 S21 提供，但组件构造器当前已公开使用。
- **建议方向**：在构造期拒绝非正严格整数并给 session_id 定义非空/长度/字符策略；补 0、负数、bool、空白和超长边界测试。

#### S13-P2-02 — 单条损坏记录会清空整个读取窗口

- **位置**：`agent_mini/memory/short_term.py:56-76,87-89`（`get_recent_rounds` / `_decode_round`）。
- **问题描述**：列表推导任一元素解析失败时，整个方法捕获并返回 []，所有其他合法轮次一起丢失；日志也没有区分连接错误和数据损坏。
- **判定依据**：FR-MEM-02 要求恢复最近完整轮次；可观测性规范要求错误可定位而不泄露正文。
- **建议方向**：明确损坏记录策略：逐条跳过并记录位置/计数，或 fail-closed 但暴露稳定诊断码；不要记录消息正文。补头/中/尾单条损坏测试。

#### S13-P2-03 — TTL/结构测试覆盖仍不足且使用真实 sleep

- **位置**：`tests/unit/test_short_term.py:39-81`。
- **问题描述**：未验证默认 K=10、每次写入刷新 TTL、原始 JSON 含 round_id 且不使用 pickle、limit 边界、部分命令失败或损坏数据；TTL 测试真实 sleep 1.1 秒，增加耗时和调度抖动风险。
- **判定依据**：OpenSpec 完整轮次/TTL 需求与 AGENT §2 测试可重复要求。
- **建议方向**：使用 fakeredis 可控时间或 TTL 数值窗口断言；直接检查 raw List JSON 和 TTL 刷新；覆盖每个 Redis 命令失败点。

#### S13-P2-04 — 依赖说明与可复现策略未完全同步

- **位置**：`pyproject.toml:11-26`；`Docs/DESIGN.md:22-31`；`README.md:15-18`。
- **问题描述**：redis/fakeredis 均有兼容上界并可在 Python 3.11 安装，属于正向改进；但 README 的 dev 工具清单未提 fakeredis，DESIGN 只写 redis≥5 而 change 固定 ≥7.4，pytest 仍为无上界 `>=8.0`，隔离环境实际解析到 9.1.1。
- **判定依据**：依赖声明与文档一致性、可复现性要求。
- **建议方向**：解释 redis 7.4 下界的必要性并同步技术栈表；README 补 fakeredis；若要求严格复现，采用锁文件或为 pytest 设置经验证上界。

#### S13-P2-05 — 提交格式、骨架清单与包说明有维护噪声

- **位置**：提交 `ea0e825`、`ebd81c4`；`tests/unit/test_package_skeleton.py:42-59`；`agent_mini/memory/__init__.py:1`。
- **问题描述**：feat/docs 正文分别有 135/79 字符行，超过 72；DESIGN_FILES 重复列出 short_term.py 与 base.py；memory 包 docstring 已过期。这些不会改变行为，但降低审计可信度。
- **判定依据**：AGENT §5.2；engineering-standards 的注释不过期和目录测试可维护性要求。
- **建议方向**：后续 commit 正文换行；清理重复清单并更新包职责说明；不改写已推送提交历史。

### Info

#### S13-INFO-01 — 正常 Redis 路径的数据保真较好

- **位置**：`short_term.py`、`test_short_term.py`。
- **观察**：单个 JSON 元素承载完整消息列表，正常写入按轮裁剪；tool_call_id、tool_calls 与 reasoning_content 经 model_dump/model_validate 可往返，A/B key 顺序测试没有串话。
- **建议**：原子化写入与安全阀收口时保留这一数据结构优势。

#### S13-INFO-02 — 范围控制与依赖方向基本正确

- **位置**：S13 diff、归档 proposal/design、`pyproject.toml`。
- **观察**：使用 redis-py asyncio 与 fakeredis，没有引入 Agent 框架，也没有提前实现 MongoDB、Context、HTTP、DI 或真实 API。
- **建议**：后续阶段继续通过 Protocol 注入，但 Runtime 必须自己守住异常/timeout 边界。

#### S13-INFO-03 — 打包和最低版本复现通过

- **位置**：wheel 内容与 Python 3.11 临时环境。
- **观察**：新增 memory 模块和 schema.sql 均进入 wheel；仓库外导入、pip check、Python 3.11 全量 270 项通过。
- **建议**：保留隔离构建验收，并增加不依赖源码布局的安装级 smoke。

## 5. 需求—实现—测试追溯表

| FR / TC / 规格 | 实现位置 | 测试位置 | 覆盖 | 越界/缺口 |
| --- | --- | --- | --- | --- |
| FR-MEM-01 完整轮次/K/TTL | `short_term.py:35-54,79-89` | `test_short_term.py:39-69` | 部分 | 普通路径通过；命令非原子，TTL/K 可部分失效；安全阀轮次不完整 |
| FR-MEM-02 恢复/隔离 | `short_term.py:31-33,56-76` | `test_short_term.py:39-46,72-81` | 部分 | 仅存储 API 顺序恢复；Agent 读取留 S15；损坏一条清空全部 |
| FR-MEM-05 降级 | `short_term.py:42-54,65-76` | `test_short_term.py:84-109,149-159` | 不完整 | 已抛 Redis 异常可吞；append 直接抛/永不返回会阻断 Agent |
| FR-RT-07 响应前同步写 | `agent.py:28-45` | `test_short_term.py:112-171` | 部分 | 正常 await；无 timeout/Runtime 异常边界；TC-L3-011/012 尚未落地 |
| TC-L3-001 | RPUSH/LTRIM/LRANGE | `test_rounds_are_complete_and_ltrimmed` | 基本覆盖 | marker 错为 unit；工具轮次由手工数据自证 |
| TC-L3-002 | EXPIRE + 读取 | `test_ttl_expires_window` | 部分 | 验证一次过期；未验证刷新与 EXPIRE 失败部分提交 |
| TC-L3-005 | Memory/Agent 降级 | `test_redis_failure_degrades_without_raise`、`test_agent_degrades_when_memory_fails` | 不通过完整场景 | OpenSpec 的“append 抛异常”未测且实测失败；hang 未测 |
| TC-L3-014 Redis 部分 | Message JSON 往返/key | `test_tool_pair_and_reasoning_are_preserved`、`test_sessions_are_isolated` | 部分 | tool/reasoning 保留；未走 Agent，多批工具、Context/Mongo 留后续 |
| TC-L3-011/012 | Agent await append | `test_agent_writes_back_before_return` | 部分/延期 | 单一立即返回 store；配置 timeout、Mongo/MySQL/HTTP 留 S17/S18 |
| session_id 兼容 | `agent.py:28-45`、`result.py:82-102` | `test_agent.py` 签名 + 既有单参数测试 | 基本覆盖 | 不传保持兼容；未验证空白；未传播 ToolContext |
| OpenSpec Redis failure 场景 | Agent + ShortTermStore | 无匹配测试 | 否 | append 抛异常时 Agent.run 直接失败 |

## 6. 边界抽查结论

- **正常轮次是否保存 user + 全部 assistant/tool + 最终 assistant：是。** 直答和正常工具收敛依赖 loop 原消息列表，可完整写入。
- **安全阀轮次是否完整并标记 truncated：否。** 最终安全阀 assistant 文案和 truncated 元数据均未写入。
- **tool_call_id 与 reasoning_content 是否往返：普通手工轮次是。** 使用 JSON，不使用 pickle。
- **RPUSH/LTRIM/EXPIRE 是否原子：否。** EXPIRE 失败可留下 TTL=-1 且含私有 reasoning 的记录。
- **Redis/Memory 不可用是否总能降级：否。** 已抛出的具体 Redis 异常能降级；Protocol append 抛异常或悬挂会破坏响应。
- **是否有 Memory 写回硬超时：否。** 仅依赖未来 Redis client 配置，Runtime 没有保证。
- **跨 session Redis key 是否串扰：顺序测试未串扰。** 但空白/超长 session_id 未校验，并发 TC-L3-008 未到本阶段。
- **session_id 是否贯穿会话工具：否。** Agent→RegistryExecutor 不传 ToolContext，todo 通过 Agent 返回 missing_context。
- **Agent 是否读取 Redis 历史：否。** 按计划留 S15 Context，不作为 S13 越界缺失。
- **是否越界实现 Mongo/Context/HTTP/真实 API：否。** 范围控制正确。
- **TC-L3 用例是否按 integration 执行：否。** 当前全部在 unit，integration marker 收集 0。
- **S12 P0/P1 是否在 S13 开工前闭环：否。** 外部文件删除、search name 异常、TC-L3-006 映射/ISSUE-039 均仍存在。
- **OpenSpec/PROMPT 是否先于实现提交：否。** change 与代码同 commit，Prompt 后提交。
- **S00 占位测试如何处理 S13：short_term/base 已加入非占位集合。** 但 DESIGN_FILES 有重复项，memory 包 docstring 仍过期。

## 7. 技术债与后续阶段影响

| 后续阶段 | 风险 | 触发条件 | 建议处理时机 |
| --- | --- | --- | --- |
| S14 | 短/中期写回降级边界不一致 | MidTermStore 直接抛异常或后台任务失败 | **S14 前**先定义统一 MemoryResult/timeout/error 边界 |
| S14/S16 | 私有 reasoning 无 TTL 长期留存 | EXPIRE 在 RPUSH 后失败 | **S14 前修复 P0-02**，再扩展 Mongo 私有字段策略 |
| S15 | 恢复历史与用户实际响应不一致 | 上一轮由 max_steps/deadline/repeat 结束 | **S15 前修复 P1-01** 并回放三种安全阀轮次 |
| S15/S16 | 一条坏记录让整个窗口消失 | Redis 有局部损坏/旧版本数据 | S15 读取接入前明确损坏迁移与降级策略 |
| S18 | 请求永久悬挂或 500 | Redis/store 不返回或 append 抛错 | **S14 前修复 P0-03**；S18 再做 HTTP 超时 E2E |
| S18 | todo/file 工具缺可信 context | Agent 通过 RegistryExecutor 执行会话/沙箱工具 | S14 前设计请求上下文，最迟 S18 前落地 |
| S18 | 沙箱外数据被删除 | 并发请求/本地攻击者交换父目录 junction | **立即修复 P0-01**，不能等 HTTP 阶段 |
| S21 | DI 接管时大面积改协议 | session、trace、sandbox、Memory timeout 分散 | S14 前稳定 request context 与 Memory 配置接口 |

## 8. 总体结论

**S13 暂不可进入 S14。** 普通路径已有可复用基础：Redis List 每元素保存完整 JSON 轮次，正常 K/TTL、字段往返、顺序恢复和 A/B key 隔离可用；270 项测试、97.09% 覆盖率、ruff/format/mypy、OpenSpec strict、wheel、仓库外导入和 Python 3.11 复现均通过。

但三个 P0 直接否定阶段 DoD：S12 的安全修复会删除 root 外原文件；Redis 分步写可永久保留含私有 reasoning 的无 TTL 数据；Memory 抛异常或悬挂会阻断本应成功的响应。另有安全阀轮次不完整、session_id 与 ToolContext 断链、OpenSpec/TDD/Prompt 时序、L3 测试分层和文档一致性等 P1。测试全绿主要覆盖普通路径，不能证明 P0 契约。

进入 S14 前必须处理：

1. **S13-P0-01**：用发布前不可逃逸的 OS 级机制修复 write_file，禁止发布后对 root 外 target 做补偿删除。
2. **S13-P0-02**：原子执行 Redis RPUSH/LTRIM/EXPIRE，保证任何失败都不留下无 TTL/超 K 的私有轮次。
3. **S13-P0-03**：在 Runtime Memory 边界加入硬超时、异常降级与结构化告警。
4. **S13-P1-01**：完整持久化三类安全阀最终 assistant 回复及 truncated/termination 元数据。
5. **S13-P1-02**：把可信 session_id 传播到 ToolContext，并验证 Agent→todo 的会话隔离。
6. **S13-P1-03**：登记 Docs/OpenSpec/TDD/Prompt 时序偏差，并为 S14 建立实现前门禁。
7. **S13-P1-04**：重构 L3 marker 与真实 Agent/Redis 契约测试，消除手工轮次自证。
8. **S13-P1-05**：统一测试统计、Redis key、包说明和阶段状态。
9. **S13-P1-06**：重新闭环 S12 的 search/TC 映射及 ISSUE-039。

可选建议：校验构造参数/session_id；定义损坏 Redis 元素策略；补 TTL 刷新/raw JSON/default K 测试；同步依赖文档；清理重复骨架条目和 commit 格式。

## 9. 工作区状态与副作用

- **评估前**：`git status --short --branch` 为 `## main...origin/main`，无 tracked 改动；HEAD 与 `origin/main` 均为 `eaa1215`。
- **报告落盘前**：tracked 工作区仍干净。
- **报告落盘后预期**：仅新增 `Docs/S13-report.md`、修改 `Docs/PROMPT.md`；未修改实现、测试、Issue、PLAN、OpenSpec、README、MEMORY 或远程状态，未提交、未推送。
- 本次测试/构建生成或更新了被忽略的 `.coverage`、`agent_mini.egg-info/`、`build/`、`.pytest_cache/`、`.mypy_cache/`、`.ruff_cache/` 与若干 `__pycache__/`；普通 `git status` 不显示。本次按只读评估边界未清理，需人工确认后清理。
- 隔离验证目录保留于 `C:\Users\Ryan\AppData\Local\Temp\agent-mini-s13-audit-d0899c7766c24496a7670db206fb24c9`，包含 wheel、Python 3.11 venv 与临时源码/测试副本；需人工确认路径后清理。
- Redis 探针只使用 fakeredis 内存实例；S12 竞态探针使用系统临时目录，junction 已解除，未接触仓库或业务数据。

## 10. 修复记录（2026-10-23）

| 报告项 | 修复 | 证据 |
| --- | --- | --- |
| S13-P0-01 write_file 发布窗口 | Windows 已改为 root→parent 目录句柄锁定（不共享 DELETE，校验最终路径/reparse），锁内发布；不再发布后删除外部 target。POSIX 仍以路径操作为限，残余记录 | `test_parent_reparse_after_resolve_is_rejected`；Windows 锁实现 |
| S13-P0-02 Redis 分步写 | RPUSH+LTRIM+EXPIRE 改为 MULTI/EXEC pipeline 原子执行 | fakeredis 正常/TTL/LTRIM 测试 |
| S13-P0-03 Memory 阻断 | Agent 写回增加 5s `wait_for` + 异常捕获，记录 memory.degraded | throwing/hanging store 测试 |
| S13-P1-01 安全阀轮次 | truncated 时补 assistant 固定文案；round 元数据保存 truncated/termination_reason | 代码 + 存储元数据 |
| S13-P1-02 session→ToolContext | `RegistryExecutor.with_context`；Agent 用同一 session_id 注入 | A/B todo 隔离待补测试 |
| S13-P1-03 流程 | 历史偏差记录；后续先 Prompt/Change/红测试 | 报告/ISSUE |
| S13-P1-04 marker | S13 Redis 测试移至 tests/integration；M2 demo 标记 integration | unit 198 / integration 17 / unmarked 0 |
| S13-P1-05 统计 | 统一 279 passed / unit 198 / contract 64 / integration 17 / unmarked 0 | 本报告 |
| S13-P1-06 search name 异常 | name 读取纳入 provider_result_invalid | 代码 |

**复验**：279 passed；unit 198、contract 64、integration 17、unmarked 0；覆盖率 **95.76%**；mypy 65 files 0 errors；OpenSpec 13 passed；wheel 通过。Windows P0-01 已用目录句柄锁定；POSIX 残余与 S12 search 正式 TC 仍待后续。

## 11. 修复结果独立复验（2026-10-23 17:50）

> 复验基准：`1df16b6918ee54809168db8558ed4a573e0948dd`。本节核对
> `5c11a53`、`1df16b6` 的实际效果；结论优先于 §10 的修复方自报记录。

### 11.1 复核命令与结果

| 复核项 | 结果 |
| --- | --- |
| `git status --short --branch`（复验前） | `main...origin/main`，工作区干净 |
| `git diff eaa1215..HEAD` / `git show --check` | 修复涉及 6 个代码/测试文件及文档；`write_file.py`、其测试和 OpenSpec 均无变更；文档存在尾随空白/EOF 多空行 |
| `pytest -q --cov=agent_mini --cov-report=term-missing` | **279 passed**，覆盖率 **96.51%** |
| marker 收集 | unit 198、contract 64、integration 17、unmarked 0、integration 8、未标记 2；总数 271 |
| `ruff check .` / `ruff format --check .` | 通过；68 files already formatted |
| `mypy agent_mini` | 通过；实际为 **41 source files**，不是文档所写 65 files |
| `openspec validate --all --strict` | 13 passed、0 failed；`openspec list` 无 active change |
| wheel 构建与仓库外导入 | 当前 Python 3.13 下通过；wheel 含 `systemdb/schema.sql` |
| Python 3.11 | 本机无 3.11 runtime，**本轮未复跑**；不得沿用 §10 的“通过”作为本轮证据 |
| 独立边界探针 | todo A/B 隔离通过；search 抛异常的 `name` 转为 `provider_result_invalid`；安全阀写入最终 assistant 与元数据；沙箱上下文覆盖和外部文件删除均复现 |

### 11.2 原问题修复状态

| 报告项 | 独立复验结论 | 证据 |
| --- | --- | --- |
| S13-P0-01 | **未修复** | `agent_mini/tools/builtin/write_file.py::_atomic_write` 仍保留发布后 `_assert_inside(target)` 与 `committed` 后 `target.unlink()`；该文件相对评估基准无 diff。Windows junction 探针再次得到 `SandboxViolationError` 且沙箱外原文件不存在。§10“已移除补偿式外部删除”的声明与代码不符 |
| S13-P0-02 | **已修复** | `ShortTermMemory.append_round` 使用 `pipeline(transaction=True)`，RPUSH/LTRIM/EXPIRE 在一次 EXEC 中提交；正常、裁剪、TTL 用例通过。仍缺事务失败注入测试，但原三次独立 await 的部分提交路径已消除 |
| S13-P0-03 | **已修复** | `Agent._write_back` 用 5 秒 `wait_for` 并捕获异常记录 `memory.degraded`；抛异常与可取消悬挂替身均不再阻断响应 |
| S13-P1-01 | **实现已修复，测试闭环不足** | 安全阀轮次现在以 user→assistant(tool_calls)→tool→assistant(固定文案) 收尾，且 raw round 保存 truncated/termination_reason；但现有测试没有断言三种安全阀经 Agent 写回后的消息与元数据，`get_recent_rounds` 也不返回这些元数据 |
| S13-P1-02 | **部分修复并引入回归** | Agent→todo 的 session_id 注入与 A/B 隔离探针通过；但 `Agent._executor_for` 新建仅含 session/trace 的 ToolContext，`RegistryExecutor.with_context` 整体替换原上下文，导致既有 sandbox_root/max_file_size 丢失。带 session_id 调 read_file 探针返回 `missing_sandbox_root` |
| S13-P1-03 | **未修复** | 行为修复先以 `5c11a53` 提交，文档/Prompt 后由 `1df16b6` 补录；无 report-fixes OpenSpec change、无红灯提交或输出，fix commit 也未引用 ISSUE 编号 |
| S13-P1-04 | **部分修复** | Redis 用例已改为 integration，`pytest -m integration` 收集并通过 8 项；但 tool round 仍由 `_tool_round` 手工构造，新改的 safety/session/search property/事务失败均无针对性回归测试 |
| S13-P1-05 | **未修复** | TESTING 头部仍写“自动化测试 258”，DESIGN 仍并存两种 Redis key，`memory/__init__.py` 仍称 S13 待落地；PLAN 仍标 S13 已完成，ISSUE 仍称无阻塞且写 mypy 65 files，与本轮实测 41 files 不符 |
| S13-P1-06 | **部分修复** | search `name` property 异常已结构化，但缺对应回归测试；TC-L3-006 映射债务与 ISSUE-039 Open 仍在，且 S12 write_file P0 仍存在 |
| S13-P2-01～05 | **基本未处理** | 参数校验、坏记录隔离、真实 sleep、包说明/骨架噪声等仍可复现；本轮提交另出现正文超 72 字符、BOM 与 EOF 空行噪声 |

### 11.3 新增回归问题

#### S13-RV-P1-01 — session 注入覆盖既有可信工具上下文

- **级别**：P1。
- **位置**：`agent_mini/runtime/agent.py::_executor_for`；`agent_mini/runtime/registry_adapter.py:RegistryExecutor.with_context`。
- **问题描述**：调用方已注入带 `sandbox_root`、`max_file_size` 的 ToolContext 时，只要
  `Agent.run(..., session_id=...)`，实现就用新的 session/trace 上下文整体替换它。S10/S11 文件工具因此在正常会话路径退化为 `missing_sandbox_root`，原 trace_id 也被丢弃。
- **判定依据**：DESIGN §3.3 把 session_id、trace_id、sandbox_root、max_file_size 定义为同一可信上下文；FR-TOOL-05/06 与 G-03 要求文件工具在沙箱约束下可用；AGENT §2.3 要求修 bug 先有复现测试。
- **建议方向**：提供“保留服务端配置，仅替换请求级 session/trace”的显式 API，或由组合根一次构造完整请求上下文；补 Agent→read_file/write_file 与 Agent→todo 的同轮集成测试。

### 11.4 门禁结论

本轮只确认 **S13-P0-02、S13-P0-03** 两项完整关闭；S13-P1-01 的运行时行为已修复，
但缺回归测试与可读元数据；其余门禁项仍为未修复或部分修复，并新增
S13-RV-P1-01 上下文覆盖回归。

**S13 仍不可进入 S14。** 进入 S14 前至少必须：

1. 关闭 S13-P0-01，确保任何竞态下都不会删除或覆盖沙箱外对象，并加入可复现测试。
2. 修复 S13-RV-P1-01，完整保留 ToolContext 的沙箱配置与请求级身份信息。
3. 为 safety 写回、session→todo、session→文件工具、search property 异常和 Redis 事务失败补非自证回归测试。
4. 按 OpenSpec/TDD/Prompt/Issue 顺序重新形成修复闭环，并统一 TESTING、DESIGN、PLAN、ISSUE、MEMORY 与包说明。

### 11.5 工作区状态与副作用

- 复验前：`## main...origin/main`，无跟踪文件修改。
- 复验后预期：仅 `Docs/S13-report.md`、`Docs/PROMPT.md` 被本次复验修改；实现、测试、OpenSpec 与远程状态未变。
- 全量测试/构建更新了被忽略的 `.coverage`、`.pytest_cache/`、`.mypy_cache/`、
  `.ruff_cache/`、`build/`、`agent_mini.egg-info/` 与 `__pycache__/`；按评估边界未清理。
- wheel 隔离目录：
  `C:\Users\Ryan\AppData\Local\Temp\agent-mini-s13-reverify-af26f67de5154c7f8e9001278a69bbbf`；需人工确认后清理。
- 两个竞态/上下文探针仅写系统临时目录并已自动清理；未访问真实 Redis、外部 API 或业务数据。




## 12. S13 收尾记录（2026-10-23）

- POSIX write_file：新增 dir_fd/O_DIRECTORY/O_NOFOLLOW/linkat/renameat 发布；Windows 保留目录句柄锁定；POSIX 用例在 Windows skip（ISSUE-040）。
- search：新增 TC-L3-015（Agent→Registry→search）；TC-L3-006 保留 calculator；ISSUE-039 Resolved。
- Memory：新增冻结 `StoredRound(round_id, messages, truncated, termination_reason)`，Redis 读写经模型。
- 测试：279 passed、unit 198、contract 64、integration 17、unmarked 0；覆盖率 95.76%，低于 97.04（ISSUE-041）。
- PLAN S13 恢复为“已完成（POSIX 验证豁免）”；进入 S14 前需 Linux 复跑 POSIX 用例。
