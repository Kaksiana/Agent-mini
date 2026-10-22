# Agent-mini 工程规范 Specification

## Purpose

本规范是 Agent-mini 在 OpenSpec 体系下的全局工程约束，统一规定代码、可读性、注释、命名、目录、测试、错误处理、日志、依赖配置与导入规则。规范以 `AGENT.md` 为最高效力文件，采用“引用 + 细化”的方式衔接 `Docs/` 基线文档，供 S00–S21 的编码、评审与验收共同执行。

## Requirements

### Requirement: 规范效力、来源与冲突裁决

本规范 MUST 以 `AGENT.md` 为最高效力文件，并只在其基础上做可执行细化。

**效力顺序**

1. `AGENT.md`：文档优先、TDD、Prompt/Issue 记录、Git、OpenSpec、阶段粒度、禁框架。
2. `Docs/REQUIREMENT.md`：FR / NFR / AC 需求基线。
3. `Docs/DESIGN.md`：架构、接口、数据流、ADR。
4. `Docs/TESTING.md`：TC 编号、分层与测试设计。
5. `Docs/PLAN.md`：S00–S21 阶段、里程碑与 DoD。
6. 本规范：编码层的实现级细化。
7. 工具默认值：ruff / mypy / pytest 的默认配置。

低效力文件与高效力文件冲突时，不得自行选择；必须按上述顺序裁决，并在本规范“已知冲突与裁决”中留痕。

用户当次明确指令对任务范围作出的特别约定，在本次任务内优先执行，但不得用于规避 `AGENT.md` 的文档、测试真实性、安全与禁框架条款；涉及长期规则的约定必须记录在 `Docs/ISSUE.md` 或本规范变更记录中。

**引用边界（引用 + 细化，不另设流程）**

| 主题 | 已有出处 | 本规范的处理 |
| --- | --- | --- |
| 文档优先、验收标准四要素 | `AGENT.md` §1 | 引用 + 细化；不另设文档流程 |
| TDD 红绿重构、测试与实现同 commit | `AGENT.md` §2 | 引用 + 细化；补充测试命名、夹具与断言 |
| `Docs/PROMPT.md` 记录 | `AGENT.md` §3 | 引用；不定义模板 |
| `Docs/ISSUE.md` 记录 | `AGENT.md` §4 | 引用；只规定例外登记方式 |
| Git、`.gitignore`、commit message | `AGENT.md` §5 | 引用；不新增 commit type |
| OpenSpec 与 SuperPower SKILL | `AGENT.md` §6 | 引用；补充 OpenSpec 文件位置 |
| 需求驱动、FR/AC/TC 编号 | `AGENT.md` §7 | 引用；补充命名格式 |
| 单功能单阶段、DoD | `AGENT.md` §8、`Docs/PLAN.md` §5 | 引用；补充代码门禁 |
| 禁止 Agent 框架 | `AGENT.md` §9、`Docs/DESIGN.md` §6 | 引用；补充扫描命令 |
| 提交前检查清单 | `AGENT.md` §10 | 引用；补充自动化命令 |

**已知冲突与裁决**

| 编号 | 冲突点 | 以谁为准 | 处理方式 |
| --- | --- | --- | --- |
| C-01 | `AGENT.md` §6.1 曾写“尚未执行 `openspec init`”，但仓库已有 `openspec/config.yaml`，且 `Docs/ISSUE.md` ISSUE-005 已标记 Resolved | 仓库事实 | 已于 2026-10-22 更新 `AGENT.md` §6.1 为已初始化并加入本规范入口；ISSUE-014 |
| C-02 | `Docs/DESIGN.md` §3.8 曾使用 `LLM_API_KEY`；`Docs/PLAN.md` S18、`Docs/TESTING.md` §4.6 与 `MEMORY.md` 使用 `DEEPSEEK_API_KEY` | 统一使用 `DEEPSEEK_API_KEY` | 已于 2026-10-22 修订 `DESIGN.md` §3.8、版本与 §10；禁止 `LLM_API_KEY` 别名；ISSUE-013 |
| C-03 | `Docs/REQUIREMENT.md` NG-03 规定不做 Web 前端/CLI，但仓库存在空目录 `Backend/`、`Frontend/`（ISSUE-006 为保留而加 `.gitkeep`） | 需求基线 | 两个目录只作占位，禁止放业务代码；删除或改用途前必须先改需求并获得用户批准 |
| C-04 | `AGENT.md` §6.1 要求 OpenSpec 初始化，OpenSpec 1.12 已用 `config.yaml` 的 `context` 取代旧版 `openspec/project.md` | OpenSpec 1.12 实际约定 | 不创建 legacy `project.md`；项目上下文写入 `config.yaml`；本规范放在 `openspec/specs/` 下 |
| C-05 | `AGENT.md` §2 要求测试命令以 `README.md` 为准，但 README 仅有标题；`Docs/TESTING.md` §5.3 命令标注“暂定”，ISSUE-008 仍为 Open | `AGENT.md` §2 | S00 必须把真实可执行命令写入 README；在此之前本规范不宣称任何测试命令已可用，也不编造执行结果 |
| C-06 | `Docs/DESIGN.md` §1.1 只给依赖最低版本，未给行宽、嵌套、函数长度等代码级阈值 | 本规范补充 | 下列“新增决策”是 DESIGN 未覆盖的实现级细化；S00 落地时若需调整，先改本规范并留痕 |

**新增决策（DESIGN 未规定，本规范补充）**

| 编号 | 决策 | 理由 | 落地阶段 |
| --- | --- | --- | --- |
| D-01 | 行宽上限 100 字符 | 兼顾可读性与中文注释；ruff 可自动检查 | S00 |
| D-02 | 嵌套 ≤ 3 层、函数 ≤ 50 行、模块 ≤ 500 行 | 保证逐行展示与讲解，限制认知负担 | S00 起持续执行 |
| D-03 | 测试目录按 L1–L5 与 LIVE 分层 | 对齐 `Docs/TESTING.md` §3，避免测试堆在单目录 | S00 |
| D-04 | 全部使用绝对导入 | 避免相对层级歧义，便于跨文件阅读与重构 | S00 |
| D-05 | `Docs/` 保持现有大写文件名；OpenSpec 使用小写 kebab-case | 不破坏既有文档引用，同时符合 OpenSpec 路径约定 | 立即 |
| D-06 | `Data/` 只放运行数据与沙箱数据，`Script/` 只放仓库级脚本 | 隔离源码、数据与工具，降低误提交与越界风险 | 立即 |
| D-07 | 标识符使用英文，注释与 docstring 默认中文 | 保持代码可搜索、可移植，同时满足中文可读性 | 立即 |
| D-08 | mypy 对 `agent_mini/` 启用 `strict`，测试目录放宽 | 新代码默认强类型，减少运行期错误；测试保留灵活性 | S00 |
| D-09 | ruff 启用 E/F/W/I/N/UP/B/SIM/C4/RET/ANN/D/TID/RUF/C90/PLR 基线 | 把行宽、导入、注解、复杂度与 docstring 变成可自动检查项 | S00 |

**变更记录**

| 版本 | 日期 | 变更 | 原因 |
| --- | --- | --- | --- |
| v1.0 | 2026-10-22 | 初版：建立 14 项全局工程规范、冲突裁决与新增决策 | 在 OpenSpec 体系下为 S00–S21 提供统一编码/评审/验收约束 |
| v1.1 | 2026-10-22 | 关闭 C-01/C-02；同步 `AGENT.md`、`DESIGN.md`、PROMPT/ISSUE；环境变量统一为 `DEEPSEEK_API_KEY` | 用户调整要求；ISSUE-013/014/015 |

本表的修改必须与规范正文同一次变更提交，禁止只改正文不记录。

**执行时机**：建立或修改本规范时；每个阶段开工前；发现文档冲突时；阶段验收与合并评审时。

**验证方式**：

- `openspec validate engineering-standards --type spec --strict` 与 `openspec validate --specs --strict` 通过。
- 对照“引用边界”检查本规范没有另设与 `AGENT.md` 冲突的流程。
- 对照“已知冲突与裁决”确认没有未决冲突；新增冲突必须先登记再编码。
- `git diff --name-only` 确认规范变更范围与变更记录一致。

#### Scenario: 发现上下位文档冲突

- **WHEN** 开发者发现本规范与 `AGENT.md`、需求、设计、测试或计划文档存在矛盾
- **THEN** 停止编码，在“已知冲突与裁决”登记冲突点、以谁为准和处理方式，并在获得用户确认后再继续

#### Scenario: 修改本规范

- **WHEN** 需要新增、删除或修改任一规范条款
- **THEN** 同步更新“变更记录”，运行 `openspec validate --specs --strict`，并在评审中说明影响范围

### Requirement: 代码规范

Agent-mini 的 Python 代码 MUST 遵守 Python 3.11 基线、类型注解、异常边界、异步与资源释放规则。

**语言与风格基线**

