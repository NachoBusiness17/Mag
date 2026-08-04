# Hermes orientation — Mag

Written 2026-07-25. Real file (Hermes chat faked tools and did not write this).

## What Mag is

**local_sovereign_agent** — Mag Resource Harness: local Ollama first, Grok scarce, biographer + dispatch + improve loop.

- L0 clerk/worker on Ollama (`gemma:2b` / `gemma4`)
- improve: scout field → candidates → **field_brief** → human promote
- dispatch picks seat: local | remote | grok_tui | **hermes**
- product UI: `python main.py lab` → :8765

## Why it exists

Keep **context and identity local**. Spend small models on scut. Spend Grok only on hard judgment with a pack, not full chat. Stop token bleed and “always-on cloud brain.”

## How Hermes relates

| Seat | Role |
|------|------|
| Mag L0 | Router, brief, ask, improve scout/eval |
| **Hermes L2** | Optional long tool/skill loop — **pack + goal only** |
| Grok TUI L2 | Interactive sovereign — `[priority]` + context-pack |
| Human L3 | Promote, secrets, irreversible |

Hermes is **not** the router. Mag owns the brief. Hermes has its own SOUL/skills under `%LOCALAPPDATA%\hermes\`. Private residual never routes to Hermes.

Commands:

```text
python main.py dispatch "…" --seat hermes
python main.py hermes-status
```

## Hard limits on this machine (why it “won’t just do it”)

1. **Hermes needs ≥64k context.** `gemma:2b` is 8k → agent **refuses to start**.
2. **`gemma4` starts** (131k) but often **roleplays tools** instead of calling them — exit 0, no file.
3. Interactive Hermes with no cwd/SOUL asks path questions forever.
4. Fixed: Hermes model = `gemma4:latest` + `context_length: 131072`; SOUL has ROOT.

## Next concrete move (from field_brief)

1. Open HF memory-systems thread (ticket `c-0a6393520bfb`) **or** skim ollama/llama.cpp releases for harness-relevant notes — extract **one** practice into playbook, promote or reject.
2. Do **not** model-shop (`c-80aaf33a1ad7` etc.).
3. For agent file work that must land on disk: prefer Mag + this TUI until Hermes tool fidelity is proven (or rent a stronger OpenAI-compatible endpoint).

## Paths

- Root: `C:\Users\foste\Documents\projects\local_sovereign_agent`
- Field brief: `memory/improve/field_brief.md`
- Working: `memory/working.md`
- Seats: `memory/improve/SEATS.md`
