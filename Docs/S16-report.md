# S16 阶段代码产出独立评估报告

> 评估时间：2026-10-24 00:00（Asia/Shanghai）  
> 评估基准：`4e12604..1d41999`；当前 `main`、`HEAD`、`origin/main` 均为 `1d41999`  
> 评估方式：独立只读复核；除本报告与 `Docs/PROMPT.md` 外，不修改实现、测试、OpenSpec 或远程状态  
> 结论：**不通过；S16 暂不可进入 S17，M3 尚未达成**  
> 修复状态：见 §11；P1 代码已处理，流程/覆盖率证据仍缺  
> 缺陷汇总：**P0 0 项、P1 3 项、P2 5 项、P3 1 项**

## 1. 评估范围与基准

本次以 S15 报告修复收口提交 `4e12604` 至 S16 归档提交 `1d41999` 为评估范围，共 17 个文件、`+539/-69`。重点复核：

- `Docs/REQUIREMENT.md`：FR-CTX-03/04、NFR-COST-01、AC-20。
- `Docs/DESIGN.md` §3.5、§5.3；`Docs/TESTING.md` 的 TC-L1-014/023/025/026/027、TC-L3-014。
- `Docs/PLAN.md` S16 与 M3 完成定义。
- OpenSpec `context-window` 主规范与归档 change `2026-10-23-s16-context-window`。
- `agent_mini/context/window.py`、`builder.py`、Runtime 每次出站前 fit、Memory 写回与 ContextTooLarge 失败路径。
- S16 新增测试、静态门禁、wheel、依赖与提交/归档流程。

组件级的轮次上限、token 上限、整轮删除、最小集合拒绝和每次出站前回调已经实现，现有自动化测试全部通过。但真实跨轮链路会把已恢复历史和 system prompt 再次写入新 StoredRound，连续三轮即出现 3→6→12 条消息增长；此外，fit 耗时绕过总 deadline，工具结果超限后的错误也无法携带既有 trace。三项均阻断 M3 与 S17 准入。

## 2. 复核命令与结果

| 命令 / 检查 | 结果 |
| --- | --- |
| `git diff --stat 4e12604..1d41999` | 17 files changed，539 insertions，69 deletions |
| `.venv\\Scripts\\python.exe -m pytest -q` | **312 passed，1 skipped**；skip 为继承的 POSIX-only 用例 |
| `pytest tests/integration/test_context_window.py -q` | **7 passed** |
| `pytest --cov=agent_mini --cov-report=term-missing -q` | **312 passed，1 skipped**；总计 1826 statements、74 missed，约 **95.95%**；window.py 99% |
| marker collect | unit 199（含 1 skip）、contract 64、integration 50、unmarked 0，共 313 collected |
| `ruff check .` | All checks passed |
| `ruff format --check .` | 72 files already formatted |
| `mypy agent_mini tests` | **69 source files，0 errors** |
| `openspec validate --all --strict` | **16 passed，0 failed**；engineering-standards 有既有长 Requirement INFO |
| `git diff --check 4e12604..1d41999` | **失败**：PLAN、TESTING、context-window spec 共 3 处 EOF 多空行 |
| `uv pip check --python .venv\\Scripts\\python.exe` | 42 packages compatible |
| `pip-audit --path .venv/Lib/site-packages` | No known vulnerabilities found；缓存写入有环境警告 |
| 禁用框架扫描 | pyproject 与 agent_mini 未命中被禁 Agent 框架 |
| `uv build --wheel` + wheel 内容检查 | 成功；wheel 含 window、builder、schema.sql，共 46 个文件 |

## 3. 维度结论