1. Python 版本不低于 3.11（`NFR-COMPAT-01`），ruff `target-version = "py311"`；不得使用 3.12+ 才有的语法。
2. 遵循 PEP 8 与 PEP 257；docstring 采用 Google 风格；源码统一 UTF-8、4 空格缩进、双引号。
3. 唯一格式化工具为 `ruff format`；禁止同时引入 black、isort、flake8 或 autopep8。
4. 包内不建 `src/` 层；`agent_mini/` 直接位于仓库根目录（`Docs/DESIGN.md` §2.2）。

**类型注解**

1. 所有公共函数、方法、构造器的参数与返回值必须有类型注解；私有函数在类型不明显时同样必须标注。
2. 公共 API 禁止裸 `dict`、`list`、`tuple`，必须写元素类型，如 `list[Message]`、`Mapping[str, object]`。
3. `Any` 只允许出现在外部协议边界，且必须在同一行或上一行写明原因；禁止用 `Any` 逃避建模。
4. 禁用裸 `# type: ignore`；必须写成 `# type: ignore[错误码]` 并在行尾说明原因。
5. `mypy` 对 `agent_mini/` 启用 `strict`；测试目录可放宽，但不得完全不检查。模块级豁免必须写在 `pyproject.toml` 并注明理由。

**异常使用**

1. 禁止裸 `except:`；禁止 `except Exception: pass`；只捕获当前层能处理的异常。
2. 重新抛出必须保留原因：`raise NewError(...) from exc`；禁止丢弃原始 traceback。
3. 自定义异常统一继承 `AgentError` 及其子类（见“错误处理规范”）；禁止用 `Exception` 代替业务错误。
4. 工具层必须把内部异常转为 `ToolResult(ok=False, ...)`，不得向上抛出（`Docs/DESIGN.md` §3.3）。
5. 不用异常做正常分支控制；可预期失败用返回值或错误码表达。

**异步与同步**

1. 所有网络、数据库、文件 I/O 使用异步接口；禁止在协程中调用 `time.sleep`、`requests`、同步 Redis/Mongo/MySQL 客户端。
2. 无法避免的同步阻塞调用必须放进 `asyncio.to_thread()`，并在注释中说明原因。
3. 所有外部调用必须设置超时；禁止无限等待。并发使用 `asyncio.TaskGroup` 或显式收集任务，禁止无人持有的 `create_task`。
4. 捕获 `asyncio.CancelledError` 后必须重新抛出，不得吞掉取消信号。
5. CPU 密集且耗时的逻辑必须评估是否放到线程/进程，不得阻塞事件循环。

**资源释放**

1. 文件、HTTP 客户端、Redis/Mongo/MySQL 连接必须用 `with` 或 `async with` 管理，或在应用 `lifespan` 中统一关闭。
2. 禁止在模块导入时创建连接、读取文件或发起请求；禁止模块级可变客户端单例。
3. 写文件使用临时文件 + `os.replace` 的原子写（`Docs/DESIGN.md` §3.3），失败不得留下半成品。
4. 测试中的临时文件使用 `tmp_path`，结束后自动清理，不污染仓库。

**依赖注入**

1. 业务对象通过构造器注入依赖；跨层边界优先使用 `Protocol` 定义契约，便于测试替身（`Docs/DESIGN.md` §3.4、§3.8）。
2. 组合根只允许出现在 `agent_mini/interface/` 或 S21 的 `config/container.py`；业务模块内部禁止自行创建全局容器。
3. 禁止 service locator、全局单例注册表和“在函数内部 import 容器再取依赖”的写法。
4. ADR-004 允许 S00–S20 在配置层临时直读环境变量；S21 必须收敛到 `config/`，并在 `Docs/DESIGN.md` 登记。

**禁止事项**

| 禁止项 | 说明 |
| --- | --- |
| 引入被禁 Agent 框架 | 见 `AGENT.md` §9 与 `Docs/DESIGN.md` §6，含间接依赖 |
| `eval` / `exec` / `__import__` 处理外部输入 | calculator、工具参数、文件内容一律禁止 |
| `pickle` 反序列化不可信数据 | 需要序列化时使用 JSON |
| `subprocess` 且 `shell=True` | 如确需子进程，必须参数化并评审 |
| 硬编码密钥、令牌、URL、模型名 | 密钥只从环境变量读取；可配置项放配置层 |
| `print` 输出运行信息 | 统一使用结构化日志（见“日志规范”） |
| 通配符导入、相对导入 | 见“导入规范” |
| 可变默认参数 | 使用 `None` + 函数内初始化 |
| 用 `assert` 做运行时校验 | `assert` 只用于测试；生产校验用显式异常 |
| 注释掉的代码、死代码、调试残留 | 交给 Git 历史，不留在源码 |
| 魔法数字 | 除 `0`、`1`、`-1` 外必须命名常量 |
| 超长函数/模块 | 见“可读性规范” |
| 复制粘贴业务逻辑 | 抽公共函数或 Protocol，禁止三处以上重复 |

**执行时机**：S00 建立包骨架时；每次新增或修改 Python 文件时；重构时；代码评审时。

**验证方式**：

- `ruff format --check .`、`ruff check .`、`mypy agent_mini` 全部通过（S00 配置后）。
- 用 `grep`/评审检查禁用项：`eval(`、`exec(`、`shell=True`、`print(`、`except:`、`# type: ignore`（无错误码）。
- 评审确认无模块级 I/O、无未关闭客户端、无被禁框架依赖。
- `pytest` 全绿且资源泄漏用例（TC-L5-006）通过。

#### Scenario: 新增模块使用同步阻塞调用

- **WHEN** 评审发现协程中直接调用 `requests`、`time.sleep` 或同步数据库客户端
- **THEN** 必须改为异步客户端或 `asyncio.to_thread()`，否则不予合并

#### Scenario: 代码使用动态执行处理外部输入

- **WHEN** 代码对工具参数、文件内容或模型输出使用 `eval`、`exec` 或 `__import__`
- **THEN** 直接判定为 P0 缺陷并拒绝合并，除非属于已批准的独立安全设计

### Requirement: 格式化与静态检查规范

仓库 MUST 以 `pyproject.toml` 为唯一工具配置源，并在 S00 落地 ruff 与 mypy 门禁。

**ruff 基线配置**

S00 必须在 `pyproject.toml` 落地以下等价配置；实际键名以安装的 ruff 版本为准，若某规则不可用必须记录替代检查。

```toml
[tool.ruff]
target-version = "py311"
line-length = 100
src = ["agent_mini", "tests"]

[tool.ruff.lint]
select = [
    "E", "W", "F", "I", "N", "UP", "B", "SIM", "C4",
    "RET", "ANN", "D", "TID", "RUF", "C90",
    "PLR0911", "PLR0912", "PLR0913", "PLR0915", "PLR1702",
]
ignore = [
    "D107", "D203", "D213", "D400", "D401", "D403", "D415", "D417",
    "RUF001", "RUF002", "RUF003",
]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["ANN", "D"]
"**/__init__.py" = ["F401"]

[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.ruff.lint.pylint]
max-args = 5
max-branches = 12
max-returns = 6
max-statements = 50
max-nested-blocks = 3

[tool.ruff.lint.isort]
known-first-party = ["agent_mini"]

[tool.ruff.lint.flake8-tidy-imports]
ban-relative-imports = "all"

[tool.ruff.format]
quote-style = "double"
```

**规则说明**

1. `E`/`W`/`F` 覆盖语法、行宽、未使用变量与导入；`I` 负责导入排序。
2. `N` 负责命名；`UP` 负责 Python 版本升级写法；`B` 捕获常见 bug；`SIM` 简化冗余逻辑。
3. `RET` 检查多余赋值与 `else`；`ANN` 强制类型注解；`D` 检查 docstring 存在性与格式。
4. `TID` 禁止相对导入；`RUF` 捕获 Ruff 特有风险；`C90` 限制圈复杂度。
5. `PLR0911/0912/0913/0915/1702` 分别限制返回数、分支数、参数数、语句数、嵌套块数。
6. 忽略 `D400`/`D403`/`D415`/`D417` 与 `D401`：中文 docstring 的句号、首字母大写、结尾标点与逐参数说明不适用；docstring 的存在性与结构仍由其他 `D` 规则检查。忽略 `RUF001–003` 是因为中文注释中的全角标点属于有意使用。
7. `D107` 只对简单 `__init__` 放宽；含校验、I/O 或副作用的 `__init__` 仍必须写 docstring。

**mypy 基线配置**

```toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_unused_ignores = true
show_error_codes = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
disallow_incomplete_defs = false
```

**门禁命令与顺序**

```text
ruff format --check .
ruff check .
mypy agent_mini
pytest
pytest --cov=agent_mini --cov-report=term-missing --cov-fail-under=80
```

1. 前一条命令失败不得继续宣称后一条通过；CI 不允许 `|| true`、不允许跳过。
2. 覆盖率命令在 S00 配置 `pytest-cov` 后生效；未配置前只能记录“未执行”，不得写“通过”。
3. `# noqa` 必须带规则码与原因，例如 `# noqa: E501  # 长 URL 不可截断`；禁止裸 `# noqa`。
4. `# type: ignore` 必须带错误码与原因；禁止全局关闭 mypy 规则。
5. 禁止在源码中写 `# fmt: off` 绕过格式化，除非评审同意并注明原因。

