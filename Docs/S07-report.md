# S07 独立评估报告

> 评估日期：2026-10-23  
> 基准提交：`1d6d93b`（`main` 与 `origin/main` 一致）  
> 评估性质：只读代码、测试、规范、流程与分发复核  
> 总体结论：**不通过；修复 4 项 P1 后方可进入 S08**（修复后见 §10；S07 已恢复准入）

## 1. 评估范围与基准

### 1.1 实际读取范围

| 基准 | 实际读取位置 | 核对重点 |
| --- | --- | --- |
| 阶段计划与 DoD | `Docs/PLAN.md` S07、§4、§5、阶段状态表 | S07 输出、验收标准、TC、M2 边界与准出状态 |
| 功能需求 | `Docs/REQUIREMENT.md` FR-TOOL-02、NFR-SEC-03、AC-02/03 | 四则、括号、安全拒绝与验收映射 |
| 设计契约 | `Docs/DESIGN.md` §1.1/1.3、§2.2、§3.3、§6～§8 | AST 白名单、阈值、错误码、依赖与风险 |
| 测试定义 | `Docs/TESTING.md` TC-L1-001/002/003、§4.2.7、§5.2、§6.2 | 正确求值、危险表达式、结构化错误和工具选型 |
| 全局规范 | `AGENT.md` 全文；`openspec/specs/engineering-standards/spec.md` | Docs First、TDD、覆盖率、代码、错误、依赖、导入与门禁 |
| 过程记录 | `Docs/PROMPT.md` S07；`Docs/ISSUE.md` S07；`MEMORY.md` S07；`Docs/S06-report.md` §10 | S06 前置修复、红绿证据、完成声明与前序覆盖率 |
| OpenSpec | `openspec/changes/archive/2026-10-23-s07-tool-calculator/`；`openspec/specs/calculator/spec.md` | change 时序、白名单、阈值、错误与归档 |
| 实现与测试 | `agent_mini/tools/builtin/calculator.py`；`agent_mini/tools/registry.py`；`tests/unit/test_calculator.py`；`tests/unit/test_package_skeleton.py` | 求值器、真实注册路径、断言有效性和骨架回填 |
| 构建与依赖 | `pyproject.toml`、`README.md`、wheel | 依赖变化、包文件、隔离环境安装与仓库外导入 |

### 1.2 文档基准之间的一致性与缺口

- `PLAN`、FR-TOOL-02 与 TC-L1-001/002/003 对“安全四则与括号、危险表达式拒绝、除零/语法/类型错误结构化”的主范围一致。
- `DESIGN` 与 calculator 主规格进一步明确 `UAdd/USub`、200 字符、20 层 AST、1e12 和 7 个错误码；实现大体落实，但 `CalculatorArgs` 的 pydantic 长度校验使真实 Registry 路径先返回通用 `invalid_arguments`，没有保持 `expression_too_long`。
- `TESTING` §4.2.7 宣称 S07 已覆盖四则与取负，实际测试没有二元减法和取正；TC-L1-002 定义要求“无任何副作用”，现有测试只断言错误码。
- `DESIGN` §1.1 与 `TESTING` §5.2 指定 `hypothesis` 用于 calculator 属性测试，`pyproject.toml` 没有声明且 S07 没有属性测试。
- `PLAN`、README、MEMORY、ISSUE 已把 S07 标为完成；但覆盖率从 S06 的 95.25% 降至 94.02%，并存在上述契约和测试缺口，完成声明早于 DoD。

## 2. 复核命令与结果

### 2.1 实际复跑

