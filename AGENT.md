# AGENT

> **Agent-mini 全局开发规范** — 本文件是 AI Agent 与人类开发者共同遵守的唯一开发准则。
> 凡与本文件冲突的个人习惯，以本文件为准；本文件的修改必须走独立 commit 并在 `Docs/PROMPT.md` 记录原因。

| 项目 | 内容 |
| --- | --- |
| 适用范围 | 本仓库全部代码、文档、配置与提交 |
| 生效日期 | 2026-10-21 |
| 维护方式 | 仅通过 PR/独立 commit 修改，禁止随手改 |

---

## 1. 文档优先（Docs First）

### 要求

1. 任何**新功能、行为变更、接口变更、架构调整**，必须先落文档，再写代码，顺序不可颠倒：
   `需求确认 → 文档（OpenSpec change 或 Docs/ 文档）→ 评审通过 → 编码 → 文档回填`
2. 文档必须包含四要素：**目标、验收标准、影响范围、回滚方式**。缺少任一要素视为未完成。
3. 每一条验收标准必须能对应到后续的一个测试用例；无法映射的验收标准要么细化，要么删除。
4. 紧急线上修复允许代码先行，但必须在**同一个 PR / 同一批推送**内补齐文档，并在 `Docs/ISSUE.md` 记录"文档滞后"的原因。
5. 禁止把"先写代码、之后补文档"作为默认工作流。

### 执行时机

- 开工前：任何代码 commit 之前，文档 diff 必须先存在。
- 需求变更时：先改文档再改实现，不允许文档与实现长期不一致。
- 合并/推送前：复核文档与实现是否同步。

### 验证方式

- 查看提交顺序：`git log --oneline` 中文档类提交应先于或同批次于实现提交。
- 文档中存在可勾选的"验收标准"清单，且条目数与被测用例数一致。
- 走 OpenSpec 流程的改动：`openspec validate` 必须通过。

---

## 2. 测试驱动开发（TDD）

### 要求

1. 严格执行 **红 → 绿 → 重构**：
   - **红**：先写会失败的测试，并确认失败原因正确（不是语法错误或环境缺失）。
   - **绿**：写最小实现让测试通过，不做无关优化。
   - **重构**：在测试全绿前提下清理重复与坏味道，重构后测试必须仍然全绿。
2. 新增或修改的每个函数/模块必须有对应测试；**测试文件与被测实现必须出现在同一个 commit**。
3. 修 bug 前必须先写**复现测试**，复现测试未失败前不得开始改实现。
4. 禁止提交被 `skip`、`only`、注释掉的测试；禁止为通过测试而放宽断言或删除用例。
5. 测试必须可独立运行、可重复、不依赖外部网络与真实第三方服务（集成/E2E 测试除外，需显式标记并在 README 说明前置条件）。

### 执行时机

- 写实现代码之前（先写测试）。
- 修复缺陷之前（先写复现测试）。
- 每次推送前（全量测试必须通过）。

### 验证方式

- `git show --stat <commit>` 中测试文件与实现文件同时出现。
- 本地全量测试通过。**测试命令以 `README.md` 中记录的真实脚本为准**；当前仓库技术栈尚未确定，引入测试框架的同一个 PR 必须把可执行的测试命令写入 `README.md`，禁止在规范或文档中虚构命令。
- 若接入覆盖率工具，覆盖率不得低于上一提交。

---

## 3. `Docs/PROMPT.md` — 全过程 AI Prompt 记录

### 要求

1. 记录**每一次**与 AI 的交互，追加写入，**禁止覆盖或删除历史条目**。
2. 每条记录必须包含：时间、**用户原始 Prompt（逐字保留）**、任务目标、关键约束、AI 产出摘要、人工修正与最终决策。
3. 涉及令牌、密钥、个人隐私的内容必须脱敏（写入 `***` 或 `<REDACTED>`），禁止明文入库。
4. 用户原始 Prompt 必须**逐字保留**（含错别字、口语与原始格式），不得改写、不得删减、不得只写摘要；脱敏后仍须保留原意与结构。
5. AI 侧的长篇输出可按摘要记录，但必须保留关键判断、结论与产出物路径。

### 执行时机

- 每轮 AI 交互结束后、提交代码之前。
- 重要决策（技术选型、架构调整、规范变更）发生时立即补记。

### 验证方式

- `Docs/PROMPT.md` 非空，且存在与本次任务对应的条目。
- 每条目含"时间 / 原始 Prompt / 产出"三要素，缺一视为不合格；只有摘要而无原文视为不合格。
- 原始 Prompt 以代码块逐字保留，条目数与用户实际发送轮次一致。
- 提交内容中包含 `Docs/PROMPT.md` 的变更（纯代码提交除外）。

### 条目模板

