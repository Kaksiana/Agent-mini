# S09 代码产出独立评估报告

> 评估时间：2026-10-23 13:30（Asia/Shanghai）  
> 基准提交：`9252738`（`main` 与 `origin/main` 一致）  
> 评估方式：只读复核；除本报告与 `Docs/PROMPT.md` 记录外，不修改实现、测试、OpenSpec 或远程状态  
> 修复状态：见 §10；S09 已恢复准入

## 1. 评估范围与基准

| 类别 | 实际读取范围 | 评估基准 |
| --- | --- | --- |
| 阶段计划 | `Docs/PLAN.md:149-158,335-349` | S09 仅交付 todo，会话内增删查改、空集合、可信 `session_id` 注入 |
| 功能需求 | `Docs/REQUIREMENT.md:103-108,152,188-199,286-297` | FR-TOOL-04、AC-06/16/17、工具结构化错误与会话隔离 |
| 设计契约 | `Docs/DESIGN.md:300-317,319-326,348-354` | Registry 执行边界、`ToolContext`、todo 存储/id/隔离语义、S13/S18 边界 |
| 测试定义 | `Docs/TESTING.md:88-105,219-245` | TC-L1-006、TC-L3-013 及 S09 覆盖边界 |
| 全局规范 | `AGENT.md` 全文；`openspec/specs/engineering-standards/spec.md` | Docs First、TDD、目录、错误、依赖、提交、OpenSpec 与报告归档 |
| 过程记录 | `Docs/PROMPT.md:1605-1657`、`Docs/ISSUE.md:420-447`、`MEMORY.md:3-16`、`README.md:1-3` | S08 前置修复闭环、S09 Prompt/TDD/验收声明 |
| 实现与测试 | `agent_mini/tools/builtin/todo.py`、`agent_mini/tools/registry.py`、`tests/unit/test_todo_tool.py`、`tests/unit/test_package_skeleton.py` | 真实 Schema、Registry、CRUD、隔离、错误和分发行为 |
| OpenSpec | `openspec/specs/todo-tool/spec.md`、`openspec/specs/tool-registry/spec.md`、归档 change `2026-10-23-s09-tool-todo` | 主规格与归档 change 的一致性、严格校验和流程顺序 |
| 提交历史 | `1c63de7`、`e1dcb13`、`7447ec9`、`9252738` | change 先行、实现与测试同提交、文档收口、最终归档 |

### 1.1 基准间的一致性与缺口

- `PLAN`、`REQUIREMENT`、`DESIGN` 与 todo 主规格对可信上下文、会话隔离、1-based 稳定 id、空列表及 S13 替换方向基本一致。
- `PLAN` 的输出只列 `todo.py`，实际还必须扩展 `registry.py` 才能注入 `ToolContext`；S09 原 Prompt 与 change design 已显式批准该最小扩展，因此不判为越界，但 `PLAN` 的输出清单不完整。
- `TESTING` 的 TC-L1-006 写“第二次返回 1 项”，而 OpenSpec 与实现把 `complete(1)` 解释为保留两项并将第一项标为 done；正式验收口径互相冲突。
- TC-L3-013 同时要求 A/B 各自 complete、伪造参数无副作用以及历史不泄漏；S09 覆盖边界却把该 TC 标为已覆盖，仅把 HTTP/真实 API 留给 S18，没有说明“历史”应由 S13/S18 回填。

## 2. 复核命令与结果

