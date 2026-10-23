# S14 阶段代码产出独立评估报告

> 评估时间：2026-10-23 22:24（Asia/Shanghai）  
> 基准提交：`62e434f`（`main` 与 `origin/main` 一致）  
> 评估方式：独立只读复核；除本报告与 `Docs/PROMPT.md` 记录外，不修改实现、测试、OpenSpec 或远程状态  
> 结论：**不通过；S14 暂不可进入 S15**  
> 修复状态：见 §10；代码 P0/P1 已处理，POSIX/流程豁免仍保留

## 1. 评估范围与基准

本次以 `d9cbd02..62e434f` 为 S14 变更范围，实际复核：

- `AGENT.md` §1–§10，重点检查文档优先、TDD、阶段准入、评估归档与提交规范。
- `Docs/REQUIREMENT.md` 的 FR-RT-07、FR-MEM-03/04/05、AC-07/21。
- `Docs/DESIGN.md` §3.2.2、§3.4、§5.4；`Docs/TESTING.md` 的 TC-L3-003/004/011/012/014；`Docs/PLAN.md` S14。
- `openspec/specs/mid-term-memory/spec.md` 与归档 change `2026-10-23-s14-memory-mongo-midterm`。
- `agent_mini/memory/base.py`、`mid_term.py`、`short_term.py`、`runtime/agent.py`、`runtime/loop.py`。
- `tests/integration/test_mid_term.py`、`tests/unit/test_package_skeleton.py`、`pyproject.toml`、README、MEMORY 与阶段记录。
- S14 四个提交：`9be69e5`、`b72a0fa`、`79e341b`、`62e434f`。

变更规模为 18 个文件、552 行新增、13 行删除；代码提交本身为 5 个文件、406 行变更，规模可审查。OpenSpec change 先于代码提交，但代码提交后才补录 Prompt 与完成文档。

## 2. 复核命令与结果

| 命令/检查 | 结果摘要 |
| --- | --- |
| `git status -sb`、`git rev-parse HEAD origin/main` | 评估前为干净的 `main...origin/main`；两者均为 `62e434f` |
| `git diff --stat/name-status d9cbd02..HEAD` | 18 个文件；新增 Mongo 存储、Agent 异步写回、9 个集成测试及文档/OpenSpec |
| `git log/show --format=fuller` | OpenSpec 提交先于代码 1 秒；Prompt/完成文档后于代码；feat 提交说明为英文，不符合仓库中文提交约定 |
| `git diff --check d9cbd02..HEAD` | **7 个文件存在 EOF 多余空行**，包括 DESIGN/ISSUE/PLAN/TESTING/README 与 OpenSpec 文件 |
| 初始 `uv run pytest -q` | **294 passed、1 skipped**，耗时 34.12s；但当时 `.venv` 仅安装运行依赖，实际 pytest/coverage 输出表明由 PATH 上的 Python 3.13.9 工具执行 |
| 初始 `uv run pytest -q --cov=agent_mini --cov-report=term --cov-fail-under=90` | **294 passed、1 skipped，95.91%**；coverage 明确显示 Python 3.13.9；`mid_term.py` 98%，`agent.py` 86% |
| 最终 Python 3.11.14 `.venv\\Scripts\\python.exe -m pytest -q` | **失败：287 passed、1 failed、1 skipped**；失败项为 `test_agent_mongo_failure_does_not_block`，告警在测试 teardown 才到达 |
| Python 3.11 单测重复复现 | 单独运行失败用例 **10/10 次失败**；固定 `sleep(0.01)` 未等到后台任务，证明测试和调度行为依赖运行器/时序 |
| marker 收集 | unit 199 collected（198 passed + 1 skipped）、contract 64、integration 32、e2e 0；总计 289 collected |
| `ruff check .` / `ruff format --check .` | 通过；70 files already formatted |
| `mypy agent_mini tests` | 通过；67 source files，0 errors |
| `openspec validate --all --strict` | **14 passed、0 failed**；engineering-standards 仅有既有 INFO |
| `uv pip check` | 16 个已安装包兼容，无依赖冲突 |
| `pip-audit` 扫描当前环境 | No known vulnerabilities found |
| PyMongo API 探针 | pymongo 4.19.0；`AsyncCollection` 的 find/create_index/index_information/insert_one 调用形态与实现兼容 |
| 短/中期 round_id 探针 | 同一 Agent 轮次在 Redis 与 Mongo 获得两个不同 UUID，`same_round_id=False` |
| 空 session 探针 | `append_round("")` 返回 True 并写入文档，但 `search_rounds("")` 固定返回空，形成不可检索孤儿数据 |
| 索引定义探针 | 已存在同名但仅含 `session_id` 的错误索引时，`ensure_indexes()` 返回 True，错误 key 未被识别 |
| 事件循环退出探针 | Agent 已返回 `reply=ok`，后台写尚未启动/完成；关闭事件循环后任务被取消，轮次未持久化 |

