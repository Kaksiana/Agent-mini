# ISSUE <!-- omit in toc -->

> 开发过程中遇到的问题与解决方案。规则见 `AGENT.md` §4。
> 状态取值：`Open` / `Resolved` / `Wontfix`。

## 问题记录

### ISSUE-001 — 私有仓库在无权限账号下无法解析，报错与"仓库不存在"无法区分

- 日期：2026-10-21
- 现象：`gh repo clone Kaksiana/Agent-mini` 返回 `GraphQL: Could not resolve to a Repository with the name 'Kaksiana/Agent-mini'. (repository)`，退出码 1；当时 gh 活动账号为 `Ryan-0625`。
- 根因：仓库实际存在但为 **private**，`Ryan-0625` 不是协作者。GitHub 对"无权限的私有仓库"统一返回 404，与"仓库不存在"不可区分，导致误判为仓库未创建。
- 解决方案：用户执行 `gh auth login` 以 `Kaksiana` 登录，并 `gh auth switch --user Kaksiana` 切换活动账号。
- 验证方式：`gh auth status` 显示 `Kaksiana` 为 Active account；`gh api user --jq '.login'` 输出 `Kaksiana`；`gh repo view Kaksiana/Agent-mini` 返回 `visibility: PRIVATE`、`defaultBranch: main`。
- 状态：Resolved
- 关联提交：`17fb2e8`（初始化阶段）

### ISSUE-002 — 目标目录已存在，且克隆目标名大小写与本地目录不一致

- 日期：2026-10-21
- 现象：`E:\DevTools\Projects\Projects\agent-mini` 已存在（空目录、非 Git 仓库），而 `gh repo clone` 的目标目录名为 `Agent-mini`（首字母大写）。
- 根因：Windows 文件系统大小写不敏感，`Agent-mini` 与 `agent-mini` 指向同一目录；Git 允许克隆进**已存在的空目录**，因此无需删除或重命名。
- 解决方案：保留原目录不删除，在父目录执行 `gh repo clone Kaksiana/Agent-mini`，复用该空目录落盘。
- 验证方式：`git rev-parse --show-toplevel` 输出 `E:/DevTools/Projects/Projects/agent-mini`；`git status -sb` 输出 `## main...origin/main`，无嵌套目录产生。
- 状态：Resolved
- 关联提交：`17fb2e8`

### ISSUE-003 — git push 凭据身份与 gh 活动账号不一致

- 日期：2026-10-21
- 现象：gh 活动账号为 `Kaksiana`，但直接推送存在以 `Ryan-0625` 身份认证的风险（Windows 凭据管理器缓存其 PAT）。
- 根因：git 全局 `credential.helper` 为 `manager` / `manager-core`，返回的是旧账号凭据；该凭据与 gh 的 keyring 存储相互独立。
- 解决方案：推送时使用一次性内联凭据助手，不修改全局配置：`git -c credential.helper= -c 'credential.helper=!gh auth git-credential' push origin main`。
- 验证方式：推送输出 `17fb2e8..5e74da1  main -> main`、退出码 0；`gh api repos/Kaksiana/Agent-mini/commits/main` 返回 SHA 与本地 `HEAD` 一致。
- 状态：Resolved（长期是否改用 `gh auth setup-git` 待定）
- 关联提交：`5e74da1`

### ISSUE-004 — 仓库缺少 .gitignore，存在误提交依赖与密钥的风险

- 日期：2026-10-21
- 现象：初始化后仓库根目录无 `.gitignore`，`node_modules/`、`.env`、构建产物等可能被误提交。
- 根因：仓库初始化阶段仅创建目录骨架与占位文档，未包含忽略规则。
- 解决方案：新增 `.gitignore`，覆盖 OS、IDE、Node/Python/Java/Go、构建产物、日志与临时文件、环境变量与密钥、本地数据、工具缓存九类；并按 `AGENT.md` §5.1 保留 `!.env.example` / `!.env.template` 例外。
- 验证方式：`git check-ignore -q --no-index` 逐项校验——`.env`、`node_modules/x.js`、`dist/app.js`、`Data/tmp/a.csv` 退出码 0（已忽略）；`.env.example`、`.env.template`、`src/app.js`、`Data/keep.csv` 退出码 1（可跟踪）。
- 状态：Resolved
- 关联提交：本轮 `chore(git): add .gitignore`