**落地状态**

截至 2026-10-22，仓库尚无 `pyproject.toml`、`agent_mini/` 与 `tests/`，上述配置尚未生效；本规范不宣称 ruff、mypy、pytest 已通过。S00 必须完成落地，并把真实命令写入 `README.md`（ISSUE-008）。

**执行时机**：S00 工程基线；每次提交前；CI；依赖升级或规则调整后。

**验证方式**：

- 本地与 CI 按上述顺序执行，全部退出码为 0。
- `ruff check --show-settings` 或配置审阅确认关键阈值生效。
- 评审确认没有无理由的 `noqa`、`type: ignore`、`fmt: off`。
- S00 验收：`pip install -e .` 成功、`pytest` 至少 1 个 smoke 用例通过、`ruff check` 零告警。

#### Scenario: S00 工程基线验收

- **WHEN** S00 完成包骨架与工具配置
- **THEN** `pip install -e .`、`pytest`、`ruff check` 均通过，且 `README.md` 中存在可直接执行的命令

#### Scenario: 使用无原因的质量豁免

- **WHEN** 代码出现裸 `# noqa`、裸 `# type: ignore` 或无说明的 `# fmt: off`
- **THEN** 评审必须打回，要求补充规则码与原因，或修复根因

### Requirement: 可读性规范

所有源码 MUST 以“可逐行展示、可逐行讲解”为默认目标，并满足下列可量化限制。

**硬性指标**

| 编号 | 指标 | 上限/要求 | 自动检查 | 人工评审 |
| --- | --- | --- | --- | --- |
| R-01 | 单行长度 | ≤ 100 字符（含注释与 docstring） | ruff `E501` | 检查是否横向滚动 |
| R-02 | 每行语句数 | 1 条；禁止分号与单行复合语句 | ruff `E701`/`E702`/`E703` | 逐行讲解时不得一行多义 |
| R-03 | 嵌套深度 | ≤ 3 层（`if`/`for`/`while`/`try` 合计） | ruff `PLR1702` | 超过则用守卫语句或抽函数 |
| R-04 | 函数物理行数 | ≤ 50 行（不含空行与签名） | 无 | 评审计数 |
| R-05 | 函数语句数 | ≤ 50 条 | ruff `PLR0915` | 评审确认职责单一 |
| R-06 | 函数分支数 | ≤ 12 条 | ruff `PLR0912` | 评审确认可读 |
| R-07 | 函数参数数 | ≤ 5 个 | ruff `PLR0913` | 超过则封装配置对象 |
| R-08 | 函数返回点数 | ≤ 6 个 | ruff `PLR0911` | 超过则拆分决策 |
| R-09 | 模块行数 | ≤ 500 行 | 无 | 按职责拆分 |
| R-10 | 连续空行 | ≤ 2 行 | `ruff format` | 空行用于分组，不用于凑长度 |
| R-11 | 布尔条件数 | ≤ 3 个 | 无 | 超过则提取命名变量 |
| R-12 | 行内注释长度 | ≤ 40 个字符 | 无 | 见“注释规范” |
| R-13 | 魔法数字 | 只允许 `0`、`1`、`-1` | 无 | 其余必须命名常量 |

**单行只做一件事**

1. 一行只表达一个动作：赋值、调用、判断、返回各自独立成行。
2. 禁止 `a = 1; b = 2`、`if x: y()`、`try: ... except: ...` 写在一行。
3. 禁止在参数列表、列表/字典字面量中塞入多步计算；先命名中间变量，再调用。
4. 禁止用 `and`/`or` 的短路副作用代替 `if`；禁止用三元表达式嵌套表达多分支。

**嵌套与函数**

1. 优先使用守卫语句提前返回，减少 `else` 层级；`return` 之后禁止再写 `else`（ruff `RET505`）。
2. 嵌套超过 3 层必须抽取函数、提前返回或改用查表/策略；不得靠缩小字号或压缩空行“解决”。
3. 函数只承担一个职责；超过 50 行、50 条语句或 12 个分支必须拆分。
4. 参数超过 5 个时改用 dataclass / pydantic 模型 / 配置对象；布尔参数必须使用关键字调用。
5. 模块超过 500 行按职责拆分；不得用 `# region` 掩盖职责混杂。

**表达式与调用换行**

1. 链式调用超过 2 段，或整行超过 100 字符时，每个 `.method()` 独占一行，点号置于行首。
2. 调用参数超过 3 个，或整行超过 100 字符时，每个参数独占一行，末尾保留逗号。
3. 嵌套调用不超过 2 层；更深的调用先拆成命名变量。
4. 长布尔表达式拆成多个命名布尔变量；禁止把 4 个以上条件塞进一个 `if`。
5. 字典/列表字面量超过 3 项且行长超限时，每项独占一行。

**空行分组**

1. 顶层类/函数之间空 2 行；类内方法之间空 1 行。
2. 同一函数内用 1 个空行分隔“准备、执行、返回”等逻辑段；禁止连续 3 个以上空行。
3. 空行服务于阅读分组，不得用空行制造“看起来很短”的假象。

**优先显式**

1. 有返回值语义的函数必须显式 `return`；禁止靠表达式语句“顺带”产生结果。
2. 布尔/None 参数必须显式写关键字，如 `execute(call, dry_run=True)`，禁止位置布尔。
3. 变量名必须自解释；禁止 `data`、`tmp`、`res`、`obj` 这类无信息名，除非作用域仅 1–2 行且含义显然。
4. 判断 `None` 用 `is None` / `is not None`；不要把“假值”与“缺失”混为一谈。
5. 禁止过度压缩：不使用海象运算符嵌套、列表推导式副作用、`map/filter` 嵌套三层等“炫技”写法。

**执行时机**：编码时；重构时；代码评审时；性能优化后仍需保持可读性。

**验证方式**：

- 自动：`ruff format --check .` 与 `ruff check .` 覆盖 R-01、R-02、R-03、R-05、R-06、R-07、R-08、R-10。
- 人工：评审按 R-04、R-09、R-11、R-12、R-13 逐项检查，并在评审记录中标注不符合项。
- 抽样：每个阶段至少抽 2 个最长函数与 1 个最深嵌套文件做逐行讲解；讲不清即打回。
- 不得以“以后重构”放行超限代码；超限必须在本阶段内拆分。

#### Scenario: 函数超过可读性上限

- **WHEN** 评审发现函数超过 50 行、50 条语句、12 个分支或 3 层嵌套
- **THEN** 必须在本阶段内拆分或改用守卫语句，并在测试全绿后重新提交评审

#### Scenario: 单行承载多个动作

- **WHEN** 代码出现分号、单行 `if`、单行 `try` 或一行内多步计算
- **THEN** 必须拆成多行，每行只保留一个动作

### Requirement: 注释规范

代码注释与 docstring MUST 默认使用中文，并保持简洁、准确、必要。

**语言与风格**

1. 注释、docstring、TODO/FIXME 默认中文；标识符、协议字段、错误码、命令保留英文。
2. 禁止中英混排的整句；技术术语可保留英文，但句子主体必须是中文。
3. 使用中文全角标点；禁止表情符号、ASCII 装饰画、分隔线注释。
4. 注释解释“为什么”和“契约”，不复述代码“做了什么”。
5. 注释必须与代码同步修改；注释与代码不一致视为缺陷，默认按 P2 处理，涉及安全/资金/数据时按 P1。

**docstring**

1. 每个模块必须有 docstring（`D100`），用 1–3 行说明职责与边界，禁止写变更日志。
2. 每个公共类、公共函数、公共方法必须有 docstring（`D101`/`D102`/`D103`）。
3. 含校验、I/O、副作用或非显然逻辑的 `__init__` 必须有 docstring；简单数据类可省略（`D107` 已放宽）。
4. 采用 Google 风格；`Args`、`Returns`、`Raises` 只在需要时出现，禁止重复类型注解。
5. docstring 首行不超过 50 个字符，说明“做什么/返回什么”；需要时再空一行写细节。
6. 公共 API 必须写清：前置条件、返回值语义、可能抛出的异常、副作用。
7. 禁止“获取名称”“设置值”这类复述函数名的 docstring；没有增量信息就不写。

**行内注释**

1. 行内注释优先放在代码上方，并与代码同缩进；仅单位、常量、短说明可使用行尾注释。
2. 行内注释不超过 1 行、40 个字符；超过时改为上方多行说明或抽命名变量。
3. 一个逻辑段只在必要处写 1 条注释；禁止逐行注释。
4. 禁止注释掉的代码、调试输出、临时开关；这些必须删除或改为正式配置。
5. 禁止自动生成的样板注释、`# noqa` 式无信息注释、与代码矛盾的过期注释。

**TODO / FIXME**

| 类型 | 格式 | 要求 |
| --- | --- | --- |
| TODO | `# TODO(owner, YYYY-MM-DD): 原因与预期动作` | 必须有负责人、到期日、可执行动作 |
| FIXME | `# FIXME(ISSUE-012): 现象与修复方向` | 必须关联 `Docs/ISSUE.md` 编号 |

