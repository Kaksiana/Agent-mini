## 1. TDD 红

- [x] 1.1 工具本地 TimeoutError 回归
- [x] 1.2 非法→合法空对象签名回归
- [x] 1.3 非有限/布尔 deadline 回归
- [x] 1.4 LLM deadline steps 回归
- [x] 1.5 记录逐 TC 红因

## 2. 实现

- [x] 2.1 区分本地 TimeoutError 与 deadline
- [x] 2.2 重复签名仅成功调用
- [x] 2.3 有限 deadline + 入口先计时
- [x] 2.4 保留尝试 steps
- [x] 2.5 补 TC-L1-029 矩阵与 M1 演示命令

## 3. 规格与收口

- [x] 3.1 累计 runtime 主规格修复
- [x] 3.2 同步 S05-report/PLAN/README/MEMORY/ISSUE/PROMPT
- [x] 3.3 全量验收、wheel、归档、推送