| 命令/探针 | 关键结果 | 判定 |
| --- | --- | --- |
| `git status --short --branch`、`git rev-parse HEAD/origin/main` | 评估前为 `## main...origin/main`，两者均为 `9252738` | 通过 |
| `git log/show/diff` 核对 S09 四个提交 | `1c63de7` 规划 → `e1dcb13` 代码+测试 → `7447ec9` 文档 → `9252738` 归档 | 通过 |
| `python -m pytest -m unit -q` | 123 passed，64 deselected | 通过 |
| `python -m pytest -m contract -q` | 64 passed，123 deselected，37.86s | 通过 |
| `python -m pytest -q --cov=agent_mini --cov-report=term-missing --cov-fail-under=80` | 187 passed；总覆盖率 96.24%；`todo.py` 99% | 通过 |
| `python -m ruff check .` | All checks passed | 通过 |
| `python -m ruff format --check .` | 60 files already formatted | 通过 |
| `python -m mypy agent_mini tests` | 57 source files，0 errors | 通过 |
| `openspec validate --all --strict` | 8 passed，0 failed；工程规范有长 Requirement 的 Info | 通过 |
| `openspec list` / `openspec list --specs` | 无活跃 change；todo-tool 主规格存在，3 项 Requirement | 通过 |
| `python -m pip check` | No broken requirements found | 通过 |
| `pip wheel` → 全新 venv 安装 → 仓库外导入/执行 | wheel 安装成功；从 site-packages 导入 todo；Registry add 成功；`pip check` 通过 | 通过 |
| wheel ZIP 清单探针 | 含 `agent_mini/tools/builtin/todo.py` 与 `agent_mini/systemdb/schema.sql` | 通过 |
| 完整 Schema 字符串探针 | `schema_contains_session_id=True`，来源为 `TodoArgs` 描述 | **失败** |
| Registry 非法 action 探针 | `{"action":"bogus"}` 返回 `invalid_arguments`，不是已声明的 `invalid_action` | **失败** |
| Registry index 类型探针 | `True`、`"1"`、`1.0` 均被接受为 id 1；与生成 Schema 的 integer 类型不一致 | **失败** |
| 伪造 add 副作用探针 | 携带 `session_id` 返回 `invalid_arguments`；随后可信会话仍为空 | 通过；现有测试未覆盖此副作用断言 |
| Store 别名探针 | 修改 `list_items()` 返回元素会同步修改存储内对象 | 技术债 |
| 禁用项/skip/xfail 扫描 | S09 文件无 `noqa`、`type: ignore`、调试残留、skip/xfail、危险执行 | 通过 |
| `git diff --check 1c63de7^..9252738` | 5 个文档文件新增 EOF 空行；不影响运行 | P2 |

本次已复跑 S09 声明的 unit、contract、全量、覆盖率、Ruff、format、mypy、OpenSpec、wheel、隔离安装与仓库外导入。未调用真实模型/API；TC-L4-009/010 按阶段计划留 S18，未复跑。

## 3. 维度结论表

| 维度 | 结论 | 一句话理由 | 证据位置 |
| --- | --- | --- | --- |
| 需求与范围合规 | 有条件通过 | 只实现 todo 与必要 Registry 注入，未越界到沙箱/Memory/HTTP；但 `PLAN` 输出未列 Registry 改动，TC 分阶段边界不完整 | `PLAN:149-158`；归档 design；提交 `e1dcb13` |
| 可信上下文与协议契约 | 不通过 | 顶层 properties 没有 `session_id`，但完整模型 Schema 的 description 明文包含它 | `todo.py:20-25`；`registry.py:79-85`；S09-P1-01 |
| CRUD、序号与隔离 | 有条件通过 | add/list/complete/delete、空集合、稳定 id 与基本 A/B 隔离有效；正式 TC 的计数/跨会话 complete 口径未闭合 | `todo.py:61-166`；`test_todo_tool.py:25-90`；S09-P1-04/05 |
| 错误边界 | 不通过 | 真实 Registry 路径吞掉领域 `invalid_action`，且 lax int 接受 Schema 非法类型 | `todo.py:17,121-159`；`registry.py:125-130`；S09-P1-02/03 |
| 数据模型与可替换性 | 有条件通过 | Protocol 与稳定 id 可承接 S13，但全局具体 store 被硬编码，返回元素也不是快照 | `todo.py:28-113`；S09-P2-01/02 |
| 测试质量与 TDD | 不通过 | 11 个用例均通过且实现/测试同提交，但完整 Schema、真实错误码、类型、伪造副作用与 TC-L3-013 均有漏测 | `test_todo_tool.py:25-126`；S09-P1-01～05 |
| 全局代码规范 | 有条件通过 | Ruff/format/mypy、复杂度、中文 docstring、导入均过；测试目录、commit body 与文档尾空行有 P2 | 工具输出；S09-P2-03/04 |
| 打包与分发 | 通过 | wheel 含 todo 与 schema.sql，全新 venv 可安装、仓库外导入和执行 | wheel/venv 探针；`pyproject.toml` |
| 依赖审计 | 通过 | S09 未新增依赖；无禁用 Agent 框架，当前环境与全新安装 `pip check` 均通过 | `pyproject.toml:11-24`；禁用依赖扫描 |
| 流程与文档闭环 | 有条件通过 | OpenSpec 先行、代码测试同提交、最后归档；但文档宣称与真实 Schema/错误路径不符，红灯仅有摘要 | Git 历史；`PROMPT:1650-1657`；`ISSUE:441-447` |
| 可复现性 | 通过 | 全量门禁和隔离 wheel 安装均可复现，不依赖仓库源码导入 | 本报告 §2 |
| 后续阶段影响 | 有条件通过 | S10 可独立实现，但按阶段 DoD 仍应先修 P1；S13/S18 会直接放大上下文、并发与状态替换缺口 | 本报告 §7 |