### ISSUE-005 — OpenSpec 尚未初始化，工作流暂不可用

- 日期：2026-10-21
- 现象：`openspec` CLI 可用（版本 1.12.0），但仓库内不存在 `openspec/` 目录，`openspec list` 无 change 可列。
- 根因：仓库初始化阶段未执行 `openspec init`。
- 解决方案：于 2026-10-21 执行 `openspec init --tools none --no-animation --no-copilot-cloud`，生成 `openspec/config.yaml`、`openspec/changes/archive/.gitkeep`、`openspec/specs/.gitkeep`。选用 `--tools none` 以避免初始化过程改写既有 AI 工具指令文件（含 `AGENT.md`）。
- 验证方式：`openspec list` 返回 `No active changes found.`（命令可正常运行）；`git diff --name-only` 为空，确认初始化未修改任何已跟踪文件。
- 状态：Resolved
- 关联提交：`openspec` 初始化提交

### ISSUE-006 — 空目录不被 Git 跟踪，骨架目录不会入库

- 日期：2026-10-21
- 现象：`Frontend/`、`Backend/`、`Data/`、`Script/` 为本地空目录，`git status` 不显示，提交后远端仓库中将缺少这些目录。
- 根因：Git 只跟踪文件，不跟踪空目录。
- 解决方案：在各空目录放置 `.gitkeep` 占位文件并提交：`Frontend/.gitkeep`、`Backend/.gitkeep`、`Data/.gitkeep`、`Script/.gitkeep`。
- 验证方式：`git ls-files` 返回结果中包含上述四个 `.gitkeep`；远端仓库可看到对应目录。
- 状态：Resolved
- 关联提交：`chore: track empty project directories`

### ISSUE-007 — PROMPT.md 初版只记录摘要，未保留用户原始 Prompt

- 日期：2026-10-21
- 现象：`Docs/PROMPT.md` 首版按模板仅记录目标、约束、产出等摘要字段，用户发送的原始 Prompt 原文没有入库，事后无法据此复核需求原话与措辞。
- 根因：`AGENT.md` §3 的条目模板写的是"Prompt 摘要"，落地时被理解为只记摘要即可；且原模板明确写了"不必逐字粘贴超长对话"，与"完整记录原始 Prompt"的诉求冲突。
- 解决方案：`PROMPT.md` 改为"原始 Prompt 逐字代码块 + 执行摘要"结构，并回溯补录 Prompt 01–06；同时修订 `AGENT.md` §3，将"逐字保留原始 Prompt"由惯例升级为强制要求。
- 验证方式：`PROMPT.md` 中 Prompt 01–07 均含原始 Prompt 代码块，条目数与用户实际发送轮次一致；`AGENT.md` §3 要求与验证方式已同步。
- 状态：Resolved
- 关联提交：`docs(prompt)` / `docs(agent)` / `docs(issue)`

### ISSUE-008 — `README.md` 未记录可执行的测试命令，与 TDD 规范存在空档

- 日期：2026-10-21
- 现象：`AGENT.md` §2 规定"测试命令以 `README.md` 中记录的真实脚本为准"，但 `README.md` 仅有标题，没有安装、运行、测试命令；`Docs/TESTING.md` §5.3 只能给出"暂定"命令。
- 根因：仓库初始化阶段只创建了占位 README；技术栈在 S00 才落地，测试命令尚未产生。
- 解决方案：**待办**——在 S00（工程基线）阶段把可执行的安装/运行/测试命令写入 `README.md`，并回填 `TESTING.md` §5.3。
- 验证方式：`README.md` 中存在可直接执行的 `pytest` 命令；在干净环境按 README 步骤可跑通全量测试。
- 状态：Open
- 关联提交：无