| 命令/验证 | 关键结果 |
| --- | --- |
| `git status --short --branch`、`git rev-parse HEAD/origin/main` | 评估前工作区干净；本地与远端均为 `1d6d93b` |
| `git log/show/diff d106f9f..1d6d93b` | OpenSpec 规划 `813f447` 先于代码 `a54a065`；代码与测试同 commit；之后文档 `5918e56` 和归档 `1d6d93b` |
| `python -m pytest -q -m unit -p no:cacheprovider` | **90 passed，64 deselected** |
| `python -m pytest -q -m contract -p no:cacheprovider` | **64 passed，90 deselected** |
| `python -m pytest -q -p no:cacheprovider` | **154 passed** |
| `python -m pytest --cov=agent_mini --cov-report=term-missing`（coverage 文件在仓库外） | **154 passed；总覆盖率 94%；calculator 85%**；`_sub`、`_positive` 未覆盖 |
| `ruff format --check .` | **56 files already formatted** |
| `ruff check .` | **All checks passed** |
| `mypy agent_mini tests` | **Success: no issues found in 53 source files** |
| `openspec validate --strict` | 当前 CLI 未指定对象时返回 `Nothing to validate`，不能作为通过证据 |
| `openspec validate --all --strict` | **6 passed，0 failed**；calculator 主规格通过 |
| `python -m pip check` | **No broken requirements found** |
| `python -m pip wheel . --no-deps` 到仓库外临时目录 | wheel 构建成功；包含 `calculator.py` 与 `systemdb/schema.sql` |
| 临时 venv 安装 wheel 并从仓库外导入 | 依赖按 wheel 元数据安装；calculator 注册、`(2+3)*4=20`、`pip check` 均通过 |
| 禁用框架、动态执行、`# noqa`、`# type: ignore`、skip 扫描 | 实现零命中；`eval` 字样只出现在测试危险输入与私有 `_eval` 函数名 |
| `git diff d106f9f..HEAD -- pyproject.toml` | 无差异；S07 未新增运行或开发依赖 |

首次自定义 wheel 探针错误引用了不存在且不属于契约的 `CALCULATOR_SPEC` 属性，因评估命令自身假设错误失败；修正为检查 `DEFAULT_REGISTRY.get("calculator")` 后，临时 target 和全新 venv 均通过。该失败不属于项目缺陷。

### 2.2 定向行为探针

| 探针 | 实际结果 | 判定 |
| --- | --- | --- |
| 直接调用 `calculate()`，传 201 字符 | `expression_too_long` | handler 自身正确 |
| 经 `DEFAULT_REGISTRY.execute()` 传同一输入 | `invalid_arguments` | **真实工具路径与 calculator 契约不一致** |
| `5-2`、`+3` | 分别成功返回 `3`、`3` | 实现支持，但正式测试未覆盖 |
| `1e309` | `number_overflow` | 非有限浮点被拒绝 |
| `open('x','w')` | `unsafe_expression`，未执行调用 | AST 主路径安全 |
| 新进程仅导入 `DEFAULT_REGISTRY` | 空 Schema 列表 | 必须先导入 calculator 模块才触发装饰器注册，符合归档 design，但后续组合根必须显式加载 |

### 2.3 历史 TDD 证据

- 父提交中 calculator 模块和测试文件均不存在；最终实现与测试在 `a54a065` 同一提交，符合“实现与测试同 commit”。
- `Docs/PROMPT.md` 完整保存了 S07 原始 Prompt，并逐组记录占位实现下的 `NotImplementedError` 红因及绿灯结果。
- 这些红灯发生在未提交工作区，Git 历史无法独立重建；本次只确认记录内部一致，不把摘要等同于可复跑的原始终端日志。

### 2.4 未复跑项

- 未调用真实 LLM/provider、数据库、HTTP 或网络工具；均不属于 S07。
- 未执行 S08～S12 的 time/todo/沙箱/文件/search；源码 diff 也未出现这些实现。
- 未跑 S18 的真实模型自主选工具闭环；TC-LIVE-002 按计划留待 S18。

## 3. 维度结论

| 维度 | 结论 | 理由与证据 |
| --- | --- | --- |
| 需求与范围合规 | 有条件通过 | 只交付 calculator，未越界实现其他工具/Memory/HTTP；但 Registry 超长错误语义未达主规格，`calculator.py:65-98`。 |
| 四则与数值正确性 | 有条件通过 | 定向探针和现有样例均正确；二元减法和取正实现存在但没有正式测试，`calculator.py:29-62`、`test_calculator.py:13-27`。 |
| AST 白名单与安全 | 通过 | 仅 Constant/BinOp/UnaryOp 递归求值，Call/Name 等拒绝；无 `eval/exec/compile/import` 执行，危险样例全部返回 unsafe。 |
| 阈值与错误边界 | 不通过 | handler 的 7 类错误可结构化，但 Registry 先由 pydantic 把超长表达式改判为 `invalid_arguments`。 |
| 注册与 Schema | 有条件通过 | 模块导入后注册、Schema required、正常执行均通过；fresh registry 不自动加载 builtin，留待组合根处理。 |
| 测试质量与 TDD | 不通过 | 25 个 S07 增量实例全绿，但四则测试未覆盖 Sub/UAdd，安全测试未验证无副作用，边界只测 handler。 |
| 全局代码规范 | 不通过 | Ruff/format/mypy、行宽、复杂度、中文 docstring 均通过；覆盖率低于上一提交，违反 `AGENT.md` §2。 |
| 打包与分发 | 通过 | wheel 含 calculator 与 package-data；全新 venv 安装、仓库外导入和 `pip check` 通过。 |
| 依赖审计 | 有条件通过 | S07 无新增运行依赖和禁用框架；既有 pydantic 已声明，但设计指定的 hypothesis 未声明/使用。 |
| 流程与文档闭环 | 有条件通过 | OpenSpec 先于实现、归档有效、Prompt/Issue/PLAN/README/MEMORY 已同步；完成状态未反映 P1 与覆盖率回退。 |
| 可复现性 | 通过 | 当前环境门禁、wheel、隔离 venv 均可复现；不依赖仓库可编辑安装或真实外部服务。 |
| 后续阶段影响 | 不通过 | 错误码断层会在 S18 把领域错误误报为参数错误；装饰器导入式注册需在 M2 组合时统一加载。 |

