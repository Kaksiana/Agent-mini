## 1. 规划

- [ ] 1.1 登记 ISSUE-030，创建 change 并通过 strict validate

## 2. TDD 红

- [ ] 2.1 独立工具结果密钥测试（P0）
- [ ] 2.2 非法参数/未知工具后合法调用并收敛测试（P1-01）
- [ ] 2.3 executor 异常回灌并收敛测试（P1-02）
- [ ] 2.4 记录逐 TC 红因与精确失败输出

## 3. 实现

- [ ] 3.1 统一公开 observation 脱敏与单常量
- [ ] 3.2 确认失败/成功 trace 与 call_id 配对
- [ ] 3.3 保持 S03 直答与无 executor 协议拒绝回归

## 4. 规格与收口

- [ ] 4.1 修订 runtime 主规格为 S03+S04 累计契约与 Purpose
- [ ] 4.2 同步 S04-report/PLAN/TESTING/ISSUE/MEMORY/PROMPT
- [ ] 4.3 全量 pytest、覆盖率、ruff/format、mypy tests、OpenSpec、wheel
- [ ] 4.4 归档 change、提交推送
