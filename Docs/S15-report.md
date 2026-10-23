# S15 阶段代码产出独立评估报告

> 评估时间：2026-10-23 23:21（Asia/Shanghai）  
> 评估基准：`5964581..4a84b1f`；当前 `main`、`HEAD`、`origin/main` 均为 `4a84b1f`  
> 评估方式：独立只读复核；除本报告与 `Docs/PROMPT.md` 外，不修改实现、测试、OpenSpec 或远程状态  
> 结论：**不通过；S15 暂不可进入 S16**  
> 修复状态：见 §10；代码 P1 已处理，流程/Python3.11 证据仍缺  
> 缺陷汇总：**P0 0 项、P1 3 项、P2 5 项、P3 1 项**

## 1. 评估范围与基准

本次以 S14 修复完成提交 `5964581` 至 S15 归档提交 `4a84b1f` 为评估范围，共 21 个文件、`+666/-15`。重点复核：

- `Docs/REQUIREMENT.md`：FR-CTX-01/02、NFR-COST-01、AC-20。
- `Docs/DESIGN.md` §3.5、`Docs/TESTING.md` 的 TC-L1-013/022/025 与 TC-L3-007、`Docs/PLAN.md` S15。
- OpenSpec `context-builder` 主规范与归档 change `2026-10-23-s15-context-builder`。
- `agent_mini/context/builder.py`、`token_counter.py`、Memory 协议增量、Runtime/LLM 实际出站路径。
- S15 新增测试、依赖、构建产物、提交顺序与文档回填。

S15 的组件级主体已形成：固定顺序拼接、规范 JSON 计数、预算公式、tiktoken 降级、StoredRound 读取以及 wheel 打包均有实现。但当前产物尚未接入真实 LLM 出站路径，且所谓“同一快照”是可变列表别名，计数结果可在发送前失效，因此不满足本阶段最关键的验收语义。

## 2. 复核命令与结果

| 命令 / 检查 | 结果 |
| --- | --- |
| `git diff --stat 5964581..4a84b1f` | 21 files changed，666 insertions，15 deletions |
| `.venv\\Scripts\\python.exe -VV` | Python 3.11.14，满足 Python 3.11+ |
| `.venv\\Scripts\\python.exe -m pytest -q` | **301 passed，1 skipped**；skip 为继承的 POSIX-only 用例 |
| `pytest tests/integration/test_context_builder.py -q` | **7 passed** |
| `pytest --collect-only -q` | 302 tests collected |
| `coverage report -m` | 总覆盖率 **95.24%（显示为 95%）**；builder 90%，token_counter 96% |
| `ruff check .` | **失败**：`tests/unit/test_package_skeleton.py:148` 的 EOF 多余空行 |
| `ruff format --check .` | **失败并触发 Ruff panic**；逐文件隔离后唯一触发文件为 `tests/unit/test_package_skeleton.py`，S15 同时引入 UTF-8 BOM 与异常 EOF |
| `mypy agent_mini tests` | **68 source files，0 errors** |
| `openspec validate --all --strict` | **15 passed，0 failed** |
| `git diff --check 5964581..4a84b1f` | **失败**：9 处尾随空白/EOF 多空行问题 |
| `uv pip check --python .venv\\Scripts\\python.exe` | 42 packages compatible |
| `pip-audit --path .venv/Lib/site-packages` | No known vulnerabilities found；缓存写入有环境警告，不影响审计结果 |
| `uv build --wheel` + wheel 内容检查 | 成功；wheel 含 builder、token_counter、schema.sql，共 46 个文件 |
| `rg "ContextBuilder|ContextPayload|BuildRequest" agent_mini tests` | 除定义外仅测试引用；Runtime/LLM 出站链路无引用 |

## 3. 维度结论

| 维度 | 结论 | 证据 |
| --- | --- | --- |
| 功能完整性 | **不通过** | ContextBuilder 未接入 Agent/React/LLM 出站路径，FR-CTX-01/02 对真实对话不生效 |
| 正确性与边界 | **不通过** | 工具快照可变、去重不完整、Memory 读取可无限挂起、thinking 序列化口径不一致 |
| 测试与覆盖率 | **部分通过** | 全量绿且新增模块覆盖率 >80%，但关键 TC 未按设计验证真实发送、禁用工具与无重复 |
| 静态质量 | **不通过** | Ruff lint 失败、format panic、diff-check 失败 |
| 类型与构建 | **通过** | mypy 0 errors；Python 3.11 wheel 构建和内容检查通过 |
| 依赖与安全 | **通过** | 仅新增 tiktoken；依赖兼容，未发现已知漏洞，未引入禁用 Agent 框架 |
| 文档与流程 | **不通过** | DESIGN 被转义破坏，验收记录与实测不一致，Prompt/提交语言/回滚记录不符合契约 |