| 维度 | 结论 | 证据 |
| --- | --- | --- |
| 功能完整性 | **不通过** | 跨轮记忆写回污染，工具超限错误缺少既有 trace，M3 无法可靠演示 |
| 正确性 | **不通过** | `trim_reason=both` 被覆盖为 tokens；最初超限却报告 steps=1 |
| 可靠性 | **不通过** | Context fit 不受总 deadline 约束，超时后仍可调用 LLM |
| 测试与覆盖率 | **部分通过** | 全量绿且新增 window 覆盖率 99%，但关键 TC 仅名义映射，未覆盖真实跨轮/工具增长/日志/deadline |
| 可读性与架构 | **部分通过** | window 职责清晰，但出站上下文与当前轮持久化共用一个可变 messages 列表 |
| 安全与依赖 | **通过** | 无新增运行依赖、无禁用框架命中、依赖兼容且无已知漏洞 |
| 性能 | **部分通过** | 首次出站前重复 build+fit、重复读取 Memory；裁剪最多 100 轮，暂无无界循环 |
| 工程与流程 | **不通过** | diff-check 失败，OpenSpec/Prompt 均在代码后落盘，ISSUE 未更新，文档统计不一致 |

## 4. 分级问题清单

### P1-01 — 出站完整上下文被当作“当前轮”重新写回，历史呈倍增污染

- **位置**：`agent_mini/runtime/agent.py:103-124`，尤其 `StoredRound(..., tuple(messages))`；`agent_mini/context/builder.py:86-107`。
- **问题**：ContextBuilder 把 system、已恢复历史和当前轮装入 `messages`；React 循环结束后 Agent 又把整个列表写成一个新 StoredRound。下一轮会同时加载旧 StoredRound 和包含旧历史的新 StoredRound，按 round_id 去重无法消除嵌套内容。
- **边界证据**：使用真实 Agent→ContextBuilder→内存 ShortTermStore 连续运行 `first/second/third`，新轮消息数依次为 **3、6、12**；第三次 LLM 输入中的 `first` 出现 2 次。后续轮次继续放大，并重复 system/历史内容。
- **判定依据**：FR-MEM-01/02 要求 StoredRound 是单个完整轮次；FR-CTX-03 以轮为不可拆分裁剪单位；TC-L3-014 被列为 S16 回填项。当前数据既不是单轮，轮数与 token 统计也失真。
- **建议方向**：出站上下文与“本轮待写回消息”必须分离；持久化时只截取当前 user 及其 assistant/tool 往返，禁止写入 prefix 和已恢复历史。补至少三轮真实写回/恢复回归测试并断言每个 StoredRound 不含旧轮次和 system。

### P1-02 — Context fit 未纳入 Runtime 总 deadline

- **位置**：`agent_mini/runtime/loop.py:125-135`。
- **问题**：循环先计算 remaining，再在任何 `wait_for` 之外 await `context_fit`，且 fit 完成后不重算 remaining；因此 fit 可耗尽 deadline，随后仍使用旧 remaining 调用 LLM。
- **边界证据**：deadline=10ms、fit 睡眠 50ms、LLM 立即返回的探针得到 `reply=ok`、`truncated=False`、LLM calls=1，证明总截止时间已过仍出站。
- **判定依据**：FR-RT-05/TC-L1-029 的 deadline 是 Agent.run 全程总时限；S16 新增的出站前步骤不能绕过既有安全阀。
- **建议方向**：用当次剩余时间限时执行 fit，fit 后重新计算 remaining，再决定是否调用 LLM；超时应返回 deadline 截断结果且 LLM calls=0。

### P1-03 — 工具结果撑爆预算后丢失已执行步骤的 trace 与协议状态

- **位置**：`agent_mini/context/window.py:22-30`、`agent_mini/runtime/loop.py:125-135`。
- **问题**：第二次出站前 `context_fit` 抛出的 ContextTooLarge 直接越过 Runtime；异常仅有 code/http_status/steps/truncated，没有 trace、tool_traces 或已配对的消息状态，且 steps 固定默认 1。
- **边界证据**：首个 LLM 响应执行一次工具并产生 6000 字符结果后，第二次 fit 正确阻止了 LLM，但异常显示 LLM calls=1、tool calls=1、`has_trace=False`，属性仅为 `code/http_status/steps/truncated`。
- **判定依据**：Docs/DESIGN §3.5 明确要求已有工具时错误响应带脱敏 trace、steps、truncated 且不重放；TC-L1-027 明确覆盖该路径。当前调用方无法重建已经发生的工具副作用与 trace。
- **建议方向**：在 loop 内捕获并用当前 `_LoopState`、已配对 messages 和脱敏 tool traces 丰富错误契约，或返回统一结构化结果；同时覆盖“删历史后可继续”和“当前轮仍超限”两个分支，断言工具只执行一次。