## 4. 问题清单

### P0

无。伪造 `session_id` 在 Registry 白名单处会被拒绝，定向副作用探针也证明 handler 未执行；当前未发现可直接越权读取其他会话的路径。

### P1

#### S09-P1-01 — 完整模型 Schema 仍暴露 `session_id`

- **位置**：`agent_mini/tools/builtin/todo.py:20-25`（`TodoArgs`）；`agent_mini/tools/registry.py:79-85`（`ToolSpec.to_json_schema`）；`tests/unit/test_todo_tool.py:120-126`
- **问题描述**：`TodoArgs` docstring 包含 `session_id`，pydantic 将它写入根 `description`。现有测试只检查 `parameters.properties`，因此通过；对完整 Schema 序列化后实际可见 `session_id`。这与“模型 Schema MUST NOT 含 session_id”直接冲突。
- **判定依据**：`Docs/PLAN.md:156`；`Docs/REQUIREMENT.md:195`；`Docs/DESIGN.md:306,314`；`openspec/specs/todo-tool/spec.md:22-29`；S09 原 Prompt 约束 4。
- **建议方向**：从模型可见描述中移除该名称，或显式定制公开 Schema；测试必须对完整 Schema 递归/序列化断言，而非只看 properties。

#### S09-P1-02 — `invalid_action` 在真实 Registry 路径不可达

- **位置**：`agent_mini/tools/builtin/todo.py:17,121-136`；`agent_mini/tools/registry.py:125-130,143-159`；`tests/unit/test_todo_tool.py:64-80`
- **问题描述**：`TodoArgs.action` 使用 `Literal`，非法 action 在 handler 前被 pydantic 归为 `invalid_arguments`；测试却直接调用 handler 并断言 `invalid_action`。因此文档公布的领域错误码只在非生产直调路径成立。
- **判定依据**：归档 change `design.md` 的错误码决策；`openspec/specs/todo-tool/spec.md:31-38`；`MEMORY.md:7`；S09 Prompt 约束 7；工程规范测试不得自证。
- **建议方向**：统一 Registry 与 handler 的错误映射；要么在 Registry 校验前保留领域判别，要么正式把非法枚举定义为 `invalid_arguments` 并同步规格，随后用 `DEFAULT_REGISTRY.execute` 固化真实路径。

#### S09-P1-03 — `index` 使用宽松强制转换，接受 Schema 声明之外的类型

- **位置**：`agent_mini/tools/builtin/todo.py:20-25,145-159`；`agent_mini/tools/registry.py:125-130`；`tests/unit/test_todo_tool.py:64-80`
- **问题描述**：生成的 JSON Schema 声明 `index` 为 integer，但 pydantic 默认宽松模式把 `true`、`"1"`、`1.0` 转为 1 并完成待办。现有测试只覆盖 0/99，未覆盖类型错误。
- **判定依据**：S09 Prompt 约束 7 明确要求类型错误转为结构化错误；`DESIGN.md:304-305` 要求 Schema/执行契约一致；工程规范要求边界测试覆盖非法输入。
- **建议方向**：将 index 设为严格整数并明确 bool/字符串/浮点策略；通过 Registry 增加类型负例，断言无状态副作用。

#### S09-P1-04 — TC-L1-006 的正式预期自相矛盾，测试规避了关键计数断言

- **位置**：`Docs/TESTING.md:99,219-226`；`openspec/specs/todo-tool/spec.md:12-15`；`tests/unit/test_todo_tool.py:25-37`
- **问题描述**：TC-L1-006 要求 complete 后第二次 list “返回 1 项”，OpenSpec 和实现则保留两项、第一项 done。测试只断言第一/第二项状态，没有断言第二次列表长度，无法裁决正式 TC 与实现谁正确。
- **判定依据**：`AGENT.md` §1/§7 要求验收标准与测试一一映射、文档与实现同步；FR-TOOL-04 的 CRUD 语义必须无歧义。
- **建议方向**：先确定 complete 是“标记完成”还是“从活动列表移除”，统一 TESTING/OpenSpec/DESIGN；再对第二次列表长度和完整内容做精确断言。