## 4. 分级问题清单

### P1-01 — Context 管线未接入实际 LLM 出站路径

- **位置**：`agent_mini/runtime/agent.py:85-92`、`agent_mini/runtime/loop.py:109-148`；对比 `agent_mini/context/builder.py:63-88`。
- **问题**：`Agent.run()` 仍只构造当前 `user` 消息；React 循环直接取得 `tool_executor.schemas()` 并调用 `llm_client.chat()`。全仓搜索表明 ContextBuilder 仅被 S15 测试引用，短时/中期历史、token 计数和预算均不会影响真实请求。
- **判定依据**：PLAN S15 明确要求“计数与发送复用相同快照”；FR-CTX-01/02 为 P0 需求；TC-L1-025 要求捕获 HTTP 发送体。当前仅交付孤立组件，真实链路无法满足验收。
- **建议方向**：在出站链路中注入并调用 ContextBuilder，以一次捕获的工具快照同时构建、计数和发送；S16 再在该唯一出站入口加入每步 `fit`/裁剪。若团队确实计划延后到 S18，必须先修订 PLAN、TC 与阶段完成状态，不能按现有基线宣称 S15 完成。

### P1-02 — 可变 tools_snapshot 使“计数与发送同一快照”失效

- **位置**：`agent_mini/context/builder.py:28,42,80-83`；`tests/integration/test_context_builder.py:119-127`；`openspec/specs/context-builder/spec.md:10`。
- **问题**：BuildRequest 与 ContextPayload 都保存调用方原始 `list`；计数后调用方追加/修改工具会同步改变 payload，但 token 分项不会重算。测试还把对象身份相同写成强制断言，固化了风险。
- **边界证据**：用 1 字符=1 token 的确定性编码器构建后，再向原列表追加 5000 字符 Schema，得到 `snapshot_same_object=True`、快照长度从 1 变 2、已记录估算 405、实际重算 5516。
- **判定依据**：计数结果不再描述待发送 payload，违反 FR-CTX-02、NFR-COST-01、AC-20 与 TC-L1-025。
- **建议方向**：修订 OpenSpec 的“原引用”决策，建立不可变快照（例如 tuple/冻结 DTO 或已规范化请求体）；计数器与发送器消费同一个不可变对象，而不是共享可变容器别名。

### P1-03 — Memory 读取无超时，可令核心对话永久挂起

- **位置**：`agent_mini/context/builder.py:112-124`。
- **问题**：异常会降级，但 `mid_term.get_rounds()` 与 `short_term.get_recent_rounds()` 都被直接 await；若存储端不返回，则异常处理永远不会执行，Context 构建和对话请求一起挂起。
- **边界证据**：注入永不返回的 ShortTermStore 后，外层 50ms 探针只能超时，ContextBuilder 无内部超时或降级日志。
- **判定依据**：Memory 不可用应降级继续，不能使核心对话链路不可用；与既有 Runtime 写回的限时降级策略也不一致。
- **建议方向**：增加可配置读取超时，分别包裹两类存储读取；单个存储超时后记录 `context.degraded` 并继续使用另一来源与当前输入。

### P2-01 — round_id 去重只覆盖跨存储首层场景

- **位置**：`agent_mini/context/builder.py:111-124`。
- **问题**：`seen` 只由 mid_term 初始结果构造，既不消除 mid_term 内部重复，也不在追加 short_term 结果时更新，short_term 内部重复也会全部进入消息。
- **边界证据**：同一 StoredRound 在 mid_term 返回两次时，输出角色为 `user, assistant, user, assistant, user`，历史 user 出现 2 次。
- **判定依据**：归档 design 声明按 round_id 去重，TC-L3-007 明确要求“顺序正确且无重复”。
- **建议方向**：按遍历顺序维护并即时更新 seen，稳定去重两个来源中的所有 round_id；补同源重复、跨源重复和顺序测试。

### P2-02 — TokenCounter 与 HttpLLMClient 的 reasoning 序列化口径不同

- **位置**：`agent_mini/context/token_counter.py:60`、`agent_mini/llm/client.py:185-191`。
- **问题**：计数器固定 `include_reasoning=True`，发送器则根据 `self._thinking` 决定。thinking 关闭时，计数输入不是实际 HTTP messages。
- **边界证据**：含长 reasoning 的消息在探针中计数序列化长度 1609，而 thinking=false 的实际发送序列化长度为 163。
- **判定依据**：虽然当前差异偏保守，但 S16 会据此产生错误裁剪或误报 ContextTooLarge，仍违反“实际请求计数”的可追溯语义。
- **建议方向**：将 thinking/序列化模式纳入统一请求快照，让计数和 HttpLLMClient 复用同一 provider payload。

### P2-03 — 关键测试未覆盖其声明的验收行为

