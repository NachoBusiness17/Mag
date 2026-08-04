# ClawCodex steal analysis — DeepSeek prefix cache for Mag

**As-of:** 2026-08-04  
**Source:** [agentforce314/clawcodex](https://github.com/agentforce314/clawcodex)  
**Mag prior art:** repack ratio 0.85 + 1M window (`configs/providers.yaml`, 2026-08-02)

## Claim (ClawCodex)

Byte-stable request prefix → DeepSeek disk prefix cache covers `system + tools + history` across turns. Cache-hit input ~$0.0435/1M vs ~$10/1M fresh prefix on frontier models — **order-of-magnitude** savings when the stable span is large.

## Three mechanisms

| # | Mechanism | Mag before | Mag after (this commit) |
|---|-----------|------------|-------------------------|
| 1 | Byte-stable prefix | Pack/timestamp/health in `system` every turn → **cache miss** | `mag/prefix_cache.py`: stable `system` + volatile `<system-reminder>` tail on user turn |
| 2 | Cache-hit telemetry | `record_usage` ignored cache fields | `models/cache_usage.py` + `provider_usage.jsonl` `cache_read_tokens` |
| 3 | `/eco` tool compression | `TOOL_RESULT_CHARS` hard truncate | `mag/tool_eco.py` deterministic filters (pytest/git/pip); `MAG_TOOL_ECO=0` to disable |

## Implementation (shipped)

### Phase 1 — byte-stable prefix (default ON for DeepSeek)

- `stable_system_prompt()` — law + framework only; version tag `mag-stable-system-v1`
- `volatile_reminder(pack_text)` — bonds/brief/anchor/repack notes in `<system-reminder>`
- `run_turn` / `repack_messages` / `run_agent` use stable system; pack moves to user tail
- Env: `MAG_BYTE_STABLE_PREFIX=0` restores legacy monolithic `_system_prompt()`

### Phase 2 — cache telemetry

- DeepSeek usage: `prompt_cache_hit_tokens`, `prompt_cache_miss_tokens`
- Logged per call in `logs/provider_usage.jsonl`
- Aggregated in `quota_state.json` → `cache_read_tokens`, `cache_miss_tokens`

### Phase 3 — tool eco

- `compress_tool_output()` before tool messages appended
- Never-worse: if compression grows payload, keep original

## Repack + cache

Repack no longer rewrites the stable system block — only the user residual + volatile reminder. Prefix through repack stays stable; suffix shrinks.

## Verify on home

```powershell
mag.cmd agent --provider deepseek -q "status"
# Inspect logs/provider_usage.jsonl for cache_read_tokens > 0 on turn 2+
```

## Still open

- Dashboard UI for cache hit ratio
- Cache-aware repack threshold (don't repack if hit ratio high)
- Port additional ClawCodex `/eco` filters as we see real tool traces