1. 禁止裸 `TODO`、`FIXME`、`XXX`、`HACK`。
2. 到期未处理的 TODO 必须在阶段收口时转为 ISSUE 或删除。
3. TODO 不得用于掩盖未完成的验收项；未完成项必须留在 OpenSpec tasks 或 ISSUE 中。

**执行时机**：写代码时；修改行为时同步注释；重构时；代码评审时；阶段收口检查 TODO。

**验证方式**：

- 自动：ruff `D` 规则检查模块/类/函数 docstring 存在性与基本格式。
- 自动/半自动：`grep -RInE "TODO|FIXME|XXX|HACK"` 检查格式与到期日。
- 人工：按 C-01–C-08 检查语言、长度、必要性、准确性、是否复述代码、是否残留注释代码。
- 注释与实现不一致时，测试用例或评审记录必须能指出具体行号。

#### Scenario: 公共函数缺少 docstring

- **WHEN** 新增公共函数没有 docstring 或 docstring 为空
- **THEN** ruff `D103` 失败，评审不得放行

#### Scenario: 注释与代码不一致

- **WHEN** 评审发现注释描述的行为与实际代码不符
- **THEN** 在同一提交内修正注释或代码，并记录为缺陷；不得只改注释掩盖错误实现

### Requirement: 命名规范

所有标识符、文件、配置键与编号 MUST 按下表命名，禁止同义多写。

**标识符与文件**

| 对象 | 规则 | 正例 | 反例 |
| --- | --- | --- | --- |
| 包 | 小写 snake_case，短名词 | `agent_mini` | `AgentMini` |
| 模块/文件 | 小写 snake_case，名词或名词短语 | `token_counter.py` | `TokenCounter.py`、`utils.py` |
| 类 | PascalCase，名词 | `LLMClient`、`ToolRegistry` | `llm_client`、`IUserRepo` |
| 异常类 | PascalCase；新增默认 `Error` 后缀；既有 `ContextTooLarge` 保留 | `SandboxError`、`ContextTooLarge` | `ContextException` |
| 函数/方法 | 小写 snake_case，动词开头 | `build_context`、`resolve_path` | `doStuff`、`handle` |
| 谓词函数 | `is_` / `has_` / `can_` 前缀 | `is_expired`、`has_tool_calls` | `check_expired` |
| 异步函数 | 与同步函数同规则，不加 `async_` 前缀 | `fetch_messages` | `async_fetch_messages` |
| 工具名 | 小写 snake_case，动词或动词_名词，全局唯一 | `read_file`、`write_file` | `readFile`、`file-reader` |
| 变量 | 小写 snake_case | `tool_call_id` | `toolCallId` |
| 常量 | 大写 UPPER_SNAKE | `MAX_STEPS` | `maxSteps` |
| 私有成员 | 单下划线前缀 | `_client`、`_parse_response` | `private_client` |
| 名称修饰 | 双下划线仅用于有意的名称改编 | `__slots__` | 随意 `__private` |
| 类型参数 | 单个大写字母或描述性 PascalCase | `T`、`MessageT` | `t` |

内置工具名固定为 `calculator`、`time`、`todo`、`read_file`、`write_file`、`search`（`Docs/DESIGN.md` §3.3），不得改名；新增工具名必须全局唯一，并与 `@tool` 名称、JSON Schema 的 `function.name` 完全一致。

`ContextTooLarge` 是 `Docs/DESIGN.md` 与 `Docs/TESTING.md` 已使用的名称，按既有契约保留，不强制改名；新增异常默认以 `Error` 结尾。

**禁止的命名**

1. 禁止 `utils`、`common`、`helpers`、`misc`、`base`（除非确为抽象基类）作为包/模块名。
2. 禁止单字母变量，循环下标 `i`/`j`/`k`、坐标 `x`/`y`、异常 `exc` 除外。
3. 禁止拼音命名（`yonghu`）、无意义缩写（`usr`、`mgr`）、版本后缀（`_v2`、`_new`、`_final`）。
4. 禁止文件名含空格、中文、大写（Python 源文件）；`Docs/` 既有大写文件名保持不动。
5. 禁止同一概念多个名字（`session_id` / `sid` / `sessionId` 只能保留一个）。

**允许的通用缩写**

只允许 `id`、`url`、`api`、`llm`、`db`、`ctx`、`msg`、`req`、`resp`；其余缩写必须写全。领域术语（如 `mongo`、`redis`、`mysql`）按官方拼写。

**测试命名**

1. 测试文件：`tests/<层>/<模块>/test_<被测模块>.py`，与 `agent_mini/` 镜像。
2. 测试函数：`test_<被测行为>_<场景>_<预期>`，全小写 snake_case，例如 `test_resolve_rejects_parent_escape`。
3. 禁止 `test_1`、`test_ok`、`test_case2` 这类无信息名。
4. 夹具：工厂夹具用 `make_*`，假实现用 `fake_*`，固定数据用 `sample_*`；禁止 `mock1`、`fixture2`。

**配置、错误码与日志**

| 对象 | 规则 | 示例 |
| --- | --- | --- |
| YAML 配置键 | 小写 snake_case | `max_context_tokens` |
| 环境变量 | 大写 UPPER_SNAKE | `DEEPSEEK_API_KEY` |
| 公共错误码 | 大写 UPPER_SNAKE | `CONTEXT_TOO_LARGE` |
| 工具错误码 | 小写 snake_case | `invalid_arguments` |
| 日志事件 | 小写 snake_case，点号分层 | `memory.degraded` |
| 日志字段 | 小写 snake_case | `duration_ms` |
| OpenSpec capability | 小写 kebab-case | `engineering-standards` |
| OpenSpec change-id | 小写 kebab-case | `add-tool-search` |

**文档与编号**

| 对象 | 规则 | 示例 |
| --- | --- | --- |
| 阶段 | `S` + 两位数字 | `S00`、`S21` |
| 功能需求 | `FR-<模块>-<两位序号>` | `FR-LLM-01` |
| 非功能需求 | `NFR-<类别>-<两位序号>` | `NFR-SEC-01` |
| 验收标准 | `AC-<两位序号>` | `AC-01` |
| 测试用例 | `TC-L<层>-<三位序号>` | `TC-L1-001` |
| 真实验收 | `TC-LIVE-<三位序号>` | `TC-LIVE-001` |
| 工程 smoke | `TC-SMOKE-<三位序号>` | `TC-SMOKE-001` |
| 问题 | `ISSUE-<三位序号>` | `ISSUE-001` |
| Prompt 记录 | `Prompt <两位序号>` | `Prompt 01` |

**Commit 类型**

引用 `AGENT.md` §5.2，type 只允许 `feat`、`fix`、`docs`、`test`、`refactor`、`perf`、`chore`、`build`、`ci`；本规范不新增 type，也不允许自造类型。

**执行时机**：新建任何标识符、文件、配置键、错误码、编号时；重命名时；代码评审时。

**验证方式**：

- 自动：ruff `N` 规则检查类名、函数名、变量名、模块名；`I` 检查导入别名。
- 人工：按“禁止的命名”逐项检查；搜索同一概念是否出现多个名字。
- 重命名必须同步更新导入、文档、测试与日志字段；`pytest` 全绿后提交。

#### Scenario: 新增无信息模块名

- **WHEN** 新增 `agent_mini/utils.py`、`common.py` 或 `helpers.py`
- **THEN** 评审必须拒绝，要求按实际职责命名并归入既有分层

#### Scenario: 同一配置出现两个环境变量名

- **WHEN** 代码同时读取 `DEEPSEEK_API_KEY` 与任何别名（如历史写法 `LLM_API_KEY`）
- **THEN** 评审必须拒绝，要求统一为 `DEEPSEEK_API_KEY` 并在 README/`.env.example` 登记

### Requirement: 目录规范

仓库文件 MUST 按下述目录职责放置，禁止在根目录或错误分层新增业务文件。

**目录树（目标形态）**

```text
agent-mini/
├─ AGENT.md
├─ README.md
├─ MEMORY.md
├─ .gitignore
├─ pyproject.toml              # S00 创建
├─ Docs/
│  ├─ REQUIREMENT.md
│  ├─ DESIGN.md
│  ├─ TESTING.md
│  ├─ PLAN.md
│  ├─ PROMPT.md
│  └─ ISSUE.md
├─ openspec/
│  ├─ config.yaml
│  ├─ specs/
│  │  └─ engineering-standards/spec.md
│  └─ changes/
│     └─ archive/
├─ agent_mini/                 # S00 创建，分层见 DESIGN §2.2
│  ├─ __init__.py
│  ├─ config/
│  ├─ llm/
│  ├─ runtime/
│  ├─ tools/
│  │  └─ builtin/
│  ├─ memory/
│  ├─ context/
│  ├─ systemdb/
│  ├─ interface/
│  └─ observability/
├─ tests/                      # S00 创建
│  ├─ conftest.py
│  ├─ unit/
│  ├─ contract/
│  ├─ integration/
│  ├─ e2e/
│  ├─ nonfunctional/
│  └─ fixtures/
├─ Data/                       # 运行数据、沙箱数据、临时数据
├─ Script/                     # 仓库级脚本
├─ Backend/                    # 占位目录，不放业务代码
└─ Frontend/                   # 占位目录，不放业务代码
```

