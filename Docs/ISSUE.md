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

### ISSUE-020 — S01 测试项涉及后续阶段类型与 Runtime/Tool 行为

- 日期：2026-10-22
- 现象：`PLAN.md` S01 测试项包含 TC-L2-008/009/010，需要 LLM 错误类型与非法工具参数的结构化结果；但 S01 输出只列 `llm/client.py`、`llm/models.py`，`llm/errors.py` 被列为 S02 输出；`ModelConfig` 被列为 S21 配置层输出；TC-L2-009/010 还涉及 Runtime/ToolResult 与循环 trace。
- 根因：测试项按协议契约层归类，但错误类型、配置类型和 Runtime 行为分散在后续阶段，阶段输出边界未同步。
- 解决方案/裁决：
  1. `llm/errors.py` 在 S01 只提供协议判别所需的 `LLMError`、`LLMProtocolError`、`LLMEmptyResponseError`、`LLMOutputTruncatedError`、`LLMOutputRejectedError`；鉴权/限流/超时与重试留 S02。
  2. `llm/models.py` 提供 S01 临时 `ModelConfig`（`base_url`、`model`、`timeout`）；S21 配置层落地时迁移或复用，不新增配置层实现。
  3. 非法工具参数在 S01 表示为 `ToolCall(error_code="invalid_arguments", arguments=None)` 并保留 `call_id`；映射为 `ToolResult`、执行工具与模型修正闭环留 S04/S06。
  4. TC-L2-010 在 S01 只覆盖“content + 多个 tool_calls 的解析与顺序”；循环、消息配对与 trace 留 S04。
  5. TC-L2-007 在 S01 覆盖 reasoning 解析与客户端请求回传；轮次裁剪后不回传留 S15/S16。
- 验证方式：对应 TC 的契约测试通过；文档在 DESIGN/TESTING/PLAN 的边界说明保持同步；不在 S01 引入 Runtime/Tool/Memory 实现。
- 验证结果：L2 契约测试 29 passed，全量 36 passed；S01 未引入 Runtime/Tool/Memory 实现；DESIGN §3.1、TESTING §3、PLAN S01 已同步边界。
- 状态：Resolved
- 关联提交：S01 规划与实现提交（见最终报告）

### ISSUE-021 — dev 工具依赖仅设下界，版本漂移且 `pytest-cov` 未声明

- 日期：2026-10-22
- 现象：`pyproject.toml` 的 dev 依赖对 `ruff`、`mypy`、`pytest-asyncio`、`respx` 只设最低版本；验收中使用的 `pytest-cov` 未声明。`pip install -e ".[dev]"` 实际把 ruff 从 0.15.10 升到 0.17.1、mypy 从 1.11.2 升到 2.4.0。
- 根因：初版依赖只按“最低版本”声明，没有为 dev 工具设置 minor 兼容上界，也没有把覆盖率工具纳入依赖清单。
- 解决方案：将四个指定 dev 工具 pin 到当前 minor 兼容范围；补充 `pytest-cov` 并 pin 到 minor；在 ISSUE 与本轮 PROMPT 记录升级原因。
- 验证方式：检查 `pyproject.toml` 的 dev 约束；`pip install -e ".[dev]"` 成功；`pytest --cov=agent_mini --cov-report=term-missing` 可运行；全量测试与静态检查通过。
- 验证结果：dev 约束已为 `pytest-asyncio>=1.3,<1.4`、`pytest-cov>=7.1,<7.2`、`respx>=0.23,<0.24`、`ruff>=0.17,<0.18`、`mypy>=2.4,<2.5`；`pip install -e ".[dev]"` 退出码 0；覆盖率命令 50 passed、总覆盖率 93%。
- 状态：Resolved
- 关联提交：S01 修复提交（见最终报告）

### ISSUE-022 — S01 评估报告的 P0/P1 问题修复

- 日期：2026-10-22
- 现象：`Docs/S01-report.md` 判定 S01 不宜直接进入 S02，指出 P0-01（非 object JSON 顶层泄漏 `AttributeError`）、P1-01（params 覆盖受控字段）、P1-02~P1-10（异常层次、阶段输出、TC 覆盖、TDD 证据、README/MEMORY、pytest-cov、归档顺序、reasoning 角色、Ruff 变更记录）。
- 根因：S01 主路径完成，但协议硬化、跨阶段边界与文档闭环不足。
- 解决方案：创建 `s01-report-fixes` OpenSpec change；修复 P0-01、P1-01、P1-09；同步 PLAN/TESTING/DESIGN/README/MEMORY/ISSUE；补充 pytest-cov 与依赖 pinning；记录 P1-05/P1-08 的流程改进；P2 可选项按风险选择性处理。
- 验证方式：定向负例测试先红后绿；全量 pytest、ruff、format、mypy、openspec、wheel/仓库外导入全部通过；S01-report 增加修复记录。
- 验证结果：P0-01 已修（非 object 顶层 → `LLMProtocolError`）；P1-01 已修（保留字段拒绝）；P1-09 已修（reasoning 仅 assistant）；P1-02/03/04/06/07/10 已闭环；P1-05 规范已补，历史收集级红证据保留说明；P1-08 由新 change 承接且未重写历史；P2-02/03/05/07 已修，P2-01/04/06 记录为后续可选改进。50 passed、覆盖率 93%、ruff/format/mypy/openspec 通过。
- 状态：Resolved
- 关联提交：S01 修复提交（见最终报告）

