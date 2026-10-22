## 1. 规划与依赖

- [x] 1.1 编写 proposal、spec、design、tasks 并通过 OpenSpec 校验
- [x] 1.2 在 `pyproject.toml` 声明 `httpx`、`pydantic`、`respx`、`pytest-asyncio`
- [x] 1.3 安装依赖并确认可导入

## 2. TDD 红

- [x] 2.1 编写 TC-L2-001/002/003 契约测试
- [x] 2.2 编写 TC-L2-007 thinking/reasoning 契约测试
- [x] 2.3 编写 TC-L2-008 判别测试
- [x] 2.4 编写 TC-L2-009/010 工具参数与多调用解析测试
- [x] 2.5 运行新增测试，确认红因是实现缺失

## 3. 实现（绿）

- [x] 3.1 实现 `llm/models.py` 与 `llm/errors.py`
- [x] 3.2 实现 `llm/client.py` 的请求、归一与判别
- [x] 3.3 运行新增测试至全绿
- [x] 3.4 重构并保持全量测试通过

## 4. 验收

- [x] 4.1 `pip install -e .` 成功
- [x] 4.2 `pytest` 全绿（含 S00 用例）
- [x] 4.3 `ruff check .` 零告警
- [x] 4.4 `ruff format --check .` 无差异
- [x] 4.5 `mypy agent_mini` 无错误
- [x] 4.6 `openspec validate --all --strict` 通过
- [x] 4.7 wheel 构建与仓库外导入验证通过

## 5. 收口

- [x] 5.1 更新 PLAN、MEMORY、PROMPT、ISSUE、DESIGN/TESTING/README（如需）
- [ ] 5.2 归档 change 并校验主规格
- [ ] 5.3 按 Conventional Commits 提交并推送
