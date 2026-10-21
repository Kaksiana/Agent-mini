# ISSUE

> 开发过程中遇到的问题与解决方案。规则见 `AGENT.md` §4。
> 状态取值：`Open` / `Resolved` / `Wontfix`。

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