### ISSUE-023 — 真实 DeepSeek API 测试因缺少 `DEEPSEEK_API_KEY` 未执行

- 日期：2026-10-22
- 现象：进程环境、Windows User/Machine 环境均无 `DEEPSEEK_API_KEY`，仓库根目录也没有 `.env`；`https://api.deepseek.com` 的 HEAD 请求返回 401，说明网络可达但缺少凭据。未发送任何带消息的模型请求。
- 根因：执行环境未注入真实 API 密钥；S01 文档禁止读取密钥，当前用户明确要求真实测试，但环境中仍无可用凭据。
- 解决方案：不发送无凭据或伪造密钥请求；等待用户在环境中设置 `DEEPSEEK_API_KEY` 后重试。密钥不得写入仓库、Prompt、命令输出或日志。
- 验证方式：确认 `DEEPSEEK_API_KEY` 存在且不打印值；使用 `HttpLLMClient` 发送最小文本消息；记录模型、trace_id、usage、回复与脱敏结果；失败时记录 HTTP 状态/错误类型，不记录 Authorization 或原始响应。
- 验证结果：用户配置 `.env` 后，从该文件载入当前子进程环境并成功发送一次最小文本消息；模型 `deepseek-chat` 返回 `OK`，`finish_reason=stop`，usage 为 prompt 8 / completion 1 / total 9，耗时约 1519ms，无 reasoning。未记录 Authorization、密钥或原始响应正文。
- 状态：Resolved
- 关联提交：本次文档记录（见最终报告）

### ISSUE-024 — `LLMError` 临时根延后到 S20 迁移 `AgentError`（已关闭）

- 日期：2026-10-22
- 现象：S01/S02 的 `LLMError` 直接继承 `Exception`，而 `Docs/DESIGN.md` §3.7 的最终体系是 `AgentError → LLMError`；S20 才交付 `observability/errors.py`。
- 根因：S01/S02 只实现模型接入层，提前实现 `AgentError` 会把 S20 的可观测/异常体系拉入当前阶段，形成跨层职责。
- 决策：**S02–S19 继续使用临时 `LLMError` 根，S20 统一迁移**。S02 新增异常均继承 `LLMError`，保持 `*Error` 命名与 `code/http_status`。
- 影响范围：`llm/errors.py`、`llm/client.py`、`llm/models.py`、`tests/contract/*`；S18 HTTP 错误映射与 S19 日志可先按 `LLMError` 处理。
- 迁移工作量：S20 在 `observability/errors.py` 定义 `AgentError`，将 `LLMError` 改为其子类，更新引用点并补异常层次测试；预计 0.5–1 人日。
- 触发时机：S20 建立统一异常体系时；S18 真实 API 验收前复核错误码映射。
- 状态：Resolved（2026-10-24）。验证：`LLMError(AgentError)`，全量 364 passed；错误码/状态映射测试通过。
- 关联提交：S02 规划提交（见最终报告）

### ISSUE-025 — 运行依赖与 pytest 仍仅设下界（S01 P2-05 遗留）

- 日期：2026-10-22
- 现象：`httpx>=0.27`、`pydantic>=2.6`、`pytest>=8.0` 仍没有兼容上界或锁文件；S02 的 dev 工具已 pin，但运行依赖与 pytest 未 pin。
- 根因：S01 只按设计最低版本声明；为避免在 S02 改变运行依赖行为，本轮未扩大范围。
- 决策：保持现状，登记债务；目标在 S18 真实 API 验收前复核 `httpx`/`pydantic` 上界，在 S21 配置与依赖收口时统一锁定；`pytest` 在 CI 稳定后确定上界。
- 验证方式：S18/S21 前检查 `pyproject.toml` 与干净环境解析结果；必要时引入 constraints/lock 文件并复跑全量测试。
- 状态：Open
- 关联提交：S02 规划提交（见最终报告）

### S02 阶段问题记录（2026-10-22）

- 无新增阻塞问题。开工前 ISSUE-024/025 为已登记债务，保持 Open；S02 未引入运行时依赖或越界模块。

### ISSUE-026 — S02 评估报告 P1/P2 问题修复