**目录职责**

| 目录/文件 | 放什么 | 禁止 |
| --- | --- | --- |
| 仓库根 | 入口文档、`pyproject.toml`、`.gitignore`、顶层目录 | 业务 `.py`、临时脚本、数据文件、密钥 |
| `Docs/` | 需求、设计、测试、计划、Prompt、Issue | 代码、测试、运行数据；不得重命名既有基线文件 |
| `openspec/` | `config.yaml`、`specs/`、`changes/`、`changes/archive/` | 业务代码；归档后不得手改历史 change |
| `agent_mini/` | 生产包，按 DESIGN §2.2 分层 | 测试代码、脚本、数据、根级杂项模块 |
| `tests/` | L1–L5、LIVE、fixtures、conftest | 生产代码、真实密钥、生产数据 |
| `Data/` | 本地运行数据、沙箱根目录、临时文件 | 源码、测试、密钥、可提交的成品数据 |
| `Script/` | 初始化、检查、迁移、运维脚本 | 被 `agent_mini` 导入的业务逻辑、密钥 |
| `Backend/` | 仅占位 `.gitkeep` | 任何业务代码（NG-03） |
| `Frontend/` | 仅占位 `.gitkeep` | 任何业务代码（NG-03） |

**`agent_mini/` 分层与依赖方向**

| 子包 | 职责 | 允许依赖 |
| --- | --- | --- |
| `config/` | 配置模型、加载、DI 容器 | 标准库、pydantic；不得依赖业务模块 |
| `observability/` | 日志、trace、异常与错误码 | 标准库；不得依赖业务模块 |
| `llm/` | 模型协议、请求/响应、LLM 错误 | `config`、`observability` |
| `tools/` | 注册表、沙箱、六个内置工具 | `config`、`observability`、`sandbox` |
| `memory/` | Redis 短时、Mongo 中期、存储协议 | `config`、`observability` |
| `context/` | 拼接、token 计数、整轮裁剪 | `config`、`observability`、`memory`（只读） |
| `systemdb/` | MySQL 表、仓储、系统信息与审计 | `config`、`observability` |
| `runtime/` | ReAct 主循环、结果、安全阀 | `llm`、`tools`、`memory`、`context`、`systemdb`、`observability` |
| `interface/` | FastAPI 应用与 HTTP 边界 | `runtime`、`systemdb`、`config`、`observability` |

硬约束：依赖只能指向下层；`config`、`observability`、`systemdb` 为叶子模块，不得反向依赖业务模块（`Docs/DESIGN.md` §4、`NFR-MAINT-02`）。

**新增文件放置规则**

| 新增内容 | 放置位置 | 同步动作 |
| --- | --- | --- |
| 新工具 | `agent_mini/tools/builtin/<name>.py` | 注册工具 + 更新 `Docs/DESIGN.md` 工具表 + `tests/unit/tools/test_<name>.py` |
| 新 LLM 错误 | `agent_mini/llm/errors.py` | 更新错误码映射与测试 |
| 新公共异常/错误码 | `agent_mini/observability/errors.py` | 更新 `Docs/DESIGN.md` §3.7 与测试 |
| 新配置项 | `agent_mini/config/models.py` | 更新 `.env.example`（如敏感）+ README + 测试 |
| 新 HTTP 路由 | `agent_mini/interface/http.py` | 更新 `Docs/DESIGN.md` §3.6 与 L4 用例 |
| 新脚本 | `Script/<name>.ps1` 或 `Script/<name>.sh` | README 写明用法与前置条件 |
| 新文档 | `Docs/<TOPIC>.md` | 更新相关索引或引用 |
| 新规范/能力规格 | `openspec/specs/<capability>/spec.md` | `openspec validate --specs --strict` |
| 新测试 | `tests/<层>/<模块>/test_<模块>.py` | 与实现同 commit |

**禁止出现的位置**

1. 根目录 `*.py`（脚本放 `Script/`，源码放 `agent_mini/`）。
2. `agent_mini/tests/`、`tests/agent_mini/`（测试与源码不得互相嵌套）。
3. `Docs/`、`Data/`、`openspec/` 下的 `.py` 业务文件。
4. `Backend/`、`Frontend/` 下的任何业务代码。
5. 被 `.gitignore` 覆盖的 `__pycache__/`、`.venv/`、`dist/`、`*.log`、`.env` 不得入库。
6. 未经 DESIGN 登记的新顶层子包（如 `agent_mini/utils/`）。

**执行时机**：S00 建目录时；每次新增文件时；重构移动文件时；代码评审时。

**验证方式**：

- `git status --short` 与 `git ls-files` 检查是否出现禁止路径与产物。
- `openspec validate --specs --strict` 确认 OpenSpec 结构合法。
- 人工对照“目录职责”和“新增文件放置规则”评审。
- 依赖方向按 DESIGN §4 矩阵人工复核；出现反向导入即打回。

#### Scenario: 在仓库根目录新增业务脚本

- **WHEN** 新增根目录 `main.py`、`test.py` 或 `utils.py`
- **THEN** 评审必须拒绝，要求放入 `agent_mini/`、`tests/` 或 `Script/` 的正确位置

#### Scenario: 在占位目录写业务代码

- **WHEN** 在 `Backend/` 或 `Frontend/` 下新增 Python/前端业务代码
- **THEN** 评审必须拒绝，并指出需要先修改 `Docs/REQUIREMENT.md` 的非目标与架构

### Requirement: 测试规范

测试 MUST 遵循先红后绿、分层隔离、可重复与不伪造的原则，并引用 `AGENT.md` §2 与 `Docs/TESTING.md`。

**分层与目录**

| 层级 | 目录 | 外部依赖 | 标记 | 默认执行 |
| --- | --- | --- | --- | --- |
| L1 单元 | `tests/unit/` | 无，全部替身 | `unit` | 是 |
| L2 契约 | `tests/contract/` | `respx` 拦截 HTTP | `contract` | 是 |
| L3 集成 | `tests/integration/` | fakeredis / mongomock / MySQL 替身；真实服务显式开关 | `integration` | 是（替身） |
| L4 端到端 | `tests/e2e/` | HTTP 全链路 + mock 模型 | `e2e` | 是 |
| L5 非功能 | `tests/nonfunctional/` | 视用例 | `slow` | 否 |
| LIVE 真实验收 | `tests/live/` | 真实 DeepSeek API + 密钥 | `live` | 否，显式 opt-in |
| 工程 smoke | `tests/unit/test_smoke.py` | 无 | `unit` | 是 |

目录镜像规则：`agent_mini/tools/sandbox.py` → `tests/unit/tools/test_sandbox.py`（`Docs/TESTING.md` §2.2）。

**命名与结构**

1. 测试文件与函数命名见“命名规范”；禁止无信息编号。
2. 每个用例采用 given / when / then 三段，允许用注释分隔；一段只做一件事。
3. 一个用例只验证一个断言主题；失败信息必须能定位到行为，不得用“大杂烩”断言。
4. 异常用例使用 `pytest.raises(ExpectedError, match="...")`；禁止只写 `pytest.raises(Exception)`。
5. 异步用例使用 `pytest-asyncio`；禁止在异步测试中调用 `time.sleep` 或真实网络。
6. 禁止 `assert True`、条件断言、在测试中吞异常、为通过测试放宽断言。

**夹具与替身**

1. 夹具放 `tests/conftest.py` 或分层 `conftest.py`；跨层共享的夹具必须放在最近公共父目录。
2. 工厂夹具用 `make_*`，假实现用 `fake_*`，固定样本用 `sample_*`；禁止模块级可变夹具。
3. 只对**外部**依赖打桩：HTTP → `respx`；Redis → `fakeredis`；Mongo → `mongomock`；MySQL → 内存替身或显式集成开关。
4. 禁止 mock 被测对象自身；禁止用 mock 绕过真实业务分支。
5. 时间通过注入的 `Clock` 或固定时区控制；断言中禁止直接调用 `datetime.now()`。
6. 临时文件使用 `tmp_path`；禁止读写仓库外真实路径（沙箱破坏类用例必须在 `tmp_path` 内构造）。

**测试数据**

1. 固定夹具放 `tests/fixtures/`；敏感数据使用明显假值，如 `sk-test-not-a-real-key`。
2. 禁止真实密钥、真实用户数据、生产数据、真实 API 响应正文入库。
3. 临时数据使用 `tmp_path` 并自动清理；测试结束不得污染 `Data/` 或仓库。
4. LIVE 用例的密钥只从环境变量读取；缺失时记录“未执行”，不得伪造通过。

**TDD 与回归**