- **位置**：`tests/integration/test_context_builder.py:19,89-210`；`Docs/TESTING.md:106,118,121,278`。
- **问题**：7 个测试全部使用内存 Fake，却整体标为 integration；TC-L1-025 没有捕获 HTTP 请求体、禁用工具或触发历史裁剪，只断言计数器收到同一可变 list；TC-L3-007 未验证无重复；TC-L1-013 文档要求 `tokens_after/trim_reason`，而 S15 OpenSpec 明确不提供这些字段。
- **判定依据**：需求—实现—测试映射存在空洞，测试全绿不能证明阶段验收成立。
- **建议方向**：拆分 unit/contract/integration 标记；增加 HttpLLMClient 请求体捕获、不可变快照、禁用工具过滤、同源/跨源去重、读取失败/超时及 thinking on/off 测试；统一 TC-L1-013 与 S15/S16 的字段边界。

### P2-04 — 静态门禁和文档完整性失败

- **位置**：`tests/unit/test_package_skeleton.py:1,148`；`Docs/DESIGN.md:285-286,315-318,322-323,382-385`；另见 `git diff --check` 列出的多个 EOF 问题。
- **问题**：Ruff lint 失败，format 对 S15 改写后的 package_skeleton 文件发生 panic；DESIGN 中 `name`、`number_overflow`、`now_provider`、`not_configured` 等被错误拆行，数据库表字段也被破坏；9 个文件存在空白门禁错误。
- **判定依据**：Docs/TESTING 准出要求 Ruff 零告警且文档与实现一致；归档 tasks 却把“全量/覆盖率/静态”标为已完成。
- **建议方向**：恢复被转义破坏的文本，移除意外 BOM/EOF 噪声和重复空行，重新执行 ruff lint/format 与 `git diff --check`，再修正验收记录。

### P2-05 — 文档优先、Prompt 与提交规范证据不足

- **位置**：提交 `1caec9d`、`1c015b0`、`210c98c`；归档 proposal/design；`Docs/PROMPT.md` S15 条目。
- **问题**：计划提交与代码提交仅相隔 1 秒，代码提交后才落 Prompt/完成文档；OpenSpec 未提供 AGENT.md 要求的回滚方式；S15 提交标题和正文使用英文，不符合本轮用户全局契约的中文提交描述要求；仓库没有可复核的红测执行证据。
- **判定依据**：AGENT.md §1–§3 要求文档评审先于编码、文档四要素齐全、Prompt 在提交前记录；用户全局契约要求提交信息中文。
- **建议方向**：后续 change 在编码前完成可评审文档与 Prompt 记录，写明回滚方案并保存红测证据；提交信息按当前全局契约使用中文描述。

### P3-01 — 包骨架清单重复且引入无意义编码噪声

- **位置**：`tests/unit/test_package_skeleton.py:52-62`。
- **问题**：builder/token_counter 在 DESIGN_FILES 中重复出现多次，S15 同时给文件增加 BOM；存在性测试仍会通过，降低清单可维护性并诱发格式器问题。
- **建议方向**：清单去重并统一 UTF-8 无 BOM。

## 5. 需求—实现—测试追溯

| 需求 / 用例 | 实现 | 自动化证据 | 结论 |
| --- | --- | --- | --- |
| FR-CTX-01 / TC-L1-013 | ContextBuilder 固定顺序组装 | 5 轮顺序测试通过 | **部分满足**：组件顺序正确，但真实 Agent 不使用；TC 字段边界冲突 |
| FR-CTX-01 / TC-L3-007 | Mid/Short StoredRound 合并 | 仅验证单一 mid 来源 | **部分满足**：无重复要求未覆盖且可复现失败 |
| FR-CTX-02 / TC-L1-022 | TokenCounter、预算公式、降级 | 预算、空输入、降级测试通过 | **组件级通过**：公式与分项正确 |
| FR-CTX-02 / TC-L1-025 | tools Schema 计数、快照复用 | 仅验证 list 身份与描述增长 | **不满足**：未捕获 HTTP body，快照可变，禁用工具未验证 |
| NFR-COST-01 / AC-20 | 设计要求每次出站前检查 | Runtime 无调用点 | **不满足** |
| OpenSpec ContextBuilder | StoredRound、规范 JSON、降级 | OpenSpec strict 通过 | **规范自洽但不完整**：把“原引用”固化为错误设计，未覆盖真实发送与读取超时 |

## 6. 边界抽查