- 日期：2026-10-22
- 现象：`Docs/S02-report.md` 判定 S02 有条件通过，指出 P1：尝试次数可突破 3、重试无 attempt 记录、timeout 测试未证明配置生效、全局 `AgentError` 与临时 `LLMError` 冲突；P2：3xx 误分类、RetryPolicy 运行时校验不足、llm 子包说明过时、L2 耗时超目标、异常测试未断言具体类型/http_status。
- 根因：S02 默认路径完整，但公开策略边界、可观测出口、超时验证与规范例外未闭环。
- 解决方案：创建 `s02-report-fixes` change；限制 RetryPolicy 1–3 并补运行时校验；增加 `RetryEvent` 出口；补真实本地超时测试；收窄状态映射；补具体异常/http_status 与协议错误不重试测试；在全局规范写入 S20 前临时异常例外；同步文档与 S01 TC-L2-007 组合回归。
- 验证方式：新增测试先红后绿；全量 pytest、覆盖率、ruff/format/mypy、openspec、wheel/仓库外导入通过；S02-report 追加修复记录。
- 验证结果：RetryPolicy 限制 1–3 并做运行时校验；重试事件记录 attempt/max/status/delay；退避 cap 后非递减；3xx/未知状态归 `LLMProtocolError`；补 http_status、协议错误不重试、timeout 配置传递与 S01 TC-L2-007 thinking+tools 回归。全量 72 passed、覆盖率 94.38%；contract 64 passed、31.5s（TESTING 目标调整为 <60s）；ruff/format/mypy/openspec 通过。
- 剩余限制：P1-03 以“底层 httpx timeout 配置断言 + ReadTimeout 分类”验证，本地慢服务器测试因 handler 调度不稳定未保留；P1-04 通过全局规范阶段例外解决，S20 仍需迁移 AgentError。
- 复验追加（2026-10-22）：默认 `on_retry=None` 丢事件、具体异常仍以类名字符串断言、TC-L2-007 未回传 assistant reasoning、`mypy agent_mini tests` 15 errors；见 ISSUE-027。
- 状态：Resolved
- 关联提交：S02 report-fix 提交（见最终报告）

### ISSUE-027 — S02 复验遗留：默认事件、具体异常、组合与 tests 门禁

- 日期：2026-10-22
- 现象：默认 `RetryPolicy.on_retry` 为 None，`RetryEvent` 被丢弃；异常测试比较 `type(...).__name__`；thinking+tools 用例未回传 assistant `reasoning_content`；`mypy agent_mini tests` 有 15 条错误，README 仅检查 `agent_mini`。
- 根因：事件记录依赖可选回调；测试为绕过类型检查使用字符串断言；组合用例只覆盖首轮请求；tests 未纳入 mypy 门禁。
- 解决方案：客户端始终追加 `RetryEvent` 并提供 `retry_events` 快照，`on_retry` 仅作外部订阅；异常测试改用具体异常类；组合用例改为两轮并回传 reasoning/tool_calls；修复 tests 类型错误，README/规范门禁改为 `mypy agent_mini tests`。
- 验证结果：`mypy agent_mini tests` 0 errors（46 files）；默认事件 2 条、具体异常类型、thinking+tools+reasoning 同请求通过；全量 72 passed、覆盖率 95.69%。
- 状态：Resolved
- 关联提交：S02 reverify-fix 提交（见最终报告）

### ISSUE-028 — S03 开工阻塞：TC-L1-015 与 `AgentResult`/签名定义冲突

- 日期：2026-10-22
- 现象：
  1. `Docs/PLAN.md` S03 将测试项写为“TC-L1-015（直答分支）”，但 `Docs/TESTING.md` 的 TC-L1-015 明确是 S04 的两步工具循环（第 1 次 tool_calls、第 2 次文本），没有 S03 直答分支的步骤/断言定义；`Docs/REQUIREMENT.md` FR-RT-01 只映射 TC-L1-015 与 TC-L4-003，未提供 S03 可执行用例。
  2. `Docs/DESIGN.md` §3.2 的调用链给出 `Agent.run(session_id, user_input)`，但未给出 S03 的正式签名；同节没有 `AgentResult` 字段表，伪代码使用 `AgentResult(final, steps, trace)`，而 `Docs/PLAN.md` S03 要求 `AgentResult` 含 `reply/steps/usage`，字段名与来源冲突。
- 影响：若继续实现，只能自行补写 TC 或字段契约，违反“三份文档不一致时停止、不得自行补写需求/测试定义”的约束；同时会导致 S04 返工。
- 根因：S03 测试项沿用 S04 的 TC-L1-015，三份文档未同步拆分直答分支；DESIGN 只有调用链/伪代码，没有 S03 正式字段表与签名。
- 决策：**S03 代码与 OpenSpec change 暂不开始**；不修改 `runtime/` 实现。先解决文档契约。
- 可选解决方向：
  - A（推荐）：在 TESTING 增加 S03 直答 TC（如 TC-L1-015A），并在 DESIGN §3.2 增加 `AgentResult` 字段表与 `Agent.run` 签名。
  - B：将 S03 并入 S04，取消独立 S03。
  - C：明确批准以 PLAN 的 `reply/steps/usage` 为 S03 契约，并以 TC-L4-003 作为直答验收映射，同时登记字段延后。