#### S09-P1-05 — TC-L3-013 被标为已覆盖，但隔离与无副作用断言不完整

- **位置**：`Docs/TESTING.md:219-225,244`；`tests/unit/test_todo_tool.py:40-48,93-117`
- **问题描述**：正式 TC 要求 A/B 分别 add/list/complete，并验证 B 的待办与历史不泄漏给 A；当前只做 A/B add/list，complete 仅在另一个单会话用例出现。伪造测试调用的是无副作用 list，即使 handler 被误执行也不可观察；历史能力尚不存在，却未在覆盖边界中明确延后。
- **判定依据**：TC-L3-013 完整定义；`AGENT.md` §1/§2/§7；todo 主规格伪造场景明确要求“不执行 todo”。
- **建议方向**：伪造请求改用可观察的 add 并验证 A/B 均未新增；补 A/B 独立 complete 后的状态断言；把“历史隔离”明确拆到 S13/S18，避免把部分覆盖标为整条完成。

### P2

#### S09-P2-01 — Store 返回的列表仍共享可变 `TodoItem`

- **位置**：`agent_mini/tools/builtin/todo.py:28-34,75-77`
- **问题描述**：`list_items()` 只复制 list，元素仍是存储内部的可变对象；调用方修改返回项即可绕过 complete/delete 改写状态。定向探针把返回项 content 改为 `mutated` 后，下一次读取同步变更。
- **判定依据**：`TodoStore` 是面向 S13 的复用边界；全局规范要求公共数据契约避免隐藏副作用。
- **建议方向**：返回冻结值对象或深拷贝快照，并增加“读取结果不可反向修改存储”的测试。

#### S09-P2-02 — `TodoStore` Protocol 没有形成实际注入点

- **位置**：`agent_mini/tools/builtin/todo.py:37-59,108-142`
- **问题描述**：handler 直接引用模块级具体 `_STORE`，Protocol 未用于构造器/工厂/参数边界；`reset_todo_store()` 也作为生产模块公共函数服务测试。S13 替换时仍需改动工具实现与全局状态。
- **判定依据**：归档 change 声明 S13 用 Memory KV 替换；工程规范依赖注入与 Protocol 条款；`DESIGN.md:314,319-326`。
- **建议方向**：S13 接入前建立显式 store 注入/绑定点，把测试清理由 fixture 所有的实例承担，避免模块级跨测试/跨请求共享控制函数。

#### S09-P2-03 — 上下文注入只按参数名判定，缺少注册期契约校验

- **位置**：`agent_mini/tools/registry.py:162-171`
- **问题描述**：任意 handler 只要存在名为 `context` 的参数就会被覆盖注入；注册阶段不验证它是否为 `ToolContext`，也不阻止 params_model 自身声明同名业务字段。后续新增工具可能发生静默覆盖或类型错配。
- **判定依据**：`DESIGN.md:303-306` 的统一注册/可信上下文契约；NFR-MAINT-01；工程规范要求注册边界校验公共契约。
- **建议方向**：注册时验证上下文参数的名称、位置、注解与 Schema 排斥关系，或采用显式的 context-aware handler 元数据，而非每次调用临时猜测。

#### S09-P2-04 — 测试目录、提交正文与 Markdown 尾部格式未完全符合全局规范

- **位置**：`tests/unit/test_todo_tool.py`；提交 `e1dcb13`、`7447ec9`；`Docs/ISSUE.md`、`Docs/PLAN.md`、`Docs/PROMPT.md`、`Docs/TESTING.md`、`MEMORY.md` 的 S09 diff
- **问题描述**：新增测试仍平铺在 `tests/unit/`，没有按模块镜像；两个 commit body 单行分别为 122/77 字符，超过 72；`git diff --check` 报 5 个文件新增 EOF 空行。
- **判定依据**：工程规范 D-03 与目录表；`AGENT.md:206-212`；通用 diff 清洁要求。
- **建议方向**：后续按 `tests/unit/tools/builtin/` 组织新增测试，commit body 手工换行；文档编辑时保持单个结尾换行。不要为纯历史格式问题改写已推送提交。

### Info

#### S09-INFO-01 — 非线程安全和进程内丢失是已接受的阶段边界

- **位置**：`todo.py:61-66`；归档 change design；`DESIGN.md:314`
- **观察**：当前 Runtime 在单轮内按序执行 tool_calls，但未来同 session 的并发 HTTP 请求可同时进入线程池；当前实现已明确不保证并发安全并把替换时点定在 S13。
- **建议**：S13 在共享存储中采用原子操作/版本控制，并用同 session 并发请求补测；不要把当前内存行为带入 S18。