本次未执行：

- 未连接真实 MongoDB；仓库没有 Dockerfile/Compose 文件，README 虽提到可选 `docker compose`，但没有可执行编排入口。
- 未执行 HTTP 200 级 TC-L3-011/012；HTTP 属 S18，当前仅能验证 Agent 级异步行为。
- 未复跑 Linux POSIX 用例；ISSUE-040 仍为 Open，且其状态明确写着“S14 前”复跑。

## 3. 五维评估结论

| 维度 | 结论 | 证据 |
| --- | --- | --- |
| 正确性 | **不通过** | 正常写入、session 过滤、关键词、倒序和 reasoning 剥离可用；但后台写回在进程退出时无 drain/flush，已返回成功的轮次会丢失；空 session 可写不可查；错误同名索引被误判为有效 |
| 可读性与简洁性 | **有条件通过** | `MidTermMemory` 体量小、控制流清晰；但骨架列表把 `memory/mid_term.py` 重复三次，异常统一吞掉且缺少错误上下文 |
| 架构 | **不通过** | DESIGN 要求 `MidTermStore` Protocol，Runtime 却直接依赖具体 `MidTermMemory`；后台任务集合没有生命周期接口；短/中期未共享同一 StoredRound/round_id |
| 安全与隔离 | **有条件通过** | 查询强制带 session，关键词经 `re.escape`，公开读取剥离 reasoning；但 session_id 边界不一致，空 ID 产生不可治理数据，`include_private` 也尚无调用层授权边界 |
| 性能 | **有条件通过** | 复合索引目标合理，查询有默认 limit；但索引正确性未校验、limit 无上限、每请求直接 create_task 且无队列/背压，故障期任务数随请求速率增长 |
| 测试质量 | **不通过** | Python 3.11 最终全量门禁实际失败；TC-L3-003 的原始文档结构未测，TC-L3-014 未覆盖多批工具往返/call_id，Mongo timeout、shutdown 丢写、错误索引、空 session 均漏测 |
| 依赖与分发 | **有条件通过** | pymongo/mongomock 选型合规、无禁用 Agent 框架、当前审计无已知漏洞；未复核真实 Mongo，README 的开发依赖清单未列 fakeredis/mongomock |
| 文档与流程 | **不通过** | OpenSpec strict 通过；但 DESIGN §3.4、§5.4、TESTING 与实现采用两套文档模型，S13 前置门禁未闭环，Prompt/TDD/中文提交要求未满足 |

## 4. 问题清单

### P0

#### S14-P0-01 — 已返回成功的 Mongo 写回在进程退出时可直接丢失

- **位置**：`agent_mini/runtime/agent.py:41,67-76,119-132`；`tests/integration/test_mid_term.py:209-222`。
- **问题描述**：Agent 用 `asyncio.create_task` 启动写回并保存在私有 `_background` 集合中，但没有公开的 `drain/close`、关闭钩子或持久化队列。测试只在返回后手工释放任务，未覆盖服务关闭。确定性探针在 `Agent.run` 返回成功后立即结束事件循环，后台任务被取消，Mongo 没有写入。
- **判定依据**：FR-MEM-03 是 P0 持久化要求；FR-RT-07/AC-21 要求中期异步写回，而不是静默放弃。DESIGN §3.4 又声明服务无状态、状态应落存储。正常滚动发布、测试进程结束或事件循环关闭均可触发该窗口。
- **建议方向**：引入受生命周期管理的后台写入器/队列，提供 `async drain()` 与 `async close()`，由后续 HTTP lifespan 在 shutdown 阶段限时等待；明确超时后的告警与剩余任务数。先补“返回后立即关闭/优雅关闭”红测试，再改实现。

### P1

#### S14-P1-01 — Mongo 文档模型与主设计、测试设计直接冲突