- 决策（用户确认方向 A）：
  1. `AgentResult` 使用 `reply`（不用 `final`）；DESIGN §3.2 伪代码同步为 `reply`，PLAN 不改。
  2. S03 签名固定为 `async def run(self, user_input: str) -> AgentResult`；`session_id` 延后 S13，并在 DESIGN 写明。
  3. 新增 TC-L1-015A（正常直答）、TC-L1-015B（空响应走 S01 错误路径）、TC-L1-015C（LLM 异常传播且不吞），与 TC-L1-015 形成兄弟用例。
- 开工追加核对：ISSUE-024 仅涉及 `LLMError` 根迁移，不改 `LLMResponse` 字段；ISSUE-025 仅涉及依赖版本策略；均**不阻塞 S03**。
- 解决方案：按 Phase 1 补 DESIGN/TESTING/PLAN 契约并 strict validate；Phase 2 用 TDD 实现 `Agent(llm_client).run(user_input)` 与冻结 `AgentResult`；Phase 3 完成验收、文档与归档。
- 文档：TESTING 新增 3 条 TC 与 S03 覆盖边界；mypy `agent_mini tests` 已写入准出条款。
- 验证方式：`openspec validate s03-runtime-direct-reply --strict`；新增 S03 测试先红后绿；全量 pytest、覆盖率、ruff/format、`mypy agent_mini tests`、wheel/仓库外导入。
- 验证结果：Phase 1 通过 strict；Phase 2 的 S03 测试先红后绿（后续补空白/不变量回归至 16 个 S03 单测）；全量 88 passed、覆盖率 96.03%；`mypy agent_mini tests` 47 files 0 errors。
- 状态：Resolved
- 关联提交：`dda1a10`（Phase 1）、`111439b`（Phase 2）、`13fa639`（文档）、`31f2221`（归档）

### ISSUE-029 — `LLMProtocolError` 的 S03 “不支持 tool_calls”语义清理

- 日期：2026-10-22
- 现象：S03 `Agent` 在收到 tool_calls 时抛 `LLMProtocolError("S03 不支持工具调用")`，与“响应结构非法”共用同一类型；S04 引入工具处理后该语义过期。
- 根因：S03 没有循环和工具执行器，只能用协议异常拒绝工具调用，未区分“请求契约违反”和“响应结构非法”。
- 解决方案：S04 增加 `ToolExecutor` 与循环；有 executor 时执行 tool_calls；无 executor 时收到 tool_calls 才视为请求契约违反；`LLMProtocolError` 继续只表示协议/结构/请求契约非法。DESIGN §3.2、§3.3 与 runtime 规格同步。
- 验证方式：S04 契约测试覆盖有 executor 的工具循环、无 executor 的 tool_calls 拒绝、结构非法响应；`openspec validate --all --strict`。
- 验证结果：S04 循环在配置 executor 时执行 tool_calls，未配置 executor 时以 `LLMProtocolError` 拒绝；结构非法仍由同一异常表示；S03 的“Agent 不支持 tools”分支已删除。99 passed、覆盖率 96.17%。
- 状态：Resolved
- 关联提交：`34c9758`（规划）、S04 代码/文档提交（见最终报告）

### S03 阶段问题记录（2026-10-22）

- Phase 1 完成：DESIGN §3.2 字段/签名、TESTING TC-L1-015A/B/C、PLAN 测试项、mypy `agent_mini tests` 准出条款；ISSUE-028 Resolved。
- Phase 2 完成：单轮直答与冻结 `AgentResult` 实现，16 个 S03 单元测试通过；全量 88 passed、覆盖率 96.03%。
- 无新增阻塞问题；ISSUE-024/025 为已登记债务，不阻塞 S03。

### ISSUE-030 — S04 报告 P0/P1 修复与归档后流程补记

- 日期：2026-10-22
- 现象：S04 报告发现公开 `ToolCallTrace.observation` 可泄露独立于调用参数的工具结果密钥；TC-L1-028/TC-L2-009 未覆盖“失败→合法调用→收敛”；执行异常回灌无正式测试；runtime 主规格仍保留 S03 排他字段；S04 归档后才补三步测试与红证据。
- 根因：脱敏只从参数敏感键推导 secret；错误测试直接返回最终文本；异常分支仅探针验证；主规格按阶段追加未改为累计契约；归档顺序未等全部验收测试完成。
- 解决方案：新 change `s04-report-fixes`；统一结果脱敏（敏感键、`sk-*`、Bearer、key=value 模式）；补失败→成功链、未知工具链、执行异常测试；修订 runtime 主规格为 S03+S04 累计契约；记录归档后变更例外与逐 TC 红证据。
- 验证方式：新增安全/修正/异常测试先红后绿；全量 pytest、覆盖率、ruff/format、`mypy agent_mini tests`、OpenSpec、wheel。
- 验证结果：独立结果 `token=...`/`sk-*` 用例修复前 1 failed、修复后 11 个 S04 测试全绿；失败→合法→final、未知工具→合法→final、executor 异常→final 均已固化；runtime 主规格改为 S03+S04 累计契约；全量 99 passed、覆盖率 96.17%；unit 35、contract 64；`mypy agent_mini tests` 48 files 0 errors。
- P1-05 限制：P0 有逐用例失败证据；P1-01/P1-02 是补既有实现回归，首次运行即绿，不能伪造红灯，已在 S04-report §10 如实记录。
- 状态：Resolved
- 关联提交：`s04-report-fixes` change、代码/文档提交（见最终报告）

