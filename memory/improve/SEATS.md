# Mag seat matrix — canonical (Phase α)

**Commitment:** `chord-local-first-token-bleed-001`  
**Rule:** Small local models = **janitors**. Grok TUI = **scarce judgment**. Hermes = **parked** (optional lab only).

| Job | Seat | Provider |
|-----|------|----------|
| Route, ask, status, synthesize field brief | **L0 janitor** | Ollama **`gemma:2b`** (clerk/router) |
| Short local write / multi-smoke worker | **L0 worker** | Ollama **`gemma4`** — load, run, prefer unload |
| Scout / improve ledger (no LLM or clerk only) | **L0** | Mag improve (local) |
| Public cheap draft | **L1** | OpenRouter / DeepSeek (keys + budget) |
| Hard code / architecture / promote gate | **L2-TUI** | **Grok TUI** — `[priority]` + context-pack only · **scarce** |
| Multi-file refactor in IDE | **L2-Cursor** | **Cursor IDE** — `launch_cursor_seat.cmd` + hooks → Verkle trail · REST bridge: `watch/cursor_bridge.py` → `POST /api/v1/agent` |
| Tool loop when Grok empty | **L2-agent-cli** | `mag.cmd agent --provider deepseek` — Mag tools + DeepSeek (or ollama) |
| Long autonomous agent (optional) | **L2-Hermes** | **Parked.** Explicit `via hermes` only; 8B+64k on 6GB VRAM is hybrid/slow |
| Big GPU capacity | **L1-cap** | Vast later — not identity |
| Secrets / irreversible | **L3** | Human |

## Janitor doctrine (cooked in)

1. **Useful:** classify, brief polish, field_brief, ask, improve scout/eval, status.  
2. **Not useful:** hour-long self-improve, multi-step Mag CLI under Hermes bash, replacing Grok.  
3. **One model hot** when possible — don’t leave gemma4-hermes + gemma:2b both loaded.  
4. **Grok stays** for hard inference; local keeps context cheap. Leaving Hermes cold does not break Mag.

## Invariants

1. Improve scout never uses paid remote (`remote_llm_for_scout: false`).
2. No auto `ollama pull` unless `max_auto_pull_gb` raised (default 0).
3. Model seat changes need human `promote` + manual `lanes.yaml`.
4. Grok TUI ≠ always-on. Mag L0 is always-on for routing + field improve.
5. Vast is capacity, not identity.
6. Hermes is **not** the router. Private/recall never routes to Hermes.
7. Hermes Mag CLI must use bash-safe paths (`./.venv/Scripts/python.exe`) if re-enabled — PowerShell `.\` paths break under Hermes bash.

## Commands

```text
python main.py lab
python main.py ask "what was I doing?"
python main.py bonds                   # residual bonds → memory/bonds_active.md
python main.py improve --once          # scout + eval + field brief
python main.py improve --synthesize
python main.py dispatch "…"            # default local janitor
python main.py context-pack            # bonds+brief before [priority] Grok
python main.py context-pack --refresh-bonds
python main.py dispatch "…" --seat hermes   # explicit only; expect weak agent
python main.py hermes-status
launch_cursor_seat.cmd                       # Cursor seat: preamble + :8765
python watch/cursor_bridge.py pack           # Cursor REST bridge: fetch context pack
python watch/cursor_bridge.py ask "goal"     # Cursor REST bridge: run Mag agent turn
queue_deepseek.cmd "goal"                    # orchestrator queue → DeepSeek drain
python main.py orchestrator drain --once     # run one queued DeepSeek task
mag.cmd agent --provider deepseek          # tool REPL when Grok tokens empty
mag.cmd agent -q "read memory/working.md" --provider deepseek
```

See also: `HABIT.md`, `configs/lanes.yaml`, `configs/providers.yaml`.