- **位置**：`Docs/DESIGN.md:323-327,464-472`；`Docs/TESTING.md:274`；`agent_mini/memory/mid_term.py:75-95`；`tests/integration/test_mid_term.py:71-79`。
- **问题描述**：DESIGN §3.4 和 TC-L3-003 定义集合 `messages`，每条消息一份文档，字段直接包含 `role/content/created_at`；§5.4 与 S14 OpenSpec 后来改成集合 `conversation_rounds`，一个 StoredRound 文档内嵌 `messages[]`。实现采用后一种，但没有修订前一套权威设计。测试名声称 TC-L3-003，却只写入一个两消息轮次并通过 API 取回一轮，没有断言“3 条消息 → 3 个文档”和原定字段。
- **判定依据**：AGENT §1/§7 要求需求→设计→测试→实现单向一致；当前 `insert_many`/`insert_one`、集合名和文档字段均互相矛盾，不能由测试全绿证明选型正确。
- **建议方向**：先明确并只保留一种模型。若坚持 StoredRound 文档，应先同步 DESIGN §3.4/§5.4、TC-L3-003 与迁移/查询语义，再补 raw collection 结构测试；若遵循既有消息文档设计，则实现需按消息批量写入并在读取时按 round_id 组装。

#### S14-P1-02 — 同一逻辑轮次在 Redis 与 Mongo 使用不同 round_id

- **位置**：`agent_mini/runtime/agent.py:65-74,103-110`；`agent_mini/memory/base.py:9-16`。
- **问题描述**：短时写回在 `_write_back` 内生成一个 UUID，中期写回随后再生成另一个 UUID。实测同一请求得到两个不同 ID。`StoredRound` 因而没有真正成为跨存储的唯一轮次契约，后续无法可靠关联、去重、回放或排查同一轮次。
- **判定依据**：S14 Prompt/OpenSpec 明确“复用 StoredRound”；DESIGN §3.4 的 Redis/Mongo 文档都包含 round_id。一个逻辑轮次应在写往不同介质前只构造一次。
- **建议方向**：Agent 在单一收口点生成一个 `StoredRound`，同一对象或同一 round_id 同时交给短期与中期存储；相应收敛 `ShortTermStore.append_round` 接口，并补跨存储 ID 相等测试。

#### S14-P1-03 — session_id 校验不一致，可写入不可检索的孤儿文档

- **位置**：`agent_mini/memory/mid_term.py:75-116`；`agent_mini/memory/short_term.py:49-50,121-122`；`agent_mini/runtime/agent.py:65-78`。
- **问题描述**：MidTermMemory 写入不校验 session；搜索拒绝空白 session。探针显示空 ID 写入成功且文档计数增加，但任何公开搜索都返回空。Redis 则拒绝空白及超过 128 字符的 ID，导致同一请求在两种存储中行为分裂。
- **判定依据**：FR-MEM-03/04 要求按会话持久化与检索；不可检索记录既不是有效会话数据，也无法通过正常 API 治理。
- **建议方向**：把 session 校验提升为共享函数/值对象，在 Agent 边界一次拒绝非法 ID，Redis/Mongo 防御性复用；补空白、超长和仅空格的写入/读取测试。

#### S14-P1-04 — “幂等索引”只检查名称，不验证键定义

- **位置**：`agent_mini/memory/mid_term.py:60-73`；`tests/integration/test_mid_term.py:127-133`。
- **问题描述**：`ensure_indexes` 只要发现 `session_created_desc` 名称就返回 True。探针预建同名但仅含 `session_id` 的索引后，方法仍返回 True，实际 key 仍错误，时间倒序查询失去预期索引保障。现有测试只验证重复调用与名称存在。
- **判定依据**：OpenSpec MUST 创建 `(session_id, created_at desc)`；“同名”不等于“同定义”。部署中旧索引、手工误建或历史版本都可能触发。
- **建议方向**：比较现有索引的 `key` 与目标定义；不一致时返回失败并记录可诊断告警，或通过显式迁移处理，不能静默声称成功。补同名异构索引测试。

#### S14-P1-05 — Runtime 绕过 MidTermStore 抽象并缺少统一生命周期契约