### S04 阶段问题记录（2026-10-22）

- S04 完成 ReAct 工具循环、消息配对、ThoughtStep/ToolCallTrace、错误回灌与隐私脱敏；ISSUE-029 的 `LLMProtocolError` 语义已收敛。
- 验收：99 passed、覆盖率 96.17%；unit 35、contract 64；`mypy agent_mini tests` 48 files 0 errors；OpenSpec 通过。
- 无新增阻塞问题；S05 安全阀、S06 真实注册表、S18 真实 API/HTTP 未实现。

### ISSUE-031 — S05 报告 P1 修复

- 日期：2026-10-22
- 现象：工具本地 TimeoutError 被当 deadline；非法参数/空对象签名碰撞；NaN/Infinity deadline 可绕过；deadline 在 schemas 后计时；LLM deadline 少计 steps；TC-L1-029 覆盖不足；S05 实现/OpenSpec/Prompt 时序违规；runtime 累计规格冲突；M1 声明超前。
- 根因：wait_for 无法区分内外 TimeoutError；signature 用 `arguments or {}`；deadline 校验只检查 <=0；deadline 在 schema 后建立；超时分支回退 step；测试矩阵只覆盖工具 deadline；流程记录在实现后补。
- 解决方案：新 change `s05-report-fixes`；工具本地 TimeoutError 归 tool_execution_error；非法调用不计重复；finite 校验；入口先建立 deadline；保留尝试步数；补 LLM deadline/签名/有限值/纠正测试；修累计规格；M1 状态与演示命令。
- 验证方式：新增测试先红后绿；全量 pytest、覆盖率、ruff/format、mypy tests、OpenSpec、wheel。
- 验证结果：工具本地 TimeoutError、非法→合法空对象、非有限 deadline、LLM 挂起 steps 等 5 个用例先红后绿；S05 测试增至 13 个；全量 112 passed、覆盖率 95.72%；unit 48、contract 64；`mypy agent_mini tests` 49 files 0 errors；OpenSpec/wheel 通过。M1 恢复并补离线演示命令。
- 历史限制：S05 原 Prompt 仍只有摘要、原始红灯命令不可完整复核，不伪造；新 change 记录偏差。
- 状态：Resolved
- 关联提交：`s05-report-fixes` change、代码/文档提交（见最终报告）

### ISSUE-032 — S06 工具执行结果与 S04 Protocol 对接

- 日期：2026-10-22
- 现象：S04 `ToolOutcome` 可表达 `ok=True + error_code` 或 `ok=False` 无错误码的矛盾状态；`ToolCallTrace.args` 浅冻结；S04 Runtime 只接受测试替身，尚无注册表适配。
- 根因：S04 先定义最小 Protocol，S06 才交付注册表与执行结果。
- 解决方案：S06 在 `tools/registry.py` 定义唯一 `ToolResult`（成功/失败不变量）与 `ToolContext` 预留；Runtime 通过 `RegistryExecutor` 适配，不复制第二套执行结果；`ToolCallTrace.args` 采用只读映射/防御性副本。
- 验证方式：注册/Schema/重复/执行异常/集成回填测试；全量回归。
- 验证结果：ToolResult 不变量、ToolCallTrace.args 只读映射、RegistryExecutor 适配均通过；129 passed、覆盖率 95.25%；mypy 51 files 0 errors。
- 状态：Resolved
- 关联提交：`s06-tool-registry` change、代码/文档提交（见最终报告）

### ISSUE-033 — S06 报告 P1 修复与历史流程缺口

- 日期：2026-10-22
- 现象：`enabled_key` 只存不执行；同步 handler 阻塞事件循环；额外模型参数被静默接受；handler 返回 None 被包装成功；FR-TOOL-01 启停未映射测试；OpenSpec/测试/文档晚于实现；S06 Prompt 非逐字且无有效红灯。
- 根因：S06 把启停当元数据；handler 直接同步调用；未在注册/执行边界拒绝额外字段与非 ToolResult；流程记录在实现后补。
- 解决方案：新 change `s06-report-fixes`；启停过滤、`asyncio.to_thread`、参数键白名单、严格 ToolResult 返回、元数据/内容校验、深冻结 args；补未知工具/启停/同步/额外参数/返回类型测试；记录流程例外。
- 验证方式：新增测试先红后绿；全量 pytest、覆盖率、ruff/format、mypy tests、OpenSpec、wheel。
- 验证结果：新增启停、同步 handler、额外参数、非 ToolResult、元数据、失败内容、深冻结等用例先红后绿；全量 129 passed、覆盖率 95.25%；unit 65、contract 64；mypy 51 files 0 errors；OpenSpec/wheel 通过。
- 历史限制：S06 原始 Prompt 仍为摘要；不伪造历史红灯。
- 状态：Resolved
- 关联提交：`s06-report-fixes` change、代码/文档提交（见最终报告）