| 探针 | 结果 | 判定 |
| --- | --- | --- |
| 构建后原地追加超长工具 Schema | 405 的旧计数对应 5516 的新 payload；`stale=True` | 失败 |
| mid_term 返回重复 round_id | 同一历史轮次被展开两次 | 失败 |
| thinking=false 且历史含 reasoning | 计数序列化 1609，实际发送序列化 163 | 失败 |
| ShortTermStore 永不返回 | ContextBuilder 无内部超时，外层探针超时 | 失败 |
| max_context=16000、max_output=1024 | budget=13376 | 通过 |
| tokenizer 加载失败 | 字符降级仍统计 Schema 并记录 degraded | 通过 |
| wheel 内容 | builder/token_counter/schema.sql 均存在 | 通过 |

## 7. 技术债与后续影响

1. S16 的裁剪与 ContextTooLarge 依赖“不可变且与发送完全一致的请求快照”；P1-01/P1-02 未修复前继续实现，会把错误边界放大到所有 LLM 步骤。
2. 无读取超时会让接入 Memory 后的真实请求出现无上限尾延迟，不能依赖异常降级覆盖挂起场景。
3. reasoning 序列化差异会在 S16 形成不必要的历史丢弃或本地拒绝，应在引入裁剪前统一。
4. 当前 95.24% 总覆盖率低于文档记录的 95.42%，也低于 S14 的 95.79%；新增模块虽超过 80%，但全局回退应被如实记录并解释。
5. S13 ISSUE-040 的 Linux/POSIX 验证仍为继承风险，本次 Windows 评估未关闭该项。

## 8. 总体门禁结论

**S15 不通过，暂不可进入 S16。**

进入 S16 前至少必须：

1. 关闭 P1-01：把 ContextBuilder/TokenCounter 接入现有真实出站路径，或先正式修订阶段边界与验收映射。
2. 关闭 P1-02：以不可变请求快照保证计数和发送完全同源。
3. 关闭 P1-03：为 Memory 读取增加限时降级。
4. 补齐 TC-L1-025/TC-L3-007 的真实发送、禁用工具、去重和挂起测试。
5. 修复 Ruff、`git diff --check` 与 DESIGN 损坏，重新执行全量门禁并更新不实的“已完成”记录。

本轮未发现 P0、安全越界、已知依赖漏洞或打包缺失；这些通过项不能抵消核心链路和强制门禁失败。

## 9. 工作区状态与副作用

- 评估开始时工作区干净，`main` 与 `origin/main` 一致；未提交、未推送、未修改远程状态。
- 按只读评估边界，仅新增本报告并向 `Docs/PROMPT.md` 追加本次原始 Prompt 与摘要。
- `uv sync --extra dev` 使用/更新了被忽略的 `.venv/`，并生成过未跟踪 `uv.lock`；该 lock 已由评估方移除。
- wheel 验证更新了被忽略的 `build/` 与 `agent_mini.egg-info/`；因无法确认它们在评估前是否已存在，未做破坏性清理。
- 外部临时目录 `C:\\Users\\Ryan\\AppData\\Local\\Temp\\agent-mini-s15-wheel-audit-20261023-2301` 留有本次 wheel 与目录内 `.gitignore`；不影响仓库工作区。
- pip-audit 报告缓存目录写入失败警告；未产生仓库内文件。


## 10. 修复记录（2026-10-23）

| 报告项 | 修复 | 证据 |
| --- | --- | --- |
| P1-01 Context 未接出站 | Agent 新增 `with_context`，一次 `schemas()` 构建，loop 使用同一 tools_snapshot | `test_agent_uses_builder_snapshot_for_llm` |
| P1-02 可变 snapshot | `ContextPayload.tools_snapshot` 改为 tuple；Builder 规范化一次；调用方后续修改原列表不影响 payload | `test_tools_snapshot_identity_and_budget` |
| P1-03 读取无超时 | `ContextBuilder(read_timeout_seconds=1.0)` 分别 wait_for 两类存储；超时 `context.degraded` | `test_memory_read_timeout_degrades` |
| P2-01 去重 | `seen` 即时更新，mid/short 同源/跨源重复均消除 | `test_duplicate_round_ids_are_removed` |
| P2-02 reasoning 口径 | `TokenCounter.count_request(include_reasoning=...)` 与 BuildRequest 透传 | `test_reasoning_serialization_toggle` |
| P2-03 测试空洞 | 补 Agent→LLM snapshot、超时、去重、reasoning；原 L3 用例仍 integration | 集成 43 passed |
| P2-04 静态/文档 | 修正 EOF/空白、DESIGN 转义、骨架重复；ruff/mypy 通过 | `ruff check .`、`mypy` |
| P3-01 骨架噪声 | DESIGN_FILES 去重，context 模块单次列出 | 骨架测试通过 |
| P2-05 流程 | 历史偏差保留记录，不改写已推送提交 | ISSUE/PROMPT |

**复验**：305 passed、1 skipped；unit 198、contract 64、integration 43、unmarked 0；覆盖率 **95.93%**；mypy 68 files 0 errors；OpenSpec 15 passed；wheel 通过。