### ISSUE-009 — 文档基线未走 OpenSpec change 流程

- 日期：2026-10-21
- 现象：`AGENT.md` §6.1 要求新功能先建 OpenSpec change，但 `Docs/REQUIREMENT.md` 等四份文档是直接落盘的，`openspec list` 仍为 `No active changes found.`。
- 根因：本阶段为"规范与文档基线"，尚未进入功能开发；`openspec/` 已初始化但未创建 change。
- 解决方案：**待办**——首次功能开发（S00 之后）前，用 `openspec new change` 或 `openspec-propose` 建立 change；文档基线可补建一个 `requirement-baseline` change 以便归档。
- 验证方式：`openspec list` 能看到活跃 change；`openspec validate <change-id>` 通过。
- 状态：Open
- 关联提交：无

### ISSUE-010 — 思考字段与决策摘要混用，输出解析缺少异常分支

- 日期：2026-10-21
- 现象：`thought` 直接取最终文本或运行时补写文本，未区分模型推理、工具决策与最终答案；多工具调用的 trace 粒度和 HTTP 字段不一致。
- 根因：只描述了正常的 function calling 路径，没有定义响应判别、来源标记和协议错误契约。
- 解决方案：补充 `reasoning_content` 的可选解析、运行时决策摘要来源、完整响应判别表、多工具调用列表与脱敏输出；同步需求、测试与阶段计划。
- 验证方式：检查 DESIGN §3.1、§3.2.3、§3.2.4 与 TESTING 的解析用例和 AC-22 映射一致；运行时验证留待实现阶段，不以文档检查代替测试通过。
- 状态：Resolved
- 验证结果：文档定义与用例映射已校验；关闭的是设计缺口，相关运行时功能尚未实现或执行测试。
- 关联提交：无

### ISSUE-011 — Token 预算遗漏工具 Schema 与循环增长，单轮超限仍发送

- 日期：2026-10-21
- 现象：TokenCounter 仅描述消息计数，未显式统计实际 `tools` JSON；工具结果增长后缺少再次检查；最小上下文超预算时仍尝试请求模型。
- 根因：预算校验以初始消息拼接为中心，没有覆盖每次实际出站请求。
- 解决方案：统一统计 messages、tools 和结构开销；冻结工具定义快照；每次调用前复核预算；仅剩不可裁剪内容仍超限时本地返回 `CONTEXT_TOO_LARGE`。
- 验证方式：检查预算公式、Schema 统计、零出站请求与工具结果增长用例映射；实现后再运行对应测试。
- 状态：Resolved
- 验证结果：messages/tools/开销公式与出站预算规则一致；对应 TC 均已定义，运行验证待实现。
- 关联提交：无

### ISSUE-012 — 双窗口、工具追问和真实 API 缺少验收用例

- 日期：2026-10-21
- 现象：已设计并发隔离和纯对话追问，但没有双窗口交替恢复、待办隔离、带工具追问和真实 API 的正式用例。
- 根因：现有用例拆分后未覆盖题目完整用户旅程，真实调用仅被列为手工步骤。
- 解决方案：新增会话、工具追问、解析、预算和真实 API 用例；真实凭据仅从 `DEEPSEEK_API_KEY` 环境变量读取，Prompt 记录中脱敏。
- 验证方式：机械核对新增 TC 编号唯一、统计准确、需求与计划可追溯；当前没有 Runtime 与测试代码，真实 API 验收保持未执行状态。
- 状态：Resolved
- 验证结果：75 个功能 TC 与 1 个工程 smoke 无重复或缺失引用；47 个 FR 全部关联计划；23 个 AC 在需求与测试文档中的映射一致。密钥模式扫描未命中真实格式凭据；不代表真实 API 已验收。
- 关联提交：无

### ISSUE-013 — 环境变量命名冲突：`LLM_API_KEY` 与 `DEEPSEEK_API_KEY`