### ISSUE-034 — S08 time 参数名 `timezone` 与 TC `tz` 不一致

- 日期：2026-10-23
- 现象：S08 Prompt 要求参数模型字段为 `timezone`；TESTING TC-L1-005 调用 `time(tz="UTC")`。
- 根因：TC 使用简写 `tz`，Prompt 明确要求 `timezone`。
- 解决方案：`TimeArgs` 只公开 `timezone`；handler 增加仅内部/直调兼容的 `tz` 关键字，`timezone` 优先；不把 `tz` 公开到 Schema。
- 验证方式：`current_time(tz=...)` 与 `Registry.execute({"timezone": ...})` 双路径测试。
- 验证结果：`tz` 直调与 `timezone` Registry 路径均通过；Schema 只含 `timezone`；大小写/空串/不存在时区均 `invalid_timezone`。
- 状态：Resolved
- 关联提交：S08 time change（见最终报告）

### ISSUE-035 — S08 报告 6 项 P1 修复

- 日期：2026-10-23
- 现象：Windows 无 tzdata、Registry 非字符串错误码、Schema 暴露 tz、固定时钟断言不足、ISSUE-034 后补、S07 归档后修复绕过 change。
- 解决方案：声明 Windows tzdata；TimeArgs before validator + handler 统一 invalid_timezone；Schema 描述去 tz；完整 ISO/naive 断言；新 change `s07-s08-report-fixes` 追溯 S07/S08。
- 验证结果：192 passed、覆盖率 96.34%；unit 128、contract 64；干净 Windows venv 安装 wheel 后默认/UTC 成功；mypy 55 files 0 errors；OpenSpec 7 passed。
- 历史限制：ISSUE-034 后补无法回改；由新 change 记录流程例外，后续先记账。
- 状态：Resolved
- 关联提交：S08 报告修复提交（见最终报告）

### ISSUE-036 — S09 报告 P1/P2 修复

- 日期：2026-10-23
- 现象：完整 Schema 含 session_id、invalid_action 在 Registry 不可达、index 宽松转换、TC 计数/隔离断言不足、Store 返回共享对象。
- 解决方案：TodoArgs 描述去 session_id；action=str 交给 handler；index strict；complete 后仍 2 项；补跨会话/伪造/快照；TodoItem frozen + Store 快照 + configure_todo_store。
- 验证结果：192 passed、覆盖率 96.34%；unit 128、contract 64；mypy 57 files 0 errors；OpenSpec/wheel 通过。
- 状态：Resolved
- 关联提交：`s09-report-fixes` change（见最终报告）

### ISSUE-037 — S10 报告 P1/P2 修复

- 日期：2026-10-23
- 现象：Windows 反斜杠隐藏段/任意 `..` 绕过、非文本 codec、stat 后增长、skip、错误码过粗与计数矛盾。
- 解决方案：POSIX+Windows 拆段、任意 `..` path_escape、设备名拒绝；文本 codec 校验；最多读 limit+1；file_not_found/file_read_error 区分；移除 skip；新 change 承接。
- 验证结果：224 passed、覆盖率 96.76%；unit 160、contract 64；mypy 59 files 0 errors；OpenSpec/wheel 通过。
- 状态：Resolved
- 关联提交：`s10-report-fixes` change（见最终报告）

### ISSUE-038 — S11 报告 P0/P1 修复与 Prompt 时序偏差

- 日期：2026-10-23
- 现象：resolve 后父目录替换可越界写；overwrite=false 并发覆盖；设备名不完整；TC-L4-002 错配；计数矛盾；Prompt 后补。
- 解决方案：temp/parent 多次 containment；overwrite=false 用 os.link 原子发布；补全 COM/LPT；文件 E2E 待 S18；统一计数；新 change 承接。
- 验证结果：247 passed、覆盖率 97.06%；unit 183、contract 64；mypy 61 files 0 errors；OpenSpec 11 passed。
- 历史限制：S11 Prompt 在实现/收口提交后补，无法回改；后续先留 Prompt 再提交。
- 状态：Resolved
- 关联提交：`s11-report-fixes` change（见最终报告）

### S13 阶段问题记录（2026-10-23）

- 新增 redis>=7.4,<8 运行依赖、fakeredis>=2.23,<3 dev；无其他缓存库。
- `Agent.run(user_input, session_id=None)` 增量兼容；`AgentResult.session_id` 可选；旧单参数调用不写 Redis。
- ShortTermMemory JSON 完整轮次、LTRIM 10 轮、TTL 24h、跨会话 key；Redis/序列化失败 memory.degraded。
- 验收：279 passed、覆盖率 95.76%；unit 198、contract 64、integration 17、unmarked 0；mypy 65 files 0 errors；OpenSpec/wheel 通过。
- 无新增阻塞；TC-L3-014 Mongo/Context 部分留 S14/S16；TC-L3-011/012 留 S17/S18。

### S14 阶段问题记录（2026-10-23）

