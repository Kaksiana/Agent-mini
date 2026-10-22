## 1. 规划

- [ ] 1.1 编写 proposal、spec、design、tasks 并通过 OpenSpec 校验
- [ ] 1.2 在 ISSUE-021/022 记录依赖与报告问题，PLAN 回退 S01 为“进行中”

## 2. TDD 红

- [ ] 2.1 新增非 object 顶层响应测试
- [ ] 2.2 新增保留字段覆盖测试
- [ ] 2.3 新增 reasoning 角色约束测试
- [ ] 2.4 新增 dev 依赖 minor 上界与 pytest-cov 测试
- [ ] 2.5 运行新增测试并确认红因

## 3. 实现（绿）

- [ ] 3.1 硬化 `LLMResponse.from_openai` 与 `Message` 校验
- [ ] 3.2 拒绝受控字段覆盖
- [ ] 3.3 更新 dev 依赖 pin 并安装 pytest-cov
- [ ] 3.4 运行全量测试至绿

## 4. 文档与验收

- [ ] 4.1 同步 PLAN/TESTING/DESIGN/README/MEMORY/ISSUE/S01-report
- [ ] 4.2 `pip install -e ".[dev]"`、`pytest`、`pytest --cov`、ruff/format/mypy
- [ ] 4.3 `openspec validate --all --strict`
- [ ] 4.4 wheel 构建与仓库外导入
- [ ] 4.5 归档 change 并提交推送
