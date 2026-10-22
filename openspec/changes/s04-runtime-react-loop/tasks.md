## 1. 开工核对

- [ ] 1.1 核对 S03 完成状态、ISSUE-024/025，登记 LLMProtocolError 语义债务 ISSUE-029
- [ ] 1.2 登记 AgentResult 增量、ToolExecutor Protocol、S05 边界到 DESIGN
- [ ] 1.3 创建并 strict validate S04 change

## 2. TDD 红

- [ ] 2.1 TC-L1-015/TC-L2-010：两步与多工具配对
- [ ] 2.2 TC-L1-024：ThoughtStep 字段与 runtime_summary
- [ ] 2.3 TC-L1-028/TC-L2-009：错误回灌与修正
- [ ] 2.4 TC-L1-030：reasoning 隐私与敏感参数脱敏
- [ ] 2.5 TC-L3-006 替身：AgentResult.tool_traces

## 3. 实现（绿）

- [ ] 3.1 新增 ThoughtStep/ToolCallTrace 与 AgentResult 增量字段
- [ ] 3.2 实现 ToolExecutor/ToolOutcome 与 ReAct 循环
- [ ] 3.3 实现消息配对、错误回灌、脱敏截断
- [ ] 3.4 清理 S03 tool_calls 语义并保持 S03 回归

## 4. 验收与收口

- [ ] 4.1 全量 pytest、unit/contract、覆盖率
- [ ] 4.2 ruff/format、mypy agent_mini tests、openspec
- [ ] 4.3 wheel 构建、内容与仓库外导入
- [ ] 4.4 PLAN/DESIGN/TESTING/ISSUE/MEMORY/PROMPT/README 收口
- [ ] 4.5 归档 change、提交推送
