## 1. 修正准备

- [ ] 1.1 在 ISSUE-018 记录 wheel 缺失 `schema.sql`，并将 PLAN 中 S00 回退为“进行中”
- [ ] 1.2 编写 proposal、spec、design 与 tasks 并通过 OpenSpec 校验

## 2. TDD 红

- [ ] 2.1 新增打包配置测试，断言 `agent_mini.systemdb` 的 package-data 含 `schema.sql`
- [ ] 2.2 运行该测试，确认因缺少 package-data 而失败

## 3. 修正与补充测试（绿）

- [ ] 3.1 在 `pyproject.toml` 增加 `schema.sql` package-data
- [ ] 3.2 新增 DESIGN §2.2 文件清单测试、占位模块 AST 测试、schema 注释测试
- [ ] 3.3 运行 pytest，确认打包测试与原有测试全部通过

## 4. 验收

- [ ] 4.1 构建 wheel，确认 35 个 `agent_mini/` 文件全部存在（含 `schema.sql`）
- [ ] 4.2 `pip install -e .` 成功
- [ ] 4.3 子包导入全部成功
- [ ] 4.4 `pytest` 全绿
- [ ] 4.5 `ruff check .` 零告警
- [ ] 4.6 `ruff format --check .` 无差异
- [ ] 4.7 `mypy agent_mini` 无错误
- [ ] 4.8 `openspec validate --all --strict` 通过

## 5. 收口

- [ ] 5.1 更新 PLAN、MEMORY、PROMPT、ISSUE，恢复 S00“已完成”
- [ ] 5.2 归档 change 并校验主规格
- [ ] 5.3 按 Conventional Commits 提交并推送
