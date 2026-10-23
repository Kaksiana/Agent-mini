## Context

S15 只做拼接/计数；S16 才做整轮裁剪与 ContextTooLarge。StoredRound 是唯一历史契约。

## Decisions

- `ContextPayload` 仅 S15 字段；不引入 rounds_before/after/dropped/trim_reason。
- 顺序：system → 可选工具摘要（system）→ 可选中期摘要（system）→ 历史 rounds 消息 → 当前 user。
- 历史：MidTermStore.get_rounds（时间正序、私有 reasoning）与 ShortTermStore.get_recent_rounds 合并，按 round_id 去重；只消费 StoredRound。
- tools_snapshot：原对象保存并原样传给计数器，不复制/排序。
- 公式常量：DEFAULT_MAX_OUTPUT_TOKENS=1024、SAFETY_MARGIN_RATIO=0.10、DEFAULT_PROTOCOL_OVERHEAD_TOKENS=256；budget 用整数 floor。
- JSON：ensure_ascii=False、sort_keys=True、separators=(",", ":")。
- tiktoken：默认 lazy get_encoding(cl100k_base)；失败或编码不可用走字符比例（ASCII 0.3、非 ASCII 0.6，ceil），记录 token_counter.degraded；测试注入假 encoder，不依赖网络。
- 空 messages+tools → 总估算 0；否则协议开销固定生效。
- 不抛 ContextTooLarge；超预算仅返回 estimated/budget 供 S16 判断。