- **位置**：`Docs/DESIGN.md:321-327`；`agent_mini/memory/base.py:19-39`；`agent_mini/runtime/agent.py:12-13,39-47`。
- **问题描述**：DESIGN 明确要求 `ShortTermStore / MidTermStore` 两个 Protocol，但 base 只定义 ShortTermStore，Agent 直接 import/标注具体 `MidTermMemory`。测试只能大量 `cast(Any, ...)` 注入替身。后台 drain/close 也没有可替换契约。
- **判定依据**：依赖方向虽允许 Runtime→Memory，但项目设计要求存储实现可替换；具体类耦合会把 Mongo 驱动和生命周期细节带入 Runtime，并使 S15/S18/S21 组合根继续依赖私有实现。
- **建议方向**：在 `memory/base.py` 定义最小 `MidTermStore` Protocol（append，必要时 lifecycle）；Agent 仅依赖协议，Mongo 类实现协议。测试替身应在 mypy 下无需 `Any` cast。

#### S14-P1-06 — 异步降级测试在 Python 3.11 稳定失败，且 TC-L3-003/014 存在关键覆盖空洞

- **位置**：`tests/integration/test_mid_term.py:57-111,150-222`；`Docs/TESTING.md:274-285`。
- **问题描述**：Agent 失败测试靠 `sleep(0.01)` 等后台日志，没有确定性完成信号。在项目声明支持的 Python 3.11.14 环境中，单项 10/10 次失败，全量得到 287 passed、1 failed、1 skipped；日志直到 pytest teardown 才出现。初始 294 passed 来自 PATH 上 Python 3.13.9 的工具运行，因调度差异掩盖竞态。此外，Mongo reasoning 测试只有 user→assistant 两条消息，不含 TC-L3-014 要求的多批 assistant(tool_calls)→tool 往返和 call_id；TC-L3-003 不检查 raw 文档数量/字段；Mongo timeout、取消、shutdown、空 session、错误索引与并发顺序均未覆盖。
- **判定依据**：AGENT §1.3/§2 要求验收标准与测试一一对应、可重复且能抓回归；README 声明 Python 3.11+，故最低版本必须通过。当前 95.91% 是 Python 3.13 的覆盖率证据，不能替代 Python 3.11 的失败门禁。
- **建议方向**：使用可等待的后台任务句柄、事件或 `drain()` 做条件同步，禁止固定 sleep；把 raw collection、完整工具轮次、timeout/cancel/shutdown、非法 session 与错误索引加入 L3，并在 Python 3.11/3.13 矩阵复跑。

#### S14-P1-07 — 阶段前置门禁与开发流程未闭环

- **位置**：`Docs/S13-report.md:11.4,12`；`Docs/ISSUE.md:495-508`；提交 `9be69e5..62e434f`；`Docs/PROMPT.md:2032-2047`。
- **问题描述**：S13 收尾明确要求进入 S14 前在 Linux 复跑 POSIX 用例，ISSUE-040 仍 Open；ISSUE-041 也写着 S14 前补测或维持豁免。S14 仍被标为完成。S14 OpenSpec 虽先提交，但其后 1 秒即提交测试+实现，仓库无红灯证据；原始 Prompt 与完成记录在代码后补。feat 提交说明为英文，也不符合全局中文提交约定。
- **判定依据**：AGENT §1、§2、§3、§5、§8 明确要求前置阶段 DoD、红→绿、Prompt 时机、中文 Conventional Commits 与阶段五件套。
- **建议方向**：不改写已推送历史；如实把 S14 状态改为评估不通过，先关闭/明确豁免 S13 门禁。后续修复按 Prompt/Issue→OpenSpec→红测试→实现→验证→归档顺序形成可审计提交。

### P2

#### S14-P2-01 — 文档、包说明与测试统计未完全收口

- **位置**：`agent_mini/memory/__init__.py:1`；`Docs/DESIGN.md:469,572-574`；`Docs/TESTING.md:9-14`；`README.md:15-33`。
- **问题描述**：memory 包仍称 S13–S14 待落地；DESIGN 流程图仍写 Mongo `insert_many`，变更记录缺 S14；TESTING 的设计总数 78 与分项 33+10+15+12+6+3=79 不一致；README 开发依赖说明漏列 fakeredis/mongomock，也没有 `pytest -m integration` 命令。
- **建议方向**：在行为模型确定后一次同步所有权威文档、包 docstring、测试统计与真实命令，避免在 §5.4 追加补丁句而保留旧规格。

#### S14-P2-02 — 机械噪声降低评审质量