````markdown
## YYYY-MM-DD HH:mm — <任务简称>

### 原始 Prompt

```text
<用户发送的原文，逐字保留，不得改写或删减>
```

### 执行摘要

- 目标：
- 产出：
- 人工修正 / 决策：
- 关联提交：
````

---

## 4. `Docs/ISSUE.md` — 问题与解决方案记录

### 要求

1. 记录开发过程中遇到的**阻塞问题、缺陷、环境/依赖问题、踩坑点**，先记录再修复。
2. 每条必须包含：编号、日期、现象、根因、解决方案、验证方式、状态。
3. 状态仅允许三种：`Open` / `Resolved` / `Wontfix`；`Wontfix` 必须写明放弃理由。
4. `Resolved` 的条目必须有可复现的验证步骤，否则视为未解决。
5. 修复类 commit 的正文必须引用对应编号（如 `Refs: ISSUE-003`）。

### 执行时机

- 问题发生当下（先记账，再动手）。
- 根因定位后回填"根因"。
- 修复并验证通过后更新状态。

### 验证方式

- 编号连续不跳号；每条状态非空。
- 所有 `Resolved` 条目均含验证步骤。
- `git log` 中修复类提交能反查到 ISSUE 编号。

### 条目模板

```markdown
### ISSUE-001 — <一句话标题>

- 日期：YYYY-MM-DD
- 现象：
- 根因：
- 解决方案：
- 验证方式：
- 状态：Open | Resolved | Wontfix
- 关联提交：
```

---

## 5. Git 规范

### 5.1 `.gitignore`

**要求**

1. 仓库根目录必须存在 `.gitignore`，至少覆盖以下类别：
   - 操作系统：`Thumbs.db`、`.DS_Store`、`desktop.ini`
   - 编辑器/IDE：`.idea/`、`.vscode/`（共享配置除外）、`*.swp`
   - 依赖目录：`node_modules/`、`venv/`、`__pycache__/`、`vendor/`
   - 构建产物：`dist/`、`build/`、`target/`、`*.pyc`、`*.log`
   - 密钥与环境变量：`.env`、`.env.*`、`*.pem`、`*.key`、`*.p12`
   - 本地数据与临时文件：`Data/tmp/`、`*.sqlite-journal`、`*.tmp`
2. 严禁将密钥、令牌、证书、大体积二进制文件提交进仓库。
3. **当前事实**：截至 2026-10-21 本仓库 `.gitignore` **尚未创建**。按本规范应在首次功能性提交前补齐；补齐动作需单独 commit（`chore(git): add .gitignore`）。

**执行时机**：首次提交前创建；新增技术栈或新增产物类型时同步补充。

**验证方式**

- `git check-ignore -v <路径>` 能命中预期规则。
- `git ls-files` 中不含 `.env`、`*.key`、`*.pem` 等敏感文件。
- `git status` 中不出现应被忽略的产物文件。

### 5.2 Commit 编写规范

**格式**：遵循 Conventional Commits

```
<type>(<scope>): <subject>

<body: 说明 why 与影响面>

<footer: Refs / Closes>
```

**type 取值**

| type | 用途 |
| --- | --- |
| `feat` | 新功能 |
| `fix` | 缺陷修复 |
| `docs` | 仅文档变更 |
| `test` | 仅测试变更 |
| `refactor` | 不改变外部行为的重构 |
| `perf` | 性能优化 |
| `chore` | 构建/依赖/杂项 |
| `build` | 构建系统或打包配置 |
| `ci` | CI/CD 配置 |

**规则**

1. `subject` 用祈使句、小写开头、结尾不加句号、不超过 50 字符。
2. 正文说明**为什么改**与影响范围，每行不超过 72 字符；只改了什么一眼可见的简单提交可省略正文。
3. 一个 commit 只做一件事；文档、测试、实现如需分离，按依赖顺序分别提交。
4. 禁止 `update`、`fix bug`、`修改` 等无信息量消息；禁止中英混排的含糊描述。
5. 关联 issue 使用 `Refs: #12`（引用）或 `Closes: #12`（关闭）。

**执行时机**：每次提交前自查。

**验证方式**

- `git log --oneline -5` 目视符合 `^(feat|fix|docs|test|refactor|perf|chore|build|ci)(\(.+\))?: .+$`。
- 可用如下命令机械校验：

```bash
git log --format=%s -20 | grep -Ev '^(feat|fix|docs|test|refactor|perf|chore|build|ci)(\(.+\))?: .+$'
```

输出为空则通过。

### 5.3 主动推送

**要求**