## 4. 问题清单

### P0

无。静态检查与行为探针均未发现任意代码执行、文件副作用、数据损坏或越界访问。

### P1

#### S07-P1-01 — Registry 路径把 `expression_too_long` 改判为 `invalid_arguments`

- **位置**：`agent_mini/tools/builtin/calculator.py:65-68,84-98`，`CalculatorArgs.expression`、`calculate`；`agent_mini/tools/registry.py:113-130`，`ToolRegistry.execute`；`tests/unit/test_calculator.py:85-88`
- **问题描述**：`CalculatorArgs` 的 `max_length=200` 在 handler 前触发通用 pydantic 校验。直接调用 handler 返回 `expression_too_long`，真实工具执行路径却返回 `invalid_arguments`。现有测试只直调 handler，绕开了注册表边界。
- **判定依据**：`Docs/DESIGN.md:311` 与 calculator 主规格“结构化错误与边界”要求超长固定返回 `expression_too_long`；`Docs/TESTING.md:207-208` 同时宣称覆盖超长和 Registry 执行；工程规范 CR-08 要求错误码边界正确。
- **建议方向**：让长度分类只有一个权威边界；可由 calculator 参数模型保留类型/必填校验、handler 负责领域阈值，或为 Registry 建立不丢失领域错误码的明确映射。必须增加 Registry 路径的 200/201 字符测试。

#### S07-P1-02 — “四则/取正已覆盖”与测试事实不符

- **位置**：`tests/unit/test_calculator.py:13-27`，`test_calculator_evaluates_four_operations`；`agent_mini/tools/builtin/calculator.py:33-34,45-46`，`_sub`、`_positive`
- **问题描述**：参数集覆盖加法、乘法、除法和一元负号，没有任何二元减法或一元正号；`-3+2` 不能证明 `ast.Sub`。coverage 明确显示 `_sub` 与 `_positive` 未执行，测试名和 `TESTING` 的“四则已覆盖”陈述均过强。
- **判定依据**：FR-TOOL-02、`Docs/DESIGN.md:311` 和 calculator 主规格要求 `+ - * /`、取负/取正；`AGENT.md` §2.2 要求每个新增函数/模块有对应测试；工程规范 CR-07 要求测试覆盖真实契约。
- **建议方向**：增加二元减法和一元正号的 handler/Registry 正例，并让测试名与实际覆盖一致；保留现有运算优先级和浮点用例。

#### S07-P1-03 — TC-L1-002 未验证“无任何副作用”

- **位置**：`tests/unit/test_calculator.py:30-50`，`test_calculator_rejects_dangerous_expressions`
- **问题描述**：危险表达式测试只断言 `ok=False` 与 `unsafe_expression`，没有断言 `open('a','w')` 未创建文件，也没有为 import/system 调用设置可观察哨兵。因此测试不能证明 TC 中的“无任何副作用”，尽管当前 AST 实现经静态复核确实不会执行这些调用。
- **判定依据**：`Docs/TESTING.md:95` 与 calculator 主规格“代码执行”场景明确要求无副作用；`AGENT.md` §1.3 要求每条验收标准映射到测试；安全断言不得只验证自定义返回值。
- **建议方向**：使用 `tmp_path` 检查目标文件始终不存在，并通过 monkeypatch/哨兵证明危险调用没有发生；继续保留静态禁用 API 扫描。