- 新增 pymongo>=4.9,<5 运行依赖、mongomock>=4.3,<5 dev；未引入 motor/beanie。
- MidTermMemory：StoredRound + session_id/created_at；索引 `session_created_desc` 幂等；检索 session/content，公开剥离 reasoning。
- Agent 响应后异步 Mongo；失败 memory.degraded；Redis 仍在响应前同步。
- 验收：294 passed、1 skipped；unit 198、contract 64、integration 32；覆盖率 95.79%。
- S13 ISSUE-040（POSIX Linux 未实跑）/041（覆盖率）仍 Open。

### S15 阶段问题记录（2026-10-23）

- 新增 tiktoken>=0.12,<0.13；不引入 transformers/sentencepiece/openai；测试注入假 encoder，不依赖模型下载。
- ContextBuilder 只拼接/计数，不裁剪；S16 才做整轮丢弃、双触发与 ContextTooLarge。
- ContextPayload 仅 S15 字段；tools_snapshot 原引用复用。
- 验收：305 passed、1 skipped；unit 198、contract 64、integration 43；覆盖率 95.93%。
- 当前环境无 Python 3.11；S13 ISSUE-040/041 仍 Open。

### S15 报告修复记录（2026-10-23）

- Agent 接入 ContextBuilder；tools_snapshot 不可变 tuple；Memory 读取超时；round_id 同源/跨源去重；reasoning 计数开关。
- 补 Agent→LLM 快照、超时、去重、reasoning 测试；骨架清单去重、EOF/空白修复。
- 验收：305 passed、1 skipped；unit 198、contract 64、integration 43、unmarked 0；覆盖率 95.93%。

### S16 阶段问题记录（2026-10-24）

- 只持久化当前轮；fit 纳入 deadline；ContextTooLarge 补 trace/tool_traces。
- trim_reason 累计、日志分项/超限事件、max_rounds 可配置。
- 验收：316 passed、1 skipped；unit 198、contract 64、integration 54；覆盖率 95.94%。
- S15 报告复验/Python3.11/S13 POSIX 仍 Open。

### ISSUE-043 — 真实 MySQL 未运行（已关闭）

- 日期：2026-10-24
- 现象：本机 MySQL80 服务无法启动，Docker 无可用 MySQL 镜像；S17 使用 SQLite 异步仓储 + MySQL schema 静态测试。
- 影响：MySQL 8 JSON/时间精度/ON DUPLICATE KEY UPDATE 未在真实实例验证；S17 PLAN 标注“SQLite 仓储验证”。
- 复现：设置 `MYSQL_TEST_DSN` 后在 MySQL 8 执行 schema + 仓储测试；当前环境无法提供。
- 状态：Resolved（2026-10-24，Docker mysql:8.0，端口 3307；schema/upsert/session/audit/metrics/索引实测通过）
- 复现命令：`docker run -d --name agent-mini-mysql -e MYSQL_ROOT_PASSWORD=testpass -e MYSQL_DATABASE=agent_mini -p 3307:3306 mysql:8.0`；`MYSQL_TEST_DSN=mysql+asyncmy://root:testpass@127.0.0.1:3307/agent_mini pytest tests/integration/test_systemdb.py`

### ISSUE-044 — LIVE 验收未运行

- 日期：2026-10-24
- 现象：`DEEPSEEK_API_KEY` 与 `RUN_LIVE` 均未设置，TC-LIVE-001/002/003 未执行。
- 处理：不伪造通过；启用命令：`RUN_LIVE=1 DEEPSEEK_API_KEY=... pytest -m live`。
- 状态：Open

### ISSUE-039 — S12 TC-L3-006 与 search 不匹配

- 日期：2026-10-23
- 现象：PLAN S12/FR-TOOL-08 引用 TC-L3-006，但该 TC 实际验证 mock LLM 触发 calculator，与 search 无关。
- 根因：测试编号映射错误，search 缺少独立集成/E2E TC。
- 解决方案：S12 以 TC-L1-021 为正式验收；TC-L3-006 保留 calculator 原语义；search 独立 E2E 留后续阶段新增，不自行补写 TC。
- 验证结果：新增 TC-L3-015（Agent→Registry→search），断言 `not_configured` 与 tool_trace；TC-L3-006 保留 calculator 原语义。
- 状态：Resolved（2026-10-23）
- 关联提交：`s12-tool-search`、`s13-closeout`

### ISSUE-040 — POSIX 用例在当前 Windows 环境 skip

- 日期：2026-10-23
- 现象：`test_posix_parent_symlink_is_rejected` 在 Windows 标记 skip；本机无 Linux/WSL Python 3.11，无法实跑 POSIX dir_fd 路径。
- 影响：代码已实现 dir_fd/O_DIRECTORY/O_NOFOLLOW/linkat/renameat；POSIX 运行证据待 Linux CI；当前机器无 Python 3.11。
- 状态：Open（S14 前在 Linux 复跑；不伪造通过）
- 关联：`s13-closeout`

### ISSUE-041 — 覆盖率低于 97.04%