1. 完成**一个可验证单元**（文档齐全 + 测试通过 + 提交规范）即推送，不积压本地提交。
2. 推送前必须先同步远端：`git pull --rebase origin <branch>`；冲突解决后**必须重跑测试**。
3. 推送失败不得静默跳过，必须记录到 `Docs/ISSUE.md` 并报告失败原因（权限、网络、保护分支等）。
4. `main` 分支禁止 force push（`git push --force`）；需要改写历史时走独立分支 + PR。
5. 推送后确认本地与远端一致，避免"以为推了其实没推"。

**执行时机**

- 每个可验证单元完成后。
- 每日工作结束前。
- 切换任务前（先让当前改动落地）。

**验证方式**

- `git status -sb` 显示 `## main...origin/main` 且**无** `ahead`/`behind` 标记。
- `git log origin/main..HEAD --oneline` 输出为空（无未推送提交）。
- `git remote -v` 中 `origin` 指向 `https://github.com/Kaksiana/Agent-mini.git`。

---

## 6. 开发代码使用 OpenSpec 与 SuperPower SKILL

### 6.1 OpenSpec

**环境事实（2026-10-21 实测）**

- `openspec` CLI 可用，版本 `1.12.0`。
- 本仓库**尚未执行 `openspec init`**，即 `openspec/` 目录尚不存在；首次使用前需初始化。

**要求**

1. 新功能或行为变更必须先建 change，再编码：
   `openspec new change <change-id>`（或使用 `openspec-propose` 技能）
2. change 内必须产出 `proposal` / `design`（如需要）/ `tasks`，`tasks` 拆分到可勾选的粒度。
3. 实现阶段逐条勾选 tasks；实现完成、验证通过后执行归档（`openspec-archive-change`）。
4. 归档前必须 `openspec validate` 通过；未通过不得归档。
5. 禁止绕过 change 直接改行为（纯文档、纯配置调整除外）。

**执行时机**

- 需求确认后、写第一行代码前：建 change。
- 实现完成后：校验并归档。
- 规范或文档类改动：使用 `openspec-sync-specs` / `write-openspec-docs` 保持规格同步。

**验证方式**

- `openspec list` 能看到当前活跃 change。
- `openspec validate <change-id>` 返回通过。
- 仓库中存在 `openspec/` 目录及对应 change 文件。

### 6.2 SuperPower SKILL

**环境事实（2026-10-21 实测）**

- 技能已安装于 `C:\Users\Ryan\.agents\skills`（`C:\Users\Ryan\.claude\skills` 为镜像）。
- 可用技能包含：`using-superpowers`、`brainstorming`、`writing-plans`、`executing-plans`、`test-driven-development`、`requesting-code-review`、`receiving-code-review`、`verification-before-completion`，以及 OpenSpec 系列（`openspec-propose`、`openspec-apply-change`、`openspec-archive-change` 等）。

**要求**

1. 会话开始先加载 `using-superpowers`，按其中规则决定后续技能调用。
2. 按阶段使用技能，不得跳步：

   | 阶段 | 应使用技能 |
   | --- | --- |
   | 需求模糊、方案未定 | `brainstorming` |
   | 需求明确、需要拆解 | `writing-plans` |
   | 开始实现 | `executing-plans` + `test-driven-development` |
   | 提交前 | `verification-before-completion` |
   | 合并前 | `requesting-code-review` |
   | 收到评审意见 | `receiving-code-review` |

3. 技能**实际不可用**时（文件缺失、加载失败、环境不支持），必须在 `Docs/ISSUE.md` 记录并说明降级方案，**禁止假装调用或编造技能执行结果**。
4. 涉及 OpenSpec 的工作优先使用 OpenSpec 系列技能，而非手工拼命令。

**执行时机**：见上表，按开发阶段触发。

**验证方式**

- `Docs/PROMPT.md` 或 PR 描述中标注了本次实际使用的技能名。
- 对应产出物可查：计划文档、测试用例、验证记录、评审意见。
- 若声明使用了某技能，其产物必须存在，否则视为虚报。

---

## 7. 提交前检查清单

每次 `git commit` 前逐项确认，任一项不满足不得提交：

- [ ] 文档已先行更新，验收标准可映射到测试用例
- [ ] 测试先于实现编写，且当前全绿
- [ ] `Docs/PROMPT.md` 已追加本轮 AI 交互记录（含脱敏）
- [ ] `Docs/ISSUE.md` 已记录新问题或关闭已解决问题
- [ ] commit message 符合 Conventional Commits
- [ ] 新增产物已被 `.gitignore` 覆盖
- [ ] `git pull --rebase` 后无冲突，且冲突解决后已重跑测试
- [ ] 推送成功并通过 `git status -sb` 确认与远端同步

---

## 8. 变更记录

| 日期 | 变更 | 说明 |
| --- | --- | --- |
| 2026-10-21 | 初版 | 建立文档优先、TDD、Prompt/Issue 记录、Git 规范、OpenSpec 与 SuperPower SKILL 六项全局规范 |