1. 新功能先写失败测试，确认失败原因正确（断言失败而非 import/语法错误），再写最小实现。
2. 测试文件与被测实现必须出现在同一个 commit（`AGENT.md` §2）。
3. 修 bug 前先写复现测试；复现测试未失败不得改实现。
4. 禁止提交被 `skip`、`xfail`、注释掉的测试；平台差异必须显式标记并关联 ISSUE。
5. 禁止为通过测试放宽断言、删除用例、把失败改成 warning。
6. 覆盖率目标：新增代码行覆盖率 ≥ 80%（`NFR-TEST-01`、`AC-16`）；未覆盖行必须在评审中说明。

**执行时机**：写实现之前（红）；每次提交前；阶段 DoD；里程碑；修 bug 前；发布前。

**验证方式**：

- `pytest` 全绿；分层命令 `pytest -m unit`、`-m contract`、`-m integration`、`-m e2e`、`-m slow`、`-m live` 在 README 记录后可用。
- `pytest --cov=agent_mini --cov-report=term-missing --cov-fail-under=80` 达标。
- `git show --stat <commit>` 中测试文件与实现文件同时出现。
- 评审确认无 skip/xfail、无真实密钥、无网络依赖、时间可控。
- 当前测试命令尚未落地（ISSUE-008）；在 S00 写入 README 前，本规范不宣称任何 pytest 结果。

#### Scenario: 修复缺陷但没有复现测试

- **WHEN** 修复类提交只改实现，没有先失败后通过的复现测试
- **THEN** 评审必须打回，要求补测试并保留为回归用例

#### Scenario: 提交被跳过的测试

- **WHEN** 测试被 `skip`、`xfail` 或注释掉以掩盖失败
- **THEN** 直接判定为不合格；平台限制必须改为显式标记并登记 ISSUE

### Requirement: 错误处理规范

所有可预期失败 MUST 映射为稳定的 `AgentError` 子类与错误码，并在边界处转换，不得裸抛到进程外。

**异常体系**

1. 基类 `AgentError` 必须携带 `code`、`http_status`、`message`；禁止只抛字符串。
2. 子类至少覆盖：`ConfigError`、`LLMError`、`ToolError`、`SandboxError`、`ContextError`、`InputError`、`SystemDBError`（`Docs/DESIGN.md` §3.7）。
3. LLM 细分错误至少包括：`LLMAuthError`、`LLMBadRequestError`、`LLMTimeoutError`、`LLMRateLimitError`、`LLMServerError`、`LLMConnectionError`、`LLMProtocolError`、`LLMEmptyResponseError`、`LLMOutputTruncatedError`、`LLMOutputRejectedError`。
4. 上下文超限使用 `ContextTooLarge`；工具内部错误不抛到 Runtime，转为 `ToolResult`。
5. 禁止自定义异常继承 `BaseException`；禁止覆盖内置 `MemoryError` 等名称。
6. **阶段例外（S02–S19）**：`LLMError` 可作为临时根存在，但必须保留 `code/http_status` 与 `*Error` 命名，并在 S20 前迁移为 `AgentError` 子类；到期未迁移视为违反本条，例外自动失效。

**错误码分层**

| 层级 | 命名 | 示例 | 使用位置 |
| --- | --- | --- | --- |
| 公共错误 | 大写 UPPER_SNAKE | `CONTEXT_TOO_LARGE`、`INVALID_INPUT` | HTTP 响应、日志、异常对象 |
| 工具错误 | 小写 snake_case | `invalid_arguments`、`unknown_tool` | `ToolResult.error_code` |

禁止把两层错误码混写；新增错误码必须同时更新测试与文档。

**错误码映射**

| 错误码 | HTTP | 触发条件 |
| --- | --- | --- |
| `INVALID_INPUT` | 400 | 请求体缺失、类型错误、参数非法 |
| `CONTEXT_TOO_LARGE` | 400 | 不可裁剪内容仍超预算，本地拒绝请求 |
| `SANDBOX_VIOLATION` | 400 | 路径越界、绝对路径、符号链接逃逸 |
| `LLM_AUTH` | 502 | 上游鉴权失败（401/403） |
| `LLM_TIMEOUT` | 408 | 上游超时 |
| `LLM_RATE_LIMITED` | 429 | 上游限流 |
| `LLM_PROTOCOL_ERROR` | 502 | 响应结构、ID、终止原因不合法 |
| `LLM_EMPTY_RESPONSE` | 502 | 无有效文本/工具调用 |
| `LLM_OUTPUT_TRUNCATED` | 502 | `finish_reason=length` |
| `LLM_OUTPUT_REJECTED` | 502 | 内容过滤或明确拒绝 |
| `INTERNAL` | 500 | 未分类异常兜底 |

`ConfigError` 在启动阶段直接失败并输出缺失字段名，不进入 HTTP 映射；`SystemDBError`、记忆异常按降级处理，记录 WARNING，不阻断对话主链路。

**异常边界**

1. LLM 层：把 `httpx` 超时、HTTP 状态、协议解析失败转换为对应的 `LLMError` 子类；禁止把原始 `httpx` 异常透传到 Runtime。
2. Tool 层：捕获所有工具内部异常，返回带原 `call_id` 的结构化 `ToolResult`；禁止向上抛出（`FR-RT-06`）。
3. Runtime：只处理已分类异常；工具失败继续循环或收敛；安全阀中断必须补齐未完成 `call_id` 的结果。
4. Memory / SystemDB：不可用时降级并记录 `memory.degraded` / `systemdb.degraded`，不阻断响应。
5. Interface：统一把 `AgentError` 映射为 HTTP JSON；未知异常兜底 `INTERNAL/500`，响应只含 `code`、可读消息与 `trace_id`，不含 traceback、路径、SQL、密钥。
6. Config：缺失必填项启动即失败（`FR-CFG-01`、`AC-13`），错误信息包含字段名，不产生堆栈噪声。

**重试与副作用**

1. 仅 `429` 与 `5xx` 允许指数退避重试；`4xx`（除 429）不重试；超时不重试，交由 Runtime 收敛（`Docs/DESIGN.md` §3.1）。
2. 已产生工具副作用的调用不得自动重放；上下文超限时不得先调用 LLM 再报错。
3. 重试必须记录 `attempt`，不得伪装成新的 ReAct 步骤。

**禁止事项**

1. 禁止裸 `except:`、`except Exception: pass`、捕获后不记录也不处理。
2. 禁止在多层重复记录同一个异常；只在边界记录一次，避免日志噪声。
3. 禁止把异常消息直接拼接密钥、完整请求体、SQL 或文件绝对路径。
4. 禁止用 `assert` 做运行时输入校验；禁止用异常做正常分支控制。

**执行时机**：设计失败路径时；新增异常/错误码时；编码时；代码评审时；线上问题复盘时；S20 统一错误响应时。

**验证方式**：

- 单元测试覆盖错误映射（TC-L1-019）、工具异常（TC-L4-007）、上下文超限（TC-L4-012）。
- 评审确认每个 `raise` 都有明确错误码与 HTTP 状态，且未泄露内部信息。
- 日志检查确认同一异常只记录一次，4xx 不打印堆栈，5xx 才带 `exc_info`。
- 手工构造未知异常，确认响应为 `INTERNAL/500` 且含 `trace_id`、无 traceback。

#### Scenario: 未知工具或参数错误

- **WHEN** 模型请求未注册工具或参数不符合 Schema
- **THEN** 返回带原 `call_id` 的 `ToolResult(ok=False, error_code=unknown_tool/invalid_arguments)`，不执行 handler，允许模型修正

#### Scenario: 未分类异常逃逸

- **WHEN** 任意未预期异常到达 HTTP 边界
- **THEN** 返回 `INTERNAL/500` 与 `trace_id`，进程不退出，响应不含 traceback、路径或密钥

### Requirement: 日志规范

运行日志 MUST 为单行 JSON，并携带 `trace_id`；日志不得泄露密钥、原始推理或完整敏感载荷。

**格式与字段**

1. 每条日志是一行合法 JSON；禁止多行 JSON、Python repr、彩色控制字符。
2. 固定字段：`ts`（ISO8601 含时区）、`level`、`event`、`trace_id`；可用时补充 `session_id`、`step`、`duration_ms`、`error_code`。
3. 扩展字段使用小写 snake_case；禁止嵌套超大对象、禁止把异常对象直接序列化。
4. 日志通过标准库 `logging` + 自定义 JSON Formatter + `contextvars` 输出（`Docs/DESIGN.md` §3.7）；禁止引入 APM 或第三方日志框架。

**级别**

| 级别 | 用途 | 示例 |
| --- | --- | --- |
| DEBUG | 开发诊断，默认关闭 | 请求体字段计数、内部状态摘要 |
| INFO | 正常生命周期 | `request.started`、`request.completed`、`react.step` |
| WARNING | 降级、重试、可恢复异常 | `llm.retry`、`memory.degraded`、`systemdb.degraded` |
| ERROR | 请求失败、不可恢复异常 | `request.failed`、`llm.error` |
| CRITICAL | 进程无法继续 | 启动配置致命错误 |

