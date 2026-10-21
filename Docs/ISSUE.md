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
- 解决方案：首次使用 OpenSpec 流程前执行 `openspec init` 初始化目录结构（本次未执行，避免超出当前任务范围）。
- 验证方式：`openspec list` 可正常返回；仓库根目录存在 `openspec/` 目录。
- 状态：Open
- 关联提交：无

### ISSUE-006 — 空目录不被 Git 跟踪，骨架目录不会入库

- 日期：2026-10-21
- 现象：`Frontend/`、`Backend/`、`Data/`、`Script/` 为本地空目录，`git status` 不显示，提交后远端仓库中将缺少这些目录。
- 根因：Git 只跟踪文件，不跟踪空目录。
- 解决方案：待确认——在各目录放置 `.gitkeep` 占位文件后提交（本次未执行，需确认后再做）。
- 验证方式：`git ls-files | Select-String 'Frontend/'` 至少返回一条记录。
- 状态：Open
- 关联提交：无