### P2-01 — `trim_reason=both` 被后续单一触发覆盖

- **位置**：`agent_mini/context/window.py:70-79`；`tests/integration/test_context_window.py:73-77`。
- **问题**：reason 在每次删除时被覆盖。轮次与 token 最初同时超限、后续仅 token 超限时，最终返回 tokens，而不是累计语义 both；测试把断言放宽为 `{"both", "tokens"}`。
- **边界证据**：12 个宽轮次、budget=600 的探针返回 `rounds_before=12`、`rounds_after=0`、`dropped=12`、`trim_reason=tokens`、`tokens_before=6444`、`tokens_after=332`。
- **判定依据**：TC-L1-023 和 Docs/DESIGN 示例明确要求该两阶段场景为 both。
- **建议方向**：累计本次 fit 曾出现的触发原因，而不是保留最后一次原因；恢复精确断言。

### P2-02 — 裁剪日志分项不完整，超限拒绝日志缺失

- **位置**：`agent_mini/context/window.py:100-112`；对照 `Docs/DESIGN.md:352-353`、`Docs/TESTING.md:122`。
- **问题**：`context.trimmed` 未记录 message_tokens、tool_schema_tokens、protocol_overhead_tokens、budget；最小集合超限时直接抛错，没有要求的 `context.over_budget_after_trim`。
- **判定依据**：FR-CTX-04 要求裁剪分项可追溯，OpenSpec 要求 payload 与日志一致，TC-L1-026 明确断言 over_budget_after_trim。
- **建议方向**：统一从 TrimResult/错误快照生成日志字段，并为超限拒绝补结构化事件测试。

### P2-03 — 窗口 K 被硬编码，无法使用“默认 10”的配置语义

- **位置**：`agent_mini/context/window.py:14,72`、`FitInput:33-42`。
- **问题**：DEFAULT_MAX_ROUNDS=10 直接用于判断，FitInput/ContextBuilder 没有 max_rounds 参数。
- **判定依据**：PLAN S16 把窗口大小 K（默认 10）列为输入；“默认”意味着调用方可配置，而当前只能修改源码。
- **建议方向**：将 max_rounds 作为经校验的 FitInput/ContextBuilder 配置，保留 10 为默认值，补 K=0/1/自定义上限测试。

### P2-04 — S16 测试只覆盖组件 happy path，TC 映射名不副实

- **位置**：`tests/integration/test_context_window.py:1-154`。
- **问题**：文件声明覆盖 TC-L1-014/023/026/027、TC-L3-014，但 7 个用例没有覆盖工具结果增长后的第二次 fit、已有工具不重放、脱敏 trace、实际 tools Schema、over-budget 日志、跨轮写回恢复或 deadline；大部分为纯函数/Fake，却整体标为 integration。
- **判定依据**：这些遗漏直接让 P1-01/02/03 与 P2-02 未被测试发现；测试通过不能证明列出的 TC 已完成。
- **建议方向**：纯 fit 用例移到 unit；增加 Agent+Memory 三轮链路、工具增长两分支、Schema 超限、日志字段和 deadline 回归测试，按实际行为重新映射 TC。

### P2-05 — 阶段 DoD、文档和归档流程未闭环