#### S09-INFO-02 — TDD 红灯只有摘要，无法由提交历史独立回放

- **位置**：`Docs/PROMPT.md:1650-1657`；提交 `e1dcb13`
- **观察**：记录称 11 个用例因占位实现在 setup 阶段先红后绿；最终测试与实现同 commit，符合仓库同提交要求，但未保留可复跑红态或逐用例输出。本次不把摘要等同于独立证据。
- **建议**：后续 Prompt 至少记录红灯命令、失败节点与预期红因；无需改写历史。

#### S09-INFO-03 — S08 阻塞项已在 S09 开工前闭环

- **位置**：提交 `16105eb` → `b2c19ce` → `2074a3e` → `079c2db`；`Docs/S08-report.md` §10
- **观察**：S08 报告修复使用独立 change，规划、实现/测试、文档、归档顺序正确，S09 开工点晚于归档；不再构成 S09 前置阻塞。

## 5. 需求—实现—测试追溯表

| FR / TC | 需求摘要 | 实现位置 | 测试位置 | 覆盖 | 越界/缺口 |
| --- | --- | --- | --- | --- | --- |
| FR-TOOL-04 | 会话级 CRUD；可信上下文；不可模型覆盖 | `todo.py:61-166`；`registry.py:113-171` | `test_todo_tool.py` | 部分 | 完整 Schema 泄露字段名；严格类型与 Registry 错误码不一致 |
| TC-L1-006 | add a/b、list、complete(1)、再 list | `todo`、`MemoryTodoStore` | `test_add_list_complete_same_session` | 部分 | TESTING 的“第二次 1 项”与实现冲突；测试未断言长度 |
| TC-L3-013 | A/B 独立 add/list/complete；伪造 session；待办/历史均隔离 | Registry context 注入、session 分区 | `test_sessions_are_isolated`、`test_registry_injects_context_and_rejects_forged_session`、Schema 测试 | 部分 | 无跨会话 complete；伪造无副作用断言不可观察；历史应延后但未拆分；完整 Schema 断言失真 |
| TC-L4-009 | HTTP 双窗口 todo 交替恢复 | 未实现 | 未实现 | 否 | 正确留 S18 |
| TC-L4-010 | HTTP 工具追问引用前文 | 未实现 | 未实现 | 否 | 正确留 S18 |

## 6. 边界抽查结论

- **是否越界实现 S10 沙箱、S13/S14 Memory、S17 系统库或 S18 HTTP：否。** 仅增加 todo 与 Registry 的必要 context 注入。
- **`session_id` 是否完全不在模型 Schema：否。** 不在 properties，但仍出现在完整 Schema 的根 description，见 S09-P1-01。
- **模型伪造 `session_id` 是否能覆盖可信上下文：不能。** Registry 在调用 handler 前返回 `invalid_arguments`；定向 add 探针证明无副作用。
- **非法 action 是否在真实执行路径返回 `invalid_action`：否。** Registry 返回 `invalid_arguments`；`invalid_action` 只在 handler 直调测试中可达。
- **TC-L3-013 是否越界实现历史隔离：没有实现。** 这是正确的阶段边界，但 TESTING 的 S09 覆盖说明没有把历史断言明确拆给 S13/S18。
- **是否提前实现并发安全或持久化：否。** change 明确声明非线程安全、重启丢失，S13 替换。
- **S08 报告 P1 是否在 S09 前关闭：是。** 独立 change 已于 `079c2db` 归档并通过门禁。

## 7. 技术债与后续阶段影响

| 后续阶段 | 隐性风险 | 触发条件 | 建议处理时机 |
| --- | --- | --- | --- |
| S10–S12 | Registry 的 context 按名字注入会影响未来同名参数工具 | 新 handler 声明业务 `context` 或注解不符 | 新增下一个需要 context 的工具前完善注册期校验 |
| S13 | `_STORE` 硬编码、可变元素别名、非原子 id/状态更新 | 替换为 Redis/Memory KV，或同 session 并发 | S13 设计期先定义原子 store 接口和注入点 |
| S13 | TC-L3-013 的“历史隔离”未拆分 | Memory 开始保存会话历史 | S13 补正式历史隔离断言并更新覆盖边界 |
| S16 | todo 输出/历史若持有可变对象，快照与裁剪结果可能漂移 | Store 对象直接进入上下文或缓存 | S13 先改为不可变 DTO；S16 复核序列化快照 |
| S18 | Runtime 的 `RegistryExecutor.execute` 当前不携带 `ToolContext` | HTTP 真正调用 todo | S13/S18 组合根注入可信 session/trace，不允许模型路径构造 context |
| S18 | 同 session 并发可能重复 id、丢更新或状态覆盖 | 两个 HTTP 请求并发写同一 session | 使用存储原子操作并新增同 session 并发测试 |
| S18 | 模型可见描述仍出现 `session_id`，可能诱导模型生成被拒参数 | 真实模型读取 todo Schema | 进入 S10 前修 S09-P1-01，S18 再做真实工具闭环 |