- 日期：2026-10-22
- 现象：`Docs/DESIGN.md` §3.8 曾使用 `LLM_API_KEY`；`Docs/PLAN.md` S18、`Docs/TESTING.md` §4.6 与 `MEMORY.md` 使用 `DEEPSEEK_API_KEY`。同一密钥存在两个正式名，后续实现若双读会产生歧义与配置错误。
- 根因：DESIGN 早期按通用 provider 命名，后续真实 API 验收改用 DeepSeek 专用名，文档之间未同步收敛。
- 解决方案：统一为 `DEEPSEEK_API_KEY`；修订 `Docs/DESIGN.md` §3.8、版本号与 §10 变更记录；同步 `openspec/specs/engineering-standards/spec.md` C-02 与 `openspec/config.yaml` context；明确禁止 `LLM_API_KEY` 别名。
- 验证方式：全仓搜索 `LLM_API_KEY`，仅允许命中 PROMPT/ISSUE 历史记录，以及 DESIGN/OpenSpec 规范/config 中“禁止别名”的说明；运行代码、README、测试夹具不得出现该别名；`DEEPSEEK_API_KEY` 在相关文档中保持一致。
- 验证结果：当前仅命中历史 PROMPT/ISSUE 与 DESIGN/规范/config 的禁止别名说明；无运行代码、README 或测试夹具；`openspec validate --all` 通过。
- 状态：Resolved
- 关联提交：无（本轮未执行 Git 操作）

### ISSUE-014 — `AGENT.md` 环境事实滞后（OpenSpec、`.gitignore`、技术栈）

- 日期：2026-10-22
- 现象：`AGENT.md` §6.1 仍写“尚未执行 `openspec init`”；§5.1 写 `.gitignore` 尚未创建；§2 写“技术栈尚未确定”。实际上 OpenSpec 已于 2026-10-21 初始化（ISSUE-005），`.gitignore` 已创建（ISSUE-004），技术栈已在 `Docs/DESIGN.md` §1.1 确定。
- 根因：`AGENT.md` 初版按初始化前状态编写，后续 ISSUE-004/005 与 DESIGN 落地后未回填。
- 解决方案：更新 `AGENT.md` §2、§5.1、§6.1；在 §6.1 增加 `openspec/specs/engineering-standards/spec.md` 全局规范入口；§11 追加变更记录；原因见 `Docs/PROMPT.md` Prompt 17。
- 验证方式：在 `AGENT.md` 中搜索旧表述（“尚未执行 `openspec init`”“尚未创建”“技术栈尚未确定”）零命中；`git diff -- AGENT.md` 仅包含事实修正、规范入口与变更记录；`openspec validate --specs --strict` 通过。
- 验证结果：旧表述零命中；`AGENT.md` diff 仅涉及 §2、§5.1、§6.1、§11；`openspec validate --all` 通过。
- 状态：Resolved
- 关联提交：无（本轮未执行 Git 操作）

### ISSUE-015 — OpenSpec 全局规范任务未即时记录 PROMPT/ISSUE

- 日期：2026-10-22
- 现象：Prompt 16（建立 OpenSpec 全局规范）执行时受“只改 OpenSpec 文件”约束，未写入 `Docs/PROMPT.md` 与 `Docs/ISSUE.md`，与 `AGENT.md` §3/§4 的全过程记录要求冲突。
- 根因：任务范围与全局记录规范冲突，执行时未即时登记例外，导致记录滞后一轮。
- 解决方案：补录 `Docs/PROMPT.md` Prompt 16/17 与本条 ISSUE-013/014/015；在 Prompt 16 摘要中说明范围约束与补记决定；后续同类任务先登记例外再执行。
- 验证方式：`Docs/PROMPT.md` 中存在 Prompt 16/17 的原始 Prompt 与执行摘要；ISSUE-013/014/015 编号连续、状态非空且均含验证方式；本轮仅追加 Prompt 16/17 与上述 ISSUE，未删除或改写历史条目。
- 验证结果：Prompt 16/17 与 ISSUE-013/014/015 均已落盘；编号连续、状态均为 Resolved；历史 Prompt 01–15 未改写。
- 状态：Resolved
- 关联提交：无（本轮未执行 Git 操作）

