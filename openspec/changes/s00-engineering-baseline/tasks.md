## 1. OpenSpec 与文档

- [ ] 1.1 编写 proposal、spec、design 与 tasks
- [ ] 1.2 运行 `openspec validate s00-engineering-baseline --strict` 通过

## 2. 测试先行（红）

- [ ] 2.1 在 `pyproject.toml` 配置 pytest、ruff、mypy
- [ ] 2.2 编写 `tests/unit/test_smoke.py` 覆盖 TC-SMOKE-001
- [ ] 2.3 运行 `python -m pytest tests/unit/test_smoke.py -q`，确认因 `agent_mini` 不存在而失败

## 3. 最小实现（绿）

- [ ] 3.1 创建 `agent_mini/__init__.py`，提供 `__version__` 与 `get_version()`
- [ ] 3.2 更新 `README.md` 安装、测试与静态检查命令
- [ ] 3.3 运行 `pytest`，确认 TC-SMOKE-001 通过

## 4. 验收

- [ ] 4.1 运行 `pip install -e .` 成功
- [ ] 4.2 运行 `pytest` 全绿
- [ ] 4.3 运行 `ruff check .` 零告警
- [ ] 4.4 运行 `mypy agent_mini` 无错误

## 5. 阶段收口

- [ ] 5.1 更新 `Docs/PLAN.md` 进度、`MEMORY.md`、`Docs/PROMPT.md`、`Docs/ISSUE.md`
- [ ] 5.2 归档 OpenSpec change 并校验主规格
- [ ] 5.3 按 Conventional Commits 提交并推送
