## 1. 修正准备

- [x] 1.1 在 ISSUE-017 记录差异清单，并将 PLAN 中 S00 回退为“进行中”
- [x] 1.2 编写 proposal、spec、design 与 tasks 并通过 OpenSpec 校验

## 2. TDD 红

- [x] 2.1 新增 `tests/unit/test_package_skeleton.py`，覆盖全部子包导入
- [x] 2.2 运行该测试，确认因缺少子包而失败

## 3. 骨架补全（绿）

- [x] 3.1 创建 10 个子包目录与 `__init__.py`
- [x] 3.2 创建 `DESIGN.md` §2.2 列出的 23 个占位模块/文件
- [x] 3.3 运行 pytest，确认原 smoke 与新增骨架测试均通过

## 4. 验收

- [x] 4.1 `pip install -e .` 成功
- [x] 4.2 全部子包导入成功
- [x] 4.3 `pytest` 全绿
- [x] 4.4 `ruff check .` 零告警
- [x] 4.5 `ruff format --check .` 无差异
- [x] 4.6 `mypy agent_mini` 无错误
- [x] 4.7 `openspec validate --all --strict` 通过

## 5. 收口

- [x] 5.1 更新 PLAN、MEMORY、PROMPT、ISSUE，恢复 S00“已完成”
- [ ] 5.2 归档 change 并校验主规格
- [ ] 5.3 按 Conventional Commits 提交并推送
