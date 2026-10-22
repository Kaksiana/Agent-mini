## 1. 规划

- [x] 1.1 登记 ISSUE-026，PLAN S02 回退“进行中”，编写 OpenSpec artifacts
- [x] 1.2 运行 `openspec validate s02-report-fixes --strict`

## 2. TDD 红

- [x] 2.1 新增 RetryPolicy 边界与运行时类型测试
- [x] 2.2 新增 RetryEvent 记录测试
- [x] 2.3 新增 timeout 配置传递与 ReadTimeout 测试
- [x] 2.4 新增 3xx/未知状态分类与具体异常/http_status 测试
- [x] 2.5 新增 S01 TC-L2-007 thinking+tools 组合回归
- [x] 2.6 运行新增测试，确认红因

## 3. 实现（绿）

- [x] 3.1 限制 RetryPolicy 1–3，补运行时校验与 RetryEvent
- [x] 3.2 修复退避 cap 单调性、状态分类与 llm 子包说明
- [x] 3.3 运行新增及全量测试至绿

## 4. 文档与验收

- [x] 4.1 同步 DESIGN/TESTING/ISSUE/MEMORY/PROMPT/README/S02-report
- [x] 4.2 全量 pytest、覆盖率、ruff/format/mypy、openspec
- [x] 4.3 wheel 构建与仓库外导入
- [x] 4.4 归档 change、提交推送

## 5. 收口

- [x] 5.1 恢复 S02“已完成”，关闭 ISSUE-026
- [x] 5.2 归档 change 并校验主规格
- [x] 5.3 按 Conventional Commits 提交并推送