- **位置**：`tests/unit/test_package_skeleton.py:47-64`；S14 文档 diff。
- **问题描述**：`DESIGN_FILES` 中 `memory/mid_term.py` 出现三次；7 个文件被引入 EOF 多空行，TESTING 还新增 BOM。它们不改变业务行为，但说明重构/收口阶段未执行 `git diff --check` 与重复项检查。
- **建议方向**：去重骨架列表，移除无意义 BOM/EOF 空行；把 `git diff --check` 纳入提交前门禁。

## 5. 需求—实现—测试追溯

| 需求/验收 | 实现 | 当前测试 | 结论 |
| --- | --- | --- | --- |
| FR-MEM-03 / TC-L3-003：Mongo 持久化 | `MidTermMemory.append_round` | `test_write_and_query_session` | **部分**：API 往返可用；原测试设计的 raw 文档结构/数量未覆盖，shutdown 可丢写 |
| FR-MEM-04 / TC-L3-004：session + 倒序 + 关键词 | `search_rounds` | keyword/order、A/B isolation | **基本通过**：普通路径正确；limit、非法 session、索引定义异常未覆盖 |
| FR-MEM-05：存储失败降级 | 三个存储方法吞异常；Agent `_write_mongo` 捕获异常/超时 | broken collection、failing store | **部分**：已抛异常不阻断；timeout/cancel/shutdown 未形成可靠持久化保证 |
| FR-RT-07 / AC-21：Redis 同步、Mongo 异步 | Agent 先 await `_write_back`，后 create_task | async slow store | **部分**：调用顺序成立；无生命周期收口，正常关闭丢写 |
| TC-L3-014：完整工具轮次与私有 reasoning | Message JSON 编解码、公开剥离 reasoning | 简化 user→assistant round | **不足**：未覆盖多批工具、tool_call_id、无孤立 tool 和 Agent→Mongo 完整链路 |
| OpenSpec：正确复合索引 | `ensure_indexes` | 同名重复调用 | **不足**：未验证 key 定义，错误同名索引被接受 |

## 6. 边界抽查

- **普通直答**：Agent 生成 user/assistant 完整轮次，Mongo 替身可写可读，公开模式剥离 reasoning。
- **工具消息**：序列化代码理论上保留 Message 全字段，但本阶段没有 Mongo 侧多批工具往返回归证据。
- **安全阀**：S13 已补最终 assistant/truncated 元数据；S14 直接复制 messages/元数据，未单独走 Agent→Mongo 测试。
- **跨会话**：A/B 普通检索隔离通过；空白 session 是例外，会被写入但不可检索。
- **关键词**：`re.escape` 阻断正则注入，且只匹配 `messages.content`，不会按 reasoning 命中。
- **失败/超时**：连接异常降级通过；Mongo 卡住的 timeout 分支未由测试验证；事件循环关闭会取消未完成任务。
- **索引**：正常创建与同定义重复调用通过；同名异构索引失败。
- **真实驱动**：API 形态与 pymongo 4.19.0 兼容；未连接 MongoDB ≥6 做真实 BSON/索引/查询验证。

## 7. 技术债与后续影响

| 后续阶段 | 风险 | 建议处理时机 |
| --- | --- | --- |
| S15 Context | 两套 Mongo 文档模型会让 ContextBuilder 的读取接口和粒度无法稳定 | **S15 前**确定唯一模型并同步设计/测试 |
| S15/S16 恢复与裁剪 | Redis/Mongo round_id 不同，难以去重与关联同一轮次 | **S15 前**统一 StoredRound 构造与 ID |
| S18 HTTP | 服务 shutdown 会取消 Mongo 写回；无公开 drain/lifespan 接口 | **S18 前，最好 S14 内**建立生命周期协议 |
| S18 鉴权 | `include_private=True` 是普通布尔参数，尚无授权边界 | HTTP 接入时禁止直接暴露，需服务端可信调用 |
| S20 可观测性 | `memory.degraded` 不含异常类型、timeout 标记、未完成任务数 | S14 修复时补最小结构化字段，S20 再统一 |
| S21 DI | Runtime 直接依赖 MidTermMemory，组合根会被具体 Mongo 类型绑死 | **S15 前**补 MidTermStore Protocol |

## 8. 总体结论

S14 的普通路径已经具备可用雏形：官方 PyMongo 异步 API、StoredRound JSON、session/关键词查询、时间倒序、reasoning 公开隔离与异常降级均有实现；Python 3.13 初始运行曾得到 294 passed、95.91% 覆盖率，ruff/format/mypy、OpenSpec 和依赖审计也通过。但最终按项目最低版本 Python 3.11.14 复跑为 287 passed、1 failed、1 skipped，阶段测试门禁本身不可重复。

