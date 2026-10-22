## 1. 开工与规划

- [x] 1.1 完成 S01 评估遗留的开工会话检查并记录
- [x] 1.2 编写 proposal、spec、design、tasks 并通过 OpenSpec 校验

## 2. TDD 红

- [x] 2.1 编写 TC-L2-004 重试测试
- [x] 2.2 编写 TC-L2-005 超时测试
- [x] 2.3 编写 TC-L2-006 非重试错误测试
- [x] 2.4 运行新增测试，确认红因与目标行为相关

## 3. 实现（绿）

- [x] 3.1 扩展 `llm/errors.py` 异常类型
- [x] 3.2 实现状态/异常分类与退避重试
- [x] 3.3 运行 S02 测试至绿
- [x] 3.4 重构并保持全量测试通过

## 4. 验收

- [x] 4.1 `pip install -e .` 与 `pytest -m unit`
- [x] 4.2 `pytest -m contract` 与全量 `pytest`
- [x] 4.3 覆盖率 ≥ 80%
- [x] 4.4 `ruff check .`、`ruff format --check .`、`mypy agent_mini`
- [x] 4.5 `openspec validate --all --strict`
- [x] 4.6 wheel 构建、内容完整性与仓库外导入

## 5. 收口

- [x] 5.1 同步 PLAN/DESIGN/TESTING/ISSUE/MEMORY/PROMPT/README
- [x] 5.2 归档 change 并校验主规格
- [x] 5.3 提交并推送
