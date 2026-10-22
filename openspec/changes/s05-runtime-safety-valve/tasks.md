## 1. 前置重构

- [ ] 1.1 `LoopPolicy` 参数化与 `run_react_loop` 拆分，默认不限制
- [ ] 1.2 保持 S00–S04 全绿并提交前置 commit
- [ ] 1.3 记录 PLR0915/PLR0912 现状

## 2. 规划

- [ ] 2.1 补 DESIGN truncated/终止原因/文案/deadline/repeat 契约
- [ ] 2.2 创建 change 并 strict validate

## 3. TDD 红

- [ ] 3.1 max_steps=3 永远 tool_calls
- [ ] 3.2 deadline 挂起工具取消与补齐
- [ ] 3.3 连续相同 name+args 3 次
- [ ] 3.4 3 步以上正常收敛回归

## 4. 实现（绿）

- [ ] 4.1 LoopPolicy 默认值与安全阀检查
- [ ] 4.2 truncated/termination_reason/固定文案
- [ ] 4.3 中断补齐 tool_calls
- [ ] 4.4 重构并保持全量测试通过

## 5. 验收与收口

- [ ] 5.1 全量 pytest、覆盖率、ruff/format、mypy tests、openspec
- [ ] 5.2 wheel 与仓库外导入
- [ ] 5.3 PLAN/TESTING/DESIGN/ISSUE/MEMORY/PROMPT/README；M1 记录
- [ ] 5.4 归档 change、提交推送