- 日期：2026-10-23
- 现象：S13 收尾后总覆盖率 95.76%，低于 S12 的 97.04%；主要为 POSIX-only/平台错误分支。
- 处理：POSIX-only 代码以 pragma 排除；其余分支目标 S14 补测。
- 状态：Open（S14 前补测或维持豁免）

### ISSUE-042 — 21780eb 提交粒度偏差

- 日期：2026-10-23
- 现象：`21780eb`（OpenSpec 计划提交）意外包含 `tests/unit/test_short_term.py` → `tests/integration/` rename。
- 处理：历史不改写；登记粒度偏差，后续按 change/代码/测试/文档拆分。
- 状态：Resolved（记录性）

### S11 阶段问题记录（2026-10-23）

- 实现：write_file 复用 Sandbox；父目录必须存在；默认不覆盖，overwrite=true 才替换。
- 原子：同目录 mkstemp + fsync + os.replace；失败 unlink；校验/编码/超限在临时文件前返回。
- 往返：空内容/换行与 read_file 一致；安全用例覆盖 ../、绝对路径、隐藏、symlink 目标、父目录缺失、编码错误。
- 验收：247 passed、覆盖率 97.06%；unit 183、contract 64；mypy 61 files 0 errors；OpenSpec/wheel 通过。
- 无新增阻塞；TC-L4-002 留 S18；并发非 CAS。

### S10 阶段问题记录（2026-10-23）

- 实现：`Sandbox` 四步校验、read_file、`ToolContext.sandbox_root/max_file_size`。
- 安全：`..`、绝对路径、junction/symlink 逃逸、NTFS 流、隐藏、超长、扩展名大小写均阻断。
- 限制：默认 1 MiB、扩展名白名单、路径 240、禁止隐藏；空文件正常；二进制/解码/编码结构化错误。
- TOCTOU：resolve 后 open，最小防护，未宣称强原子性。
- 验收：224 passed、覆盖率 96.76%；unit 160、contract 64；mypy 59 files 0 errors；OpenSpec/wheel 通过。
- 无新增阻塞；write_file 留 S11。

### S09 阶段问题记录（2026-10-23）

- 实现：`TodoArgs`/`@tool("todo")`、`TodoStore` Protocol、进程内 `MemoryTodoStore`；ToolContext 仅注入声明 context 的 handler。
- 安全：session_id 不在 Schema，Registry 白名单拒绝伪造；A/B 隔离测试。
- TDD：初始 11 个用例因占位 store/todo 未实现而红；实现后 11 个 todo 测试全绿。
- 验收：192 passed、覆盖率 96.34%；unit 128、contract 64；mypy 57 files 0 errors；OpenSpec/wheel 通过。
- 无新增阻塞；TC-L4-009/010 留 S18；S13 替换 MemoryStore。

### S07 阶段问题记录（2026-10-23）

- calculator 实现：AST 白名单、阈值 200/20/1e12、7 个错误码；注册到默认 ToolRegistry。
- TDD：23 个 calculator 用例在占位实现下全部失败；实现后 25 个 calculator 测试全绿。
- 验收：164 passed、覆盖率 95.81%；unit 100、contract 64；mypy 53 files 0 errors；OpenSpec/wheel 通过。
- 无新增阻塞问题；具体其他工具、沙箱、Memory/Context、HTTP 未实现。

### S05 阶段问题记录（2026-10-22）

- 前置：`LoopPolicy` 参数化提交 `1a9bdb3`，默认不限制；S04 行为不变、99 passed。
- PLR 规则核对：`pyproject.toml` 已启用 `too-many-statements`/`too-many-branches`，`ruff check --select PLR0915,PLR0912 agent_mini/runtime/loop.py` 无告警；S05 拆分后 `run_react_loop` 保持可读。
- 实现：max_steps=8、deadline=120s、repeat=3；truncated/termination_reason；固定文案；deadline 用 wait_for 取消；重复按连续 name+规范化 args；中断补齐 tool 消息。
- 验收：112 passed、覆盖率 95.72%；unit 48、contract 64；`mypy agent_mini tests` 49 files 0 errors；OpenSpec 通过；M1 S00–S05 收口。
- 无新增阻塞；S06/S13–S18 未实现。

### M3 补齐（2026-10-24）

- 新增 `test_tool_overflow_keeps_trace_and_does_not_replay`：工具后超限，LLM 只调用 1 次、工具只执行 1 次，异常含 steps/trace/tool_traces。
- 新增 M3 离线演示 `tests/integration/test_m3_demo.py`：三轮只写当前轮、跨轮历史、12 轮裁到 10 轮。
- README 增加 M3 演示命令，更新到 S16。
- 验收：316 passed、1 skipped；unit 198、contract 64、integration 54；覆盖率 95.94%。

### ISSUE-045 — 依赖审计仍报漏洞（已关闭）

- 日期：2026-10-24
- 现象：S18 阶段 `pip-audit` 曾报 certifi/urllib3；S19 升级 FastAPI 0.162/Starlette 1.9.0 后 `pip-audit .` 无已知漏洞。
- 影响：无；保留记录供审计追溯。
- 状态：Resolved（2026-10-24）