## 8. 总体结论

**S09 暂不可进入 S10。** 核心 CRUD、会话分区、伪造字段拦截、打包和 187 个累计测试均可运行，且无 P0；但完整模型 Schema 违反可信上下文契约，真实 Registry 的 action/type 行为与公布契约不一致，两个正式 TC 又存在矛盾或被过度标记为覆盖。这些问题会在后续工具与 S13/S18 组合时固化错误接口。

进入 S10 前必须处理：

1. **S09-P1-01**：确保完整模型可见 Schema 不含 `session_id`，并补全量 Schema 断言。
2. **S09-P1-02**：统一非法 action 在 Registry 与 handler 的错误码契约，测试真实执行路径。
3. **S09-P1-03**：拒绝 bool/字符串/浮点等非 integer index，保证 Schema 与执行一致。
4. **S09-P1-04**：裁决并同步 TC-L1-006 的 complete 后列表数量，补精确断言。
5. **S09-P1-05**：补全 TC-L3-013 的跨会话 complete 与伪造无副作用验证，并明确历史断言的后续阶段。

可选建议：在 S13 前处理 store 快照与注入点；为 context-aware handler 增加注册期校验；后续提交遵守目录与 72 字符正文规范。

## 9. 工作区状态与副作用

- **评估前**：`git status --short --branch` 为 `## main...origin/main`，无 tracked 改动；HEAD 与 `origin/main` 均为 `9252738`。
- **验证结束、报告落盘前**：tracked 工作区仍干净。
- **报告落盘后预期**：仅新增 `Docs/S09-report.md`、修改 `Docs/PROMPT.md`；未修改实现、测试、Issue、PLAN、OpenSpec 或远程状态，未提交、未推送。
- 测试/构建命令生成或更新了被 `.gitignore` 忽略的 `.coverage`、`.pytest_cache/`、`agent_mini.egg-info/` 与各级 `__pycache__/`；它们不出现在普通 `git status --short` 中。本次按只读评估边界未清理，需人工按需删除。
- 隔离安装目录仍保留于 `C:\Users\Ryan\AppData\Local\Temp\agent-mini-s09-audit-e7b53c8d6d0b41ccbecd08f2f5537265`，包含 wheel 与 venv；需人工确认路径后清理。

## 10. 修复记录（2026-10-23）

| 报告项 | 修复 | 证据 |
| --- | --- | --- |
| S09-P1-01 Schema 暴露 session_id | 移除 TodoArgs 描述中的 session_id；完整 Schema 字符串断言 | `test_schema_does_not_expose_session_id` |
| S09-P1-02 invalid_action 不可达 | action 改为 str，handler 统一返回 invalid_action | Registry `action=bogus` 测试 |
| S09-P1-03 宽松 index | `Field(strict=True)`，拒绝 "1"/1.5/True | 参数化 Registry 测试 |
| S09-P1-04 TC 计数矛盾 | 口径定为 complete 后仍 2 项、第一项 done；测试精确断言 | `test_add_list_complete_same_session` |
| S09-P1-05 TC-L3-013 断言不足 | 补跨会话 complete、伪造后 list 无副作用 | 隔离/伪造测试 |
| S09-P2-01 可变共享 | TodoItem frozen；Store 返回 replace 快照 | Store 快照测试 |
| S09-P2-02 Store 注入点 | 新增 `configure_todo_store` | `test_store_can_be_configured` |
| S09-P2-03 注册期契约 | 仍待后续 | — |
| S09-P2-04 格式 | 由 ruff/format 复核 | 全量静态检查 |

**复验**：192 passed；unit 128、contract 64；覆盖率 **96.34%**；mypy 57 files 0 errors；ruff/format/OpenSpec/wheel 通过。S09 可进入 S10。

