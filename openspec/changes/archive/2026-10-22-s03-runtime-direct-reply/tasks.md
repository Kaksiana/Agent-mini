## Phase 1 — 文档补全（先于实现）

- [x] 1.1 DESIGN §3.2 增加 `AgentResult` 字段表、`Agent.run(user_input)` 签名、session_id 延后 S13、异常契约；伪代码 final→reply
- [x] 1.2 TESTING 增加 TC-L1-015A/B/C、S03 覆盖边界、`mypy agent_mini tests` 准出条款
- [x] 1.3 PLAN 更新 S03 测试项/接口；ISSUE-028 关闭并记录方向 A；核对 ISSUE-024/025 不阻塞
- [x] 1.4 `openspec validate s03-runtime-direct-reply --strict` 通过后才进入 Phase 2

## Phase 2 — TDD 实现

- [x] 2.1 写 TC-L1-015A 直答测试并确认红因
- [x] 2.2 写 TC-L1-015B 空响应测试并确认红因
- [x] 2.3 写 TC-L1-015C 异常传播测试并确认红因
- [x] 2.4 实现 `AgentResult` 冻结模型
- [x] 2.5 实现 `Agent` 构造器注入与单轮直答
- [x] 2.6 运行新增测试至绿，补工具意外/无 content 防御测试

## Phase 3 — 验收与收口

- [x] 3.1 `pip install -e .`、`pytest -m unit`、`pytest -m contract`、全量 `pytest`
- [x] 3.2 覆盖率、`ruff check .`、`ruff format --check .`、`mypy agent_mini tests`
- [x] 3.3 `openspec validate --all --strict`
- [x] 3.4 wheel 构建、内容完整性与仓库外导入
- [x] 3.5 PLAN/DESIGN/TESTING/ISSUE/MEMORY/PROMPT/README 收口
- [x] 3.6 归档 change、提交推送