#### S07-P1-04 — 阶段覆盖率较 S06 回退

- **位置**：`AGENT.md:71`；`Docs/PLAN.md:345-346`；`MEMORY.md:9,16`；S07 coverage 结果
- **问题描述**：S06 记录总覆盖率 95.25%，S07 记录 94.02%，下降 1.23 个百分点；虽高于 80% 下限，但违反仓库“覆盖率不得低于上一提交”的增量门禁。新增 calculator 自身只有 85%，未覆盖行与 P1-02、错误兜底分支一致。
- **判定依据**：`AGENT.md` §2“若接入覆盖率工具，覆盖率不得低于上一提交”；工程规范 CR-07 与阶段 DoD 要求全部门禁通过。
- **建议方向**：优先补真实契约和边界测试提升覆盖，不得排除文件、降低阈值或写无行为价值的覆盖测试；修复后与 S06 的 95.25% 基线重新比较。

### P2

#### S07-P2-01 — 设计选定的 hypothesis 未声明也未用于 calculator

- **位置**：`Docs/DESIGN.md:33`；`Docs/TESTING.md:295`；`pyproject.toml:16-24`；`tests/unit/test_calculator.py`
- **问题描述**：设计和测试策略均写明 hypothesis 用于 calculator 表达式组合，但 dev 依赖没有 hypothesis，S07 只有固定样例。当前样例可验证主路径，却难以系统覆盖运算树、边界值和拒绝节点组合。
- **判定依据**：工程规范“依赖与配置规范”要求依赖单点声明、文档与实际一致；`Docs/DESIGN.md` §1.1 和 `Docs/TESTING.md` §5.2 是已选测试栈。
- **建议方向**：若仍采用 hypothesis，则锁定兼容版本并增加受限表达式生成器/不变量测试；若决定不用，应先修订设计和测试策略，不能继续声明已采用。

#### S07-P2-02 — 实现暴露了文档未登记的第八个错误码

- **位置**：`agent_mini/tools/builtin/calculator.py:22,96-97,168`，`ERROR_EVALUATION`；`Docs/DESIGN.md:311`；`MEMORY.md:7`
- **问题描述**：文档列出 7 个 calculator 错误码，实现的兜底分支还可能返回 `evaluation_error`。该码目前只服务未知内部异常，正常输入难以触发，但公开错误分类与文档不一致。
- **判定依据**：工程规范错误码要求小写 snake_case、稳定且登记；阶段 DoD 要求 DESIGN/TESTING 与实现一致。
- **建议方向**：明确内部兜底是否属于 calculator 公共协议；保留则写入设计并测试，不保留则映射到既有工具执行错误，避免形成未登记分支。

#### S07-P2-03 — builtin 包说明仍是占位，注册依赖隐式导入

- **位置**：`agent_mini/tools/__init__.py:1`；`agent_mini/tools/builtin/__init__.py:1`；归档 change `design.md`“注册”决策
- **问题描述**：两个包 docstring 仍写“待 S06/S06–S12 落地”。新进程只导入 Registry 时工具表为空，必须显式导入 calculator 才注册。归档 design 已说明该机制，因此当前不是 S07 功能错误，但过期说明和隐式加载前提容易误导后续工具集成。
- **判定依据**：工程规范 CR-04/CR-15 要求注释不过期、文档与实现同步；M2 要求六工具最终注册可用。
- **建议方向**：在不提前实现 S21 容器的前提下更新包说明；最迟 S12/M2 收口时建立显式 builtin 加载/组合入口，并测试 fresh process 的完整工具集合。

### Info

#### S07-INFO-01 — AST 求值器的安全边界实现扎实

- **位置**：`agent_mini/tools/builtin/calculator.py:101-157`
- **观察**：解析使用 `ast.parse(mode="eval")`，仅递归接受 Constant/BinOp/UnaryOp；bool、字符串、危险节点、非有限数和绝对值超限均被拒绝。源码没有动态执行或正文正则猜测。
- **建议**：修复测试和 Registry 分类时保留该白名单结构，不引入表达式执行兜底。

#### S07-INFO-02 — Docs First、提交拆分与分发主流程正确

- **位置**：提交 `813f447`、`a54a065`、`5918e56`、`1d6d93b`；wheel/venv 复核
- **观察**：OpenSpec change 先于实现，代码与测试同 commit，文档和归档随后完成；四个 subject 符合 Conventional Commits；wheel 在全新 venv 可安装并导入。
- **建议**：后续阶段继续保持相同时序，并保存可独立复核的红灯命令摘要。

