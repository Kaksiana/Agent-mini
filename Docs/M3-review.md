# M3 独立复验（2026-10-25）

> 性质：当前 Agent 只读执行，不含独立第三方评审；结论限于自动化证据。

## 命令

```bash
pytest tests/integration/test_m3_demo.py tests/integration/test_short_term.py \
  tests/integration/test_mid_term.py tests/integration/test_context_builder.py \
  tests/integration/test_context_window.py -q
```

## 结果

**51 passed**（1.73s）。

## 覆盖

- M3 demo：三轮只写当前轮、跨轮历史、12 轮裁到 10 轮。
- Redis 短时记忆：失败降级、TTL、整轮裁剪。
- Mongo 中期：索引、去重、降级、超时。
- ContextBuilder/Window：拼接、双触发裁剪、不可删减保留。

## 结论

M3 核心集成用例全绿；**未**做独立人工审阅，不把 M3 标为“独立复验完成”。