- **位置**：提交 `5d0d1f0`、`7f68e84`、`1d41999`；`Docs/PLAN.md:355-359`、`Docs/TESTING.md:9-14`、`Docs/ISSUE.md`、S16 OpenSpec proposal/design/tasks。
- **问题**：`git diff --check` 有 3 处失败；TESTING 标题已到 S16，但正文仍写“截至 S14/301 个用例/最近 305 passed”；PLAN/TESTING 再次引入 BOM，package skeleton 重复登记 window；ISSUE 没有 S16 条目。S16 没有代码前的 OpenSpec change 提交，proposal/design/tasks 直到最终归档提交才出现；Prompt 在代码后提交；没有红测提交或证据；OpenSpec 缺回滚方式；提交描述仍为英文。
- **判定依据**：违反 AGENT.md 的 Docs First、TDD、Prompt、Issue、OpenSpec 与阶段五件套要求，以及用户全局契约的中文提交描述规则。
- **建议方向**：修复空白/BOM/重复清单和统计，补 ISSUE；后续阶段必须先提交 change、Prompt 与失败测试证据，再实现并归档，proposal/design 写明回滚方式。

### P3-01 — 首次 LLM 出站前重复构建和 fit

- **位置**：`agent_mini/runtime/agent.py:156-162`、`agent_mini/runtime/loop.py:125-133`。
- **问题**：Agent 先 `builder.build()` 完成一次 Memory 读取/裁剪，进入 loop 后在第一次 chat 前立即再次调用相同 fit，导致首次请求重复读取 Redis/Mongo、重复计数，并可能重复写 trimmed 日志。
- **建议方向**：让首次 payload 直接作为已 fit 快照，只有消息增长或下一出站步骤才重新 fit；或把首次构建统一移入 loop 的唯一入口。

## 5. 需求—实现—测试追溯

| 需求 / 用例 | 实现 | 自动化证据 | 结论 |
| --- | --- | --- | --- |
| FR-CTX-03 / TC-L1-014 | `fit_rounds` 按最旧 StoredRound 删除 | 12→10、完整四消息轮测试 | **组件级通过** |
| FR-CTX-03 / TC-L1-023 | 轮次/token 双触发 | 宽轮次测试允许 both 或 tokens | **部分满足**：最终预算满足，但 reason 错误且断言被放宽 |
| FR-CTX-03 / TC-L1-026 | fixed 超限抛 ContextTooLarge | 初始超限且 LLM calls=0 | **部分满足**：拒绝有效，但缺日志，零调用却 steps=1，未测大 system/Schema |
| FR-CTX-03 / TC-L1-027 | 每次出站前 fit | loop 回调已接入 | **不满足**：未测两分支；工具超限错误缺 trace；fit 绕过 deadline |
| FR-CTX-04 / TC-L1-014/025 | ContextPayload 分项与日志 | payload 字段测试 | **部分满足**：payload 有分项，日志字段不完整 |
| FR-MEM-01/02 / TC-L3-014 | StoredRound 历史恢复与私有字段 | S16 测试仅 Fake 读取 12 轮 | **不满足**：真实多轮写回嵌套历史并倍增 |
| NFR-COST-01 / AC-20 | 每次出站前预算复核 | 工具增长探针证实第二次 LLM 被阻止 | **核心预算阻断通过**，但错误契约不完整 |

## 6. 边界抽查

| 探针 | 结果 | 判定 |
| --- | --- | --- |
| 三次同 session 对话并真实写回/恢复 | StoredRound 长度 3→6→12；第三次 first 出现 2 次 | 失败 |
| deadline=10ms、fit=50ms | 仍调用 LLM 并返回正常结果 | 失败 |
| 12 轮同时触发 rounds+tokens | 最终 reason=tokens，不是 both | 失败 |
| 首次 LLM 后工具返回 6000 字符 | 第二次 LLM 被阻止、工具只执行一次，但异常无 trace | 部分通过 |
| 无历史最小集合超预算 | LLM calls=0，code/status/truncated 正确；steps=1 | 部分通过 |
| 12 轮且预算充足 | 保留最近 10 个完整 StoredRound | 通过 |
| wheel 内容 | window/builder/schema.sql 均存在 | 通过 |

## 7. 技术债与后续影响