## 5. 需求—实现—测试追溯

| 需求/TC | 实现位置 | 测试位置 | 是否覆盖 | 是否越界 |
| --- | --- | --- | --- | --- |
| FR-TOOL-02：安全四则与括号 | `calculator.py` `_BINARY_OPS/_eval/_binary` | `test_calculator_evaluates_four_operations` | **部分**；加/乘/除/括号有断言，二元减法缺失 | 否 |
| FR-TOOL-02：取负/取正 | `calculator.py` `_UNARY_OPS/_unary` | `-3+2` 参数 | **部分**；取负覆盖，取正缺失 | 否 |
| FR-TOOL-02 / NFR-SEC-03：禁止任意代码执行 | `calculator.py` `_eval` 默认拒绝 | `test_calculator_rejects_dangerous_expressions` | **部分**；错误码覆盖，副作用未断言 | 否 |
| 阈值：200/20/1e12 | `MAX_EXPRESSION_CHARS/MAX_AST_DEPTH/MAX_ABS_VALUE` | 三个 `test_calculator_rejects_*` | **部分**；直接 handler 超限覆盖，Registry 长度分类错误，临界值未测 | 否 |
| TC-L1-001：`(2+3)*4=20` | `calculate` → `_evaluate_expression` | 参数化首项 | 覆盖并通过 | 否；LIVE 自主选择留 S18 |
| TC-L1-002：import/eval/open 均 unsafe 且无副作用 | AST 白名单 | 危险表达式参数化前三项及扩展节点 | 错误码覆盖；**无副作用断言缺失** | 否；进程级集成留后续 |
| TC-L1-003：`1/0`、`2+`、`"a"+1` | `_binary/_evaluate_expression/_constant` | `test_calculator_returns_structured_errors` | 覆盖并通过，不抛异常 | 否 |
| 注册/Schema/Registry 执行 | `CalculatorArgs`、`@tool`、`ToolRegistry` | `test_calculator_is_registered_with_schema`、`test_registry_executes_calculator` | 正常路径覆盖；超长失败路径缺失 | 属 S07 必需接入，不越界 |
| S00 骨架清单回填 | `calculator.py` 新模块 | `test_package_skeleton.py` 期望列表 | 通过；增加条目，没有 skip 或删除既有条目 | 否 |

## 6. 边界抽查

- **是否越界实现 S08～S12 其他工具、沙箱、Memory、HTTP、配置或真实 API：否。**
- **是否存在重试、退避、HTTP 状态分类或网络访问：否。** S07 是纯计算工具。
- **是否使用 `eval` / `exec` / `compile` / import 执行表达式：否。** `_eval` 只是私有递归函数名。
- **危险表达式实际是否执行：否。** 定向探针返回 `unsafe_expression`，没有文件落地；正式测试仍缺少副作用断言。
- **四则是否全部实现：是。** 加减乘除均在 `_BINARY_OPS`；但测试只覆盖加乘除。
- **结构化错误是否全路径一致：否。** 超长表达式在直接 handler 与 Registry 路径分别为 `expression_too_long` 和 `invalid_arguments`。
- **是否提前实现 S18 的真实模型自主选工具：否。** 当前只验证本地 Registry 调用。
- **S00 占位测试如何处理新增模块：增加 `tools/builtin/calculator.py` 期望条目；未 skip、未删除既有条目。**
- **是否新增依赖或触碰禁用框架：否。** 但既有设计指定的 hypothesis 尚未声明。

## 7. 技术债与后续阶段影响

| 后续阶段 | 风险/技术债 | 触发条件 | 建议处理时机 |
| --- | --- | --- | --- |
| S08 time | 参数模型约束先于 handler 会再次吞掉领域错误码 | time 的 IANA 时区/长度等同时放在 pydantic 与 handler | S08 开工前先确立 Registry 错误分层规则 |
| S09 todo | fresh registry 依赖模块导入副作用 | 新增多个 builtin 后漏 import 任一模块 | S09 起记录加载策略，S12/M2 统一验证 |
| S10/S11 沙箱 | 缺少 hypothesis，组合边界仍靠固定样例 | 路径穿越、符号链接和长度组合增加 | S10 前决定是否落实设计中的属性测试 |
| S12/M2 | 没有明确 builtin 聚合/组合入口 | 需要六个工具在新进程一次性可用 | M2 收口前建立显式加载并做 fresh-process 测试 |
| S18 | 模型收到 `invalid_arguments` 而不是 `expression_too_long` | 模型生成超长 calculator 参数 | S08 前修 P1-01，避免错误语义扩散 |
| S20 | `evaluation_error` 未纳入统一错误目录 | 未知 calculator 内部异常进入公开结果 | S20 统一错误体系前登记或归并 |