### ISSUE-016 — `pytest` console script 损坏，裸命令静默退出 1

- 日期：2026-10-22
- 现象：`python -m pytest` 正常运行（1 passed），但裸 `pytest --version` 与 `pytest` 均退出码 1 且无输出；`E:\Components\Python\Python3.13\Scripts\pytest.exe` 存在，模块版本为 9.0.2。
- 根因：Python 3.13 Scripts 目录下的 pytest console script 与当前解释器不匹配或已损坏；静默退出未提供更具体的启动错误。
- 解决方案：执行 `python -m pip install --force-reinstall --no-deps pytest==9.0.2` 重建 console script，未修改项目依赖。
- 验证方式：`pytest --version` 输出 `pytest 9.0.2`；`pytest` 运行 TC-SMOKE-001 输出 `1 passed`。
- 验证结果：`pytest` 裸命令已恢复，符合 S00 验收与 README 命令。
- 状态：Resolved
- 关联提交：无（环境修复，不在仓库内）

> S00 阶段除 ISSUE-016 外无其他阻塞问题。

### ISSUE-017 — S00 包骨架与 `Docs/DESIGN.md` §2.2 不一致

- 日期：2026-10-22
- 现象：S00 曾标记为已完成，但 `agent_mini/` 实际只有 `__init__.py` 与 `version.py`；`Docs/DESIGN.md` §2.2 规定的子包与占位模块未落地，包骨架不完整。
- 差异清单：

| `DESIGN.md` §2.2 规定项 | 仓库现状 | 差异 |
| --- | --- | --- |
| `config/`：`models.py`、`loader.py`、`container.py` | 无 | 缺目录、`__init__.py`、3 个模块 |
| `llm/`：`client.py`、`models.py`、`errors.py` | 无 | 缺目录、`__init__.py`、3 个模块 |
| `runtime/`：`agent.py`、`loop.py`、`result.py` | 无 | 缺目录、`__init__.py`、3 个模块 |
| `tools/`：`registry.py`、`sandbox.py`、`builtin/` | 无 | 缺目录、`__init__.py`、2 个模块、`builtin/` |
| `memory/`：`short_term.py`、`mid_term.py`、`base.py` | 无 | 缺目录、`__init__.py`、3 个模块 |
| `context/`：`builder.py`、`token_counter.py`、`window.py` | 无 | 缺目录、`__init__.py`、3 个模块 |
| `systemdb/`：`schema.sql`、`repository.py`、`models.py` | 无 | 缺目录、`__init__.py`、3 个文件 |
| `interface/`：`http.py` | 无 | 缺目录、`__init__.py`、1 个模块 |
| `observability/`：`logging.py`、`errors.py` | 无 | 缺目录、`__init__.py`、2 个模块 |
| 合计：9 个业务子包 + `tools/builtin/`，23 个设计模块/文件 | 0 个子包、0 个占位模块 | 10 个 `__init__.py`、23 个占位文件 |

- 根因：S00 验收只覆盖 `pip install -e .`、smoke 测试与 ruff/mypy，未把 `DESIGN.md` §2.2 的目录结构列为验收项；测试也只验证顶层包导入。
- 解决方案：创建 `s00-baseline-skeleton-fix` OpenSpec change；补齐 10 个子包 `__init__.py` 与 23 个占位模块（仅中文模块 docstring，空实现），`schema.sql` 仅写“待 S17 落地”注释；新增子包可导入测试；重新执行全部验收后再恢复 S00 状态。
- 验证方式：逐项核对 `DESIGN.md` §2.2 文件存在；执行子包导入命令；`pytest`、`ruff check .`、`ruff format --check .`、`mypy agent_mini`、`openspec validate --all --strict` 全部通过。
- 验证结果：10 个子包与 23 个占位模块/文件全部存在；子包导入输出 `all imports ok`；`pytest` 2 passed；`ruff check .` 零告警；`ruff format --check .` 36 files already formatted；`mypy agent_mini` 34 source files 无错误；`openspec validate --all --strict` 3 passed、0 failed。
- 预防：S00 DoD 增加 `DESIGN.md` §2.2 目录对照；保留子包导入测试作为回归；后续新增子包必须同步更新 DESIGN 与测试。
- 状态：Resolved
- 关联提交：`c642b2f`（修正启动）、`4e7e900`（骨架补全）