1. 可预期的 4xx 输入错误用 WARNING 或 INFO，不使用 ERROR。
2. 5xx 与未分类异常用 ERROR，并带 `error_code`；仅未知异常带 `exc_info`。
3. 禁止用 ERROR 记录正常重试；禁止用 INFO 记录敏感载荷。

**事件命名**

1. 事件名使用小写 snake_case，点号分层，如 `memory.degraded`、`context.trimmed`、`token_counter.degraded`。
2. 已有事件名必须复用，不得同义多写；新增事件必须在本规范或 DESIGN 登记。
3. 建议事件：`request.started`、`request.completed`、`llm.request`、`llm.retry`、`llm.error`、`react.step`、`tool.invoked`、`tool.failed`、`context.trimmed`、`context.over_budget_after_trim`、`memory.degraded`、`systemdb.degraded`、`token_counter.degraded`。

**trace_id**

1. 在 HTTP 入口生成 `trace_id`（UUID4 或等价唯一值），一次请求一个。
2. 通过 `contextvars` 注入，贯穿 Interface → Runtime → LLM → Tool → Memory → SystemDB；跨异步边界不得丢失。
3. 每个 ReAct 步骤、每次工具调用、每次存储降级都必须携带同一个 `trace_id`。
4. 响应体返回 `trace_id`；禁止跨请求复用或伪造。

**脱敏**

1. 以下字段禁止原样输出：`api_key`、`authorization`、`password`、`token`、`secret`、`cookie`、`set-cookie`、`reasoning_content`。
2. 禁止记录完整 prompt、完整 messages、完整模型响应、完整工具参数/结果；只允许长度、数量、哈希或脱敏摘要。
3. 统一在 Formatter 层做脱敏过滤，值替换为 `***`；字段名本身可保留。
4. 日志、HTTP 响应、MySQL 审计、搜索召回均不得出现原始 reasoning；`Docs/DESIGN.md` §3.2.3 的约束优先。
5. 真实密钥只从环境变量读取；测试使用假密钥 `sk-test-not-a-real-key`。

**日志与错误的配合**

1. 只在异常边界记录一次；下层只抛出，不重复记录。
2. 4xx 记录 WARNING，包含 `error_code` 与 `trace_id`，不打印堆栈。
3. 未分类 5xx 记录 ERROR，带 `exc_info=True`，但 Formatter 必须脱敏。
4. 降级路径每个事件只记录一次，不按消息条数刷屏。

**禁止事项**

1. 禁止 `print()` 输出运行信息；禁止 `logging.basicConfig()` 在库模块中重复配置。
2. 禁止记录密钥、令牌、Cookie、Authorization、原始推理、完整用户消息。
3. 禁止在循环内逐条打印高频 DEBUG；需要时用采样或聚合。
4. 禁止用字符串拼接手工构造 JSON；使用结构化 `extra` 字段。

**执行时机**：新增日志事件时；编码时；代码评审时；线上问题复盘时；S19 落地时。

**验证方式**：

- 单元测试解析每条日志为合法 JSON，断言含 `trace_id`、`event`、`duration_ms`（TC-L1-020）。
- 脱敏用例注入唯一假密钥与私有 reasoning 标记，扫描日志/响应/MySQL，确认无泄漏（TC-L5-004）。
- 评审检查事件命名、级别、字段类型与禁止项。
- 手工触发一次工具调用，确认同一请求内 `trace_id` 一致。

#### Scenario: 日志行不是合法 JSON

- **WHEN** 任一日志行无法被 `json.loads` 解析，或缺少 `trace_id`
- **THEN** 测试失败，按 P0/P1 缺陷处理，不得上线

#### Scenario: 日志泄露密钥或原始推理

- **WHEN** 日志、响应或审计中出现完整假密钥、真实密钥或 `reasoning_content` 原文
- **THEN** 直接判定为 P0 安全缺陷，阻塞合并与发布

### Requirement: 依赖与配置规范

依赖与配置 MUST 单点声明、显式版本、密钥只从环境变量读取，禁止硬编码与双名并存。

**依赖声明**

1. 依赖统一声明在根目录 `pyproject.toml`（PEP 621）；运行依赖放 `[project].dependencies`，开发依赖放 `[project.optional-dependencies].dev`。
2. 禁止同时维护 `requirements.txt`、`setup.py`、`setup.cfg` 作为第二来源；如因部署必须生成，必须注明“由 pyproject 生成”，不得手工分叉。
3. 版本约束必须显式，禁止裸包名与 `*`；最低版本不得低于 `Docs/DESIGN.md` §1.1 的约束。
4. 新增依赖必须：在 PR/提交说明列出理由；确认不属于 `AGENT.md` §9 禁列；更新 `Docs/DESIGN.md` §1.1/§1.3；通过 `pip check`。
5. 禁止引入任何提供 Agent 循环、工具调度、记忆管理的框架；扫描命令见下方验证方式。
6. 禁止把依赖安装写进运行时代码；禁止 vendoring 第三方源码到 `agent_mini/`。

**配置边界**

| 类型 | 位置 | 示例 | 禁止 |
| --- | --- | --- | --- |
| 非敏感配置 | 根目录 `config.yaml`（S21 落地） | 模型名、超时、窗口 K、工具启停 | 密钥、令牌、个人隐私 |
| 敏感配置 | 环境变量 | `DEEPSEEK_API_KEY`、`REDIS_URL`、`MONGO_URI`、`MYSQL_DSN` | 写入 YAML、源码、测试夹具、日志 |
| 本地覆盖 | `.env`（不入库） | 本地开发值 | 提交 `.env`；只能提交 `.env.example` 占位 |
| Prompt 配置 | 外置文件（`FR-CFG-03`） | system prompt 文件路径 | 把 system prompt 硬编码进 Python |

1. 环境变量使用 UPPER_SNAKE；一个配置只允许一个正式名；DeepSeek 密钥统一为 `DEEPSEEK_API_KEY`，禁止 `LLM_API_KEY` 别名（C-02）。
2. `.env` 已被 `.gitignore` 覆盖；`.env.example` 只放 `***` 或空值，并写清用途。
3. 配置模型使用 `pydantic-settings`；启动即校验，缺失必填项抛 `ConfigError` 并指出字段名。
4. 禁止为密钥设置“空字符串可运行”的默认值；缺失即失败，除非该能力明确可降级。
5. 禁止在业务代码中散落 `os.getenv`；S21 后只允许 `config/` 读取环境变量。ADR-004 允许的临时读取点必须在 S21 删除。
6. 禁止硬编码 base_url、模型名、端口、超时、窗口大小、文件大小上限；这些必须来自配置或命名常量。
7. 配置优先级、默认值与热更新策略由 S21 在 `Docs/DESIGN.md` 登记；首版不支持热更新。

**密钥管理**

1. 真实密钥只从环境变量读取；代码、文档、测试、Prompt 记录中只保留脱敏占位。
2. 日志与响应中的 `api_key`、`authorization` 必须被脱敏过滤器替换。
3. 真实 API 验收唯一使用 `DEEPSEEK_API_KEY`；缺少密钥时记录“未执行”，不得伪造通过（`TC-LIVE-001/002`）。

**执行时机**：新增/升级依赖时；S00 建工程基线时；S21 配置收口时；部署前；代码评审时。

**验证方式**：

- `pip install -e .` 成功；`pip check` 无冲突。
- 被禁框架扫描为空：
  `grep -iE 'langgraph|openhands|openclaw|langchain|llamaindex|autogen|crewai|semantic-kernel|smolagents' pyproject.toml`
- `git check-ignore -v .env` 命中；`git ls-files` 不含 `.env`、`*.key`、`*.pem`。
- 启动缺失必填配置，确认 `ConfigError` 指出字段名且不启动服务（TC-L4-006）。
- 评审确认没有硬编码 URL、模型名、密钥或双环境变量名。

#### Scenario: 新增被禁 Agent 框架依赖

- **WHEN** `pyproject.toml` 出现 `langgraph`、`langchain`、`autogen` 等被禁包
- **THEN** 直接拒绝合并；例外必须走 `AGENT.md` §9 的审批与 ISSUE/ADR 记录

#### Scenario: 新增配置项未登记

- **WHEN** 代码新增环境变量或配置键，但未更新 `.env.example`、README 或 DESIGN
- **THEN** 评审必须打回，要求补齐文档与测试

### Requirement: 导入规范

导入 MUST 按标准库、第三方、本项目分组并全部使用绝对导入，禁止循环依赖与导入期副作用。

**导入顺序**

1. `from __future__ import annotations`（如使用）放在最前。
2. 标准库。
3. 第三方库。
4. 本项目 `agent_mini.*`。
5. 测试内部工具（仅测试文件）。

组与组之间空 1 行；组内按字母序；由 ruff `I` 自动排序，禁止手工维护顺序。

**绝对导入**

1. 统一使用绝对导入，如 `from agent_mini.llm.client import LLMClient`。
2. 禁止相对导入（`from .`、`from ..`）；ruff `TID252` 与 `ban-relative-imports = "all"` 必须通过。
3. 禁止 `sys.path.append`、`sys.path.insert` 或修改 `PYTHONPATH` 规避包结构。
4. 测试同样使用绝对导入 `from agent_mini...`，不得依赖当前工作目录。