## 8. 总体结论

### 8.1 是否可以进入 S08

**暂不可进入 S08。** calculator 的核心求值、安全白名单、正常注册、打包和 154 个累计测试均可用，且没有 P0；但真实 Registry 路径违反超长错误码契约，两个已声明运算分支没有测试，安全 TC 没有验证“无副作用”，覆盖率也违反不低于上一提交的全局门禁。

进入 S08 前必须处理：

1. S07-P1-01：统一直接 handler 与 Registry 的超长错误分类，并补真实执行路径边界测试。
2. S07-P1-02：补二元减法与一元取正测试，修正“四则已覆盖”的证据链。
3. S07-P1-03：为 import/eval/open 危险输入增加可观察的无副作用断言。
4. S07-P1-04：通过有效契约测试把累计覆盖率恢复到不低于 S06 的 95.25%。

可选建议：落实或修订 hypothesis 策略；登记 `evaluation_error`；更新 tools/builtin 包说明并在 M2 收口前建立显式加载入口。

## 9. 工作区状态与副作用

### 9.1 状态对比

- 评估开始前：`git status --short --branch` 仅输出 `## main...origin/main`。
- 所有只读测试、探针、wheel 与隔离 venv 完成后且报告写入前：仍仅输出 `## main...origin/main`。
- 本轮按 `AGENT.md` 评估归档规则新增 `Docs/S07-report.md`，并在 `Docs/PROMPT.md` 追加本轮原始 Prompt；未修改实现、测试、OpenSpec、PLAN、ISSUE、README、MEMORY 或远程状态。

### 9.2 评估副作用

- coverage 文件：`C:\Users\Ryan\AppData\Local\Temp\agent-mini-s07.coverage`、`agent-mini-s07-final-verify.coverage`、`agent-mini-s07-final-verify-2.coverage`。
- wheel：`C:\Users\Ryan\AppData\Local\Temp\agent-mini-s07-wheel-fab25b22bd754e91853dd7fc5a1820b1`。
- 临时安装 target：`C:\Users\Ryan\AppData\Local\Temp\agent-mini-s07-target-1168b4fc3ca64e30b4a362ed54e5869d`、`C:\Users\Ryan\AppData\Local\Temp\agent-mini-s07-target-eea334e80c2c413884dfa5c625191294`。
- 隔离 venv：`C:\Users\Ryan\AppData\Local\Temp\agent-mini-s07-venv-1f047c66cc3742c291d726ab620fcff2`。
- wheel 构建和测试可能刷新仓库内被忽略的 `.coverage`、`.mypy_cache/`、`.pytest_cache/`、`.ruff_cache/`、`agent_mini.egg-info/` 与 `__pycache__/`；评估前未记录 ignored 基线，无法区分既有与本轮刷新项。
- 上述临时/忽略产物未自动删除；如需清理，请人工确认路径后处理。非忽略工作区变更仅应为本报告与 Prompt 记录。

## 10. 修复记录（2026-10-23）

| 报告项 | 修复 | 证据 |
| --- | --- | --- |
| S07-P1-01 Registry 超长误判 | 移除 `CalculatorArgs` 的 `max_length`，由 handler 统一返回 `expression_too_long` | 直接与 Registry 超长测试 |
| S07-P1-02 减法/取正缺测 | 补 `5-2=3`、`+3=3` | `test_calculator_evaluates_four_operations` |
| S07-P1-03 无副作用未断言 | 用临时路径 `open(...)` 验证文件未创建 | `test_dangerous_open_has_no_side_effect` |
| S07-P1-04 覆盖率回退 | 补减/正/副作用/Registry 超长/异常兜底/Recursion/非数值结果用例 | 总覆盖率 **95.81%**，高于 S06 的 95.25% |
| P2 可选 | `evaluation_error` 已记录为兜底码；hypothesis 仍未引入 | 本表 |

**复验**：164 passed；unit 100、contract 64；mypy 53 files 0 errors；ruff/format/OpenSpec/wheel 通过。S07 可进入 S08。