1. P1-01 会让 Redis/Mongo 中的“轮次”失去原子语义，使 S17 的会话统计、审计和后续 HTTP 多轮功能建立在污染数据上；必须先修复再进入 S17。
2. P1-02 会破坏现有 Runtime 安全阀，任何新增出站前钩子都必须共享同一总 deadline。
3. P1-03 使已执行工具后的本地拒绝无法向上层提供完整脱敏状态，S18 无法按设计构造可靠 HTTP 错误响应。
4. hardcoded K 会在 S21 配置收口时迫使再次修改 Context API，宜在当前阶段解决。
5. 当前实测总覆盖率约 95.95%，文档记录 96.11%；window 新增代码覆盖率 99%，但行为覆盖缺口比行覆盖更关键。
6. S13 ISSUE-040 的 Linux/POSIX 验证仍为继承风险；本轮 Windows 评估未关闭该项。

## 8. 总体门禁结论

**S16 不通过，暂不可进入 S17；M3“有记忆有上下文”尚未达成。**

进入 S17 前至少必须：

1. 关闭 P1-01：只持久化当前完整轮次，完成三轮以上真实恢复回归。
2. 关闭 P1-02：把每次 Context fit 纳入同一总 deadline，并验证超时不出站。
3. 关闭 P1-03：为工具后超限保留脱敏 trace/steps/协议状态且不重放工具。
4. 修正 both 累计语义、over-budget/trimmed 日志与可配置 K，并补齐声明的 TC。
5. 修复 `git diff --check`、文档统计与阶段流程记录后，重新执行全量门禁。

本轮未发现新增依赖漏洞、禁用 Agent 框架、wheel 缺包或超预算请求继续出站；这些通过项不能抵消跨轮数据污染与安全阀回归。

## 9. 工作区状态与副作用

- 评估开始时工作区干净，`main` 与 `origin/main` 一致；未提交、未推送、未修改远程状态。
- 按只读评估边界，仅新增本报告并向 `Docs/PROMPT.md` 追加本次原始 Prompt 与摘要。
- 全量测试、覆盖率、Ruff、mypy、OpenSpec 与边界探针仅产生常规缓存；仓库跟踪文件未被这些命令修改。
- wheel 验证更新了被忽略的 `build/` 与 `agent_mini.egg-info/`；为避免删除评估前可能已存在的产物，未做破坏性清理。
- 外部临时目录 `C:\\Users\\Ryan\\AppData\\Local\\Temp\\agent-mini-s16-wheel-audit-20261024-0001` 留有本次 wheel 与目录内 `.gitignore`；不影响 Git 工作区。
- pip-audit 缓存目录写入失败警告不影响审计结果，未生成仓库内跟踪文件。


## 11. 修复记录（2026-10-24）

| 报告项 | 修复 | 证据 |
| --- | --- | --- |
| P1-01 历史倍增 | Agent 只持久化最后 user 起的当前轮，system/历史不写回 | `test_three_turns_store_only_current_round` |
| P1-02 fit 绕过 deadline | loop 用剩余时间 wait_for fit，fit 后重算 remaining | `test_fit_is_bounded_by_deadline` |
| P1-03 ContextTooLarge trace | 异常补 steps/trace/tool_traces；loop 在 fit 处填充后重抛 | 代码；工具分支未单独断言 |
| P2-01 trim_reason 覆盖 | 累计 rounds/tokens 触发，both 保留 | 精确 both 断言 |
| P2-02 日志分项 | context.trimmed 增加 message/tool/protocol/budget；超限 context.over_budget_after_trim | 代码 |
| P2-03 K 硬编码 | ContextBuilder/FitInput 增加 max_rounds，默认 10 | 代码 |
| P2-04 测试 | 新增三轮写回、deadline；纯 fit 仍 integration | 集成 52 passed |
| P2-05 文档/流程 | 统计/BOM/EOF/骨架修复；进度门禁记录 | 文档 |

**复验**：316 passed、1 skipped；unit 198、contract 64、integration 54、unmarked 0；覆盖率 **95.74%**；mypy 69 files 0 errors；OpenSpec 16 passed。