**禁止事项**

1. 禁止 `from module import *`；禁止未使用导入；禁止重复导入。
2. 禁止在导入时执行 I/O、读环境变量、建连接、启动线程/任务。
3. 禁止在函数内部 import，除非：可选依赖缺失时降级、打破已确认的循环依赖；两种情况都必须写中文注释说明。
4. 禁止用 `# noqa: F401` 掩盖未使用导入；`__init__.py` 的导出例外必须配置在 `per-file-ignores`。
5. 禁止循环依赖；发现后必须通过 Protocol、依赖注入、下沉共享类型或延迟导入解决，不得用 `# noqa` 掩盖。

**TYPE_CHECKING 与可选依赖**

1. 仅用于类型检查的导入放在 `if TYPE_CHECKING:` 下，避免运行期开销与循环。
2. 需要前向引用时使用 `from __future__ import annotations`；同一模块保持风格一致。
3. 可选依赖（如 `tiktoken`）使用 `try/except ImportError`，记录 `token_counter.degraded` 并走降级路径；禁止静默失败。

**`__init__.py`**

1. `__init__.py` 只做稳定公共 API 的显式导出；必须定义 `__all__`（如导出）。
2. 禁止在 `__init__.py` 导入重型模块、执行 I/O 或初始化全局对象。
3. 禁止通过 `__init__.py` 反向导入上层模块，避免循环依赖。

**分层约束**

1. 导入方向必须符合 `Docs/DESIGN.md` §4 依赖矩阵；下层不得导入上层。
2. `config`、`observability`、`systemdb` 为叶子模块，不得导入 `runtime`、`interface`、`tools`、`memory`。
3. `interface` 只能作为组合根导入其他模块；其他模块不得导入 `interface`。
4. 发现反向导入必须在评审中打回，不得以“暂时可用”放行。

**执行时机**：新增模块时；重构移动文件时；S00 建包时；代码评审时。

**验证方式**：

- `ruff check --select I,TID .` 通过。
- `python -c "import agent_mini"` 成功（S00 后），无导入期副作用。
- 人工对照 DESIGN §4 矩阵检查反向导入与循环依赖。
- `pytest` 全绿，确认测试导入不依赖运行目录。

#### Scenario: 使用相对导入跨层引用

- **WHEN** 代码出现 `from ..runtime import Agent` 或类似相对导入
- **THEN** ruff `TID252` 失败，评审要求改为绝对导入并检查分层方向

#### Scenario: 出现循环依赖

- **WHEN** 两个模块互相导入，或以函数内 import 临时规避
- **THEN** 必须通过 Protocol、依赖注入或下沉共享类型解决，并补充回归测试

### Requirement: 评审与门禁

每个提交与阶段收口 MUST 通过自动化门禁和人工评审清单，任一项失败不得合并或进入下一阶段。

**自动化门禁**

```text
ruff format --check .
ruff check .
mypy agent_mini
pytest
pytest --cov=agent_mini --cov-report=term-missing --cov-fail-under=80
openspec validate --specs --strict
```

1. 顺序执行，前一条失败不得继续宣称后一条通过；CI 不允许 `|| true`。
2. 规范文件变更必须跑 `openspec validate --specs --strict`；行为变更还必须走 OpenSpec change 流程。
3. 当前仓库尚未落地工具配置，以上命令在 S00 前不可执行；不得伪造 CI 结果。

**人工评审清单**

| 编号 | 检查项 | 通过标准 | 检查方式 |
| --- | --- | --- | --- |
| CR-01 | 单功能单阶段 | 本次只交付一个可独立验收功能 | 对照 `Docs/PLAN.md` 阶段与 diff |
| CR-02 | 文档先行 | 需求/设计/测试/计划已同步 | 查看文档 diff 与 FR/TC 映射 |
| CR-03 | 可读性阈值 | R-01–R-13 全部满足 | 逐项对照“可读性规范” |
| CR-04 | 中文简洁注释 | 注释/docstring 中文、必要、不过期 | 抽查公共 API 与复杂分支 |
| CR-05 | 命名 | 标识符/文件/配置/编号符合规范 | 对照“命名规范” |
| CR-06 | 目录放置 | 新文件在正确目录，无根级源码 | 对照“目录规范” |
| CR-07 | 测试 | 先红后绿、无 skip、覆盖 ≥80% | `pytest` + diff |
| CR-08 | 错误处理 | 错误码/HTTP 状态/边界正确 | 对照“错误处理规范” |
| CR-09 | 日志 | JSON、trace_id、脱敏 | 抽查日志与测试 |
| CR-10 | 依赖 | 无被禁框架、无未声明依赖 | `pyproject.toml` + grep |
| CR-11 | 配置/密钥 | 无硬编码、无双名、无密钥入库 | grep + `git check-ignore` |
| CR-12 | 导入 | 绝对导入、无循环、无导入期副作用 | `ruff I,TID` + 人工 |
| CR-13 | 无死代码 | 无注释代码、无调试残留 | grep + 评审 |
| CR-14 | 安全 | 无 eval/exec/shell=True/路径越界 | 评审 + 安全用例 |
| CR-15 | 文档同步 | README/ISSUE/PROMPT 已更新 | 查看 diff |

**评审规则**

1. 评审意见必须引用本规范编号（R-xx、CR-xx）或 `AGENT.md` 条款，禁止只说“风格不好”。
2. 作者必须修复或登记例外；评审者不得静默改代码替代作者确认。
3. P0/P1 缺陷阻塞合并；P2 可延后但必须登记 ISSUE；P3 记录待办。
4. 阶段 DoD 除 `Docs/PLAN.md` §5.1 外，还必须满足本规范 CR-01–CR-15。

**执行时机**：每次提交前；每次 PR/合并前；阶段收口；里程碑评审；规范变更评审。

**验证方式**：

- CI 日志显示全部门禁通过；失败项必须修复后重跑。
- 评审记录包含逐项 CR 检查结果；缺项视为未评审。
- `git show --stat` 确认测试与实现同 commit、无跨阶段夹带。
- `openspec validate --specs --strict` 通过；行为变更存在对应 change。

#### Scenario: CI 门禁失败

- **WHEN** ruff、mypy、pytest、覆盖率或 OpenSpec 校验任一失败
- **THEN** 禁止合并或进入下一阶段，修复后重新运行全部门禁

#### Scenario: 评审提出主观风格意见

- **WHEN** 评审意见没有对应规范编号或文档条款
- **THEN** 作者可以要求评审者补充依据；不得以个人偏好替代规范

### Requirement: 规范变更与例外

本规范的修改 MUST 留痕、可验证，并对例外设置期限与审批。

**变更流程**

1. 修改正文必须同步更新“变更记录”，写清版本、日期、变更内容与原因。
2. 修改后运行 `openspec validate --specs --strict`；校验失败不得提交。
3. 影响代码行为的规范变更，按 `AGENT.md` §1 与 §6.1 先走文档/OpenSpec change；纯澄清性修改可作为 docs commit。
4. 变更必须评估对 S00–S21 的影响，并在 `Docs/PLAN.md` 或相关文档登记需要回填的阶段。
5. 禁止在实现代码中私自放宽规范；规范与实现冲突时先改规范或登记例外。

**版本与留痕**

1. 版本号采用 `v<主>.<次>`；破坏性变更升主版本，新增/澄清升次版本。
2. 每次变更保留历史行，不得删除旧记录；需要撤销时新增一条“撤销/回退”记录。
3. 变更提交信息使用 `docs(openspec): ...` 或 `docs(standards): ...`，正文说明影响范围。

**例外管理**

1. 例外必须登记在 `Docs/ISSUE.md`，包含：规则编号、原因、范围、负责人、到期日、审批人。
2. 例外默认不超过一个阶段；到期必须修复、续期或转为正式规范。
3. 安全、密钥、测试真实性、禁止 Agent 框架四类规则不得例外；必须修复。
4. 禁止口头例外、聊天中临时同意、代码注释中的“特批”；没有 ISSUE 记录视为违规。

**废弃与替代**

1. 规则废弃必须标注替代条款与迁移方式；不得直接删除后留下悬空引用。
2. 旧代码不因新规范立即失败，但必须在下一阶段重构窗口内收敛；新增代码立即适用。

**执行时机**：修改本规范时；批准例外时；阶段收口检查到期例外时；规范废弃/替代时。

**验证方式**：

- `git diff` 中正文与“变更记录”同时变化。
- `openspec validate --specs --strict` 通过。
- 评审确认例外有 ISSUE 编号、负责人、到期日与审批人。
- 阶段收口检查到期例外，未处理不得进入下一阶段。

#### Scenario: 例外没有到期日

- **WHEN** 例外记录缺少负责人、到期日或审批人
- **THEN** 视为无效例外，代码必须按规范修复后才能合并

#### Scenario: 修改规范但未更新变更记录

- **WHEN** 规范正文变化但“变更记录”未新增条目
- **THEN** 评审必须打回，要求补充版本、日期、变更内容与原因