### ISSUE-018 — S00 wheel 未包含 `systemdb/schema.sql`，打包验收缺失

- 日期：2026-10-22
- 现象：上一轮报告称“pyproject.toml 与依赖清单未改动”。实际构建 `agent_mini-0.1.0-py3-none-any.whl` 后，10 个子包的 `.py` 文件均已进入 wheel，但 `agent_mini/systemdb/schema.sql` 缺失；此前的验收只验证 editable install 与源码目录，未验证 wheel 内容。
- 根因：`[tool.setuptools.packages.find]` 只负责发现 Python 包，非 Python 文件必须通过 `package-data` 显式声明；S00 验收和测试未覆盖构建产物内容，也未约束占位模块只能含 docstring。
- 解决方案：在 `pyproject.toml` 增加 `agent_mini.systemdb` 的 `package-data` 声明；新增打包配置测试、DESIGN §2.2 结构完整性测试、占位模块 AST 检查；重建 wheel 并逐项核对 35 个 `agent_mini/` 文件（含 2 个既有文件）。
- 验证方式：`python -m pip wheel . --no-deps` 构建 wheel；用 `zipfile` 对比 `DESIGN.md` §2.2 文件清单；`pytest`、`ruff check .`、`ruff format --check .`、`mypy agent_mini`、`openspec validate --all --strict` 全部通过。
- 验证结果：wheel 内 `agent_mini/` 文件数为 35，包含 `systemdb/schema.sql`；将 wheel 安装到临时 target 后，10 个子包全部可导入，`importlib.resources` 读取 `schema.sql` 返回 True；`pytest` 7 passed；`ruff check .` 零告警；`ruff format --check .` 37 files already formatted；`mypy agent_mini` 34 source files 无错误；归档后 `openspec validate --all --strict` 为 2 passed、0 failed。
- 预防：S00/S01 DoD 增加“wheel 内容与设计目录一致”的检查；保留打包配置测试与结构测试作为回归。
- 状态：Resolved
- 关联提交：`4b538cb`（修正启动）、`3637d93`（打包修正与测试）

### ISSUE-019 — S00 遗留收口项未同步到 DoD/准出/占位规范

- 日期：2026-10-22
- 现象：S00 修正完成后，上一轮评审提出的收口项仍未落地：ISSUE-017 预防措施、`Docs/TESTING.md` §6.2 wheel 准出、`Docs/PLAN.md` §5.2 里程碑 DoD、`Docs/PLAN.md` S00 验收标准、`Docs/DESIGN.md` §2.2 占位规范均未同步；仓库原先不存在 ISSUE-019。
- 根因：S00 修正聚焦代码、测试与进度，未把评审结论回填到阶段与里程碑门禁。
- 解决方案：新增本 ISSUE；更新 `TESTING.md` §6.2、`PLAN.md` §5.2 与 S00 验收、`DESIGN.md` §2.2；保留 ISSUE-017/018 的 wheel 与结构测试作为回归。
- 验证方式：逐项检查上述文档条款；`pytest`、`ruff check .`、`ruff format --check .`、`mypy agent_mini`、`openspec validate --all --strict` 通过。
- 验证结果：四项文档条款已补齐；S00 验收新增 wheel 35/35 与占位规范；测试与静态检查全绿。
- 状态：Resolved
- 关联提交：S00 收尾提交（见最终报告）