但阶段仍不满足准出条件。P0 的后台任务生命周期缺口会在正常关闭窗口丢失已返回成功的持久化轮次；P1 还包括 Mongo 数据模型与主设计/TC 直接冲突、跨存储 round_id 分裂、空 session 孤儿数据、索引定义误判、缺失 MidTermStore 抽象、关键 L3 场景漏测及前置/流程门禁未闭环。

**结论：S14 不通过，暂不可进入 S15。** 至少需要：

1. 为 Mongo 后台写回建立可验证的 drain/close 生命周期，并补退出窗口回归测试。
2. 选定并统一 Mongo 文档模型，修订 DESIGN/TESTING/OpenSpec/实现中的冲突。
3. 单次构造 StoredRound，让 Redis/Mongo 共用 round_id。
4. 统一 session 校验并校验完整索引定义。
5. 引入 MidTermStore Protocol，补 TC-L3-003/014、timeout/cancel/shutdown 的真实契约测试。
6. 关闭或明确豁免 S13 前置门禁，并按仓库流程形成修复闭环。

## 9. 工作区状态与副作用

- **评估前**：`git status --short --branch` 为 `## main...origin/main`，无 tracked/untracked 改动；HEAD 与 `origin/main` 均为 `62e434f`。
- **报告落盘后预期**：仅新增 `Docs/S14-report.md`、修改 `Docs/PROMPT.md`；未修改实现、测试、Issue、PLAN、OpenSpec、README、MEMORY 或远程状态，未提交、未推送。
- 首次 `uv run` 在仓库创建了被忽略的 `.venv/`，当时只安装运行依赖，命令从 PATH 调用了 Python 3.13.9 的测试工具；随后以 `--extra dev` 把测试依赖安装到 Python 3.11.14 `.venv` 并完成最低版本复验。期间生成未跟踪 `uv.lock`，已在最终交付前删除；`.venv/` 因涉及递归删除按安全规则保留并如实记录。
- 测试更新了被忽略的 `.coverage`、`.pytest_cache/`、`.mypy_cache/`、`.ruff_cache/`、`agent_mini.egg-info/` 与 `__pycache__/`；未清理。
- `pip-audit` 通过 `uvx` 下载临时审计环境并写用户缓存；报告出现一次跨盘缓存写警告，不影响审计结果。
- 所有 Mongo 边界探针均使用内存替身；未启动 Docker、未访问真实数据库、未写业务数据、未调用外部 API。

## 10. 修复记录（2026-10-23）

| 报告项 | 修复 | 证据 |
| --- | --- | --- |
| S14-P0-01 | Agent 新增 `drain()`/`close()`，限时等待后台 Mongo 任务；超时记录剩余任务数 | `test_agent_mongo_failure_does_not_block`、shutdown drain |
| S14-P1-01 | DESIGN §3.4/§5.4、TC-L3-003 统一为 `conversation_rounds` 一轮一文档；新增 raw document 测试 | `test_full_tool_round_raw_document` |
| S14-P1-02 | Agent 单点构造一个 StoredRound，Redis/Mongo 共享 round_id | `test_round_id_is_shared_across_stores` |
| S14-P1-03 | `valid_session_id` 下沉 base；Agent/Redis/Mongo 共用；非法 ID 拒绝 | `test_agent_rejects_invalid_session` |
| S14-P1-04 | 索引同时校验 key 定义；同名异构返回 False + `memory.index_conflict` | `test_index_same_name_different_key_is_rejected` |
| S14-P1-05 | base 新增 `MidTermStore` Protocol；Agent 只依赖协议 | mypy 67 files 0 errors |
| S14-P1-06 | 失败/超时测试改用 `drain()` 同步；补完整 tool_calls/tool_call_id/reasoning raw 测试 | 集成 32 passed |
| S14-P1-07 | 历史流程偏差记录；S13 POSIX 豁免仍 Open | ISSUE-040/041 |
| S14-P2-01 | 包说明、DESIGN、TESTING 统计同步；README 依赖/命令待补 | 文档 |

**复验**：294 passed、1 skipped；unit 198、contract 64、integration 32、unmarked 0；覆盖率 **95.79%**（S13 基线 95.76%）；mypy 67 files 0 errors；OpenSpec 14 passed；wheel 通过。


