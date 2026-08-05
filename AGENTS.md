# local_sovereign_agent — harness rules

**LLMs: load framework first → `docs/FRAMEWORK_LOAD.md`** (or repo root `LOAD.md`)

This project is the **Mag Resource Harness** (standalone product home): local Ollama **janitors** first (`gemma:2b` scut, `gemma4` short worker), **remote specialist scarce** for hard inference, Hermes **parked**, biographer + orchestrator.

**DNA:** residual + registry + leaf = filed workdays (`docs/DNA.md`). Lab is optional ops.  
**Zeitgeist:** beads (this repo) + forest (mycelial-republic) — `docs/ZEITGEIST.md`. No core-mirror throne.

## Load order (agents — do not skip)

| # | File | Why |
|---|------|-----|
| 1 | `docs/FRAMEWORK_LOAD.md` | Navigation, metaphors, use cases, commands |
| 2 | `docs/ref/MAG_PROJECT_PROPOSAL.md` | Where we are / going (alpha → v2 → v3) |
| 3 | `docs/ref/OPERATOR_CARD.md` | FIND · FILE · LOAD |
| 4 | `AGENTS.md` | This file — env + commands |
| 5 | `mag.cmd context-pack` | Min-token pack for your seat |

Then: `memory/briefs/latest.md` · `queue/todo.md` · `HANDOFF_MAG_AGENT_TODOS.md` if implementing.

## When a specialist seat is used

- Prefer `memory/briefs/latest.md`, `memory/live_from_grok.md`, `memory/attention.md`, `queue/todo.md`.
- L2 escalate needs `[priority]` / `[L2]` (see `configs/lanes.yaml`) unless force.
- Mag escalations may call the harness or `queue/handoff/*.json` with **brief attached**, not full chat.
- Do not claim R0; T0/T1 stay local.

## Python env (do not skip)

**Default shell `python` is often Hermes** (`…\hermes-agent\venv\…`) — no Mag deps → `No module named 'langgraph'`.

Always use **this repo's** interpreter:

```text
mag.cmd doctor                # preferred (no PS execution policy issues)
mag.cmd context-pack
.\.venv\Scripts\python.exe main.py <cmd>
```

Repair / create venv: `powershell -ExecutionPolicy Bypass -File .\scripts\ensure_venv.ps1`  
Agents: call `.venv\Scripts\python.exe` or `mag.cmd`, **never** bare `python` on PATH (Hermes).

## Commands

```text
mag.cmd lab                   # product UI :8765 (+ flags for watch/mag)
mag.cmd dashboard             # UI only
mag.cmd brief                 # L0 dossier → memory/briefs/
mag.cmd ask "…"               # biographer Q&A local
mag.cmd mag --once            # companion cycle
mag.cmd watch                 # tail specialist sessions
mag.cmd run "goal"            # single graph job
mag.cmd context-pack          # min-token pack for TUI (bonds+brief)
mag.cmd bonds                 # residual next-session edges
mag.cmd improve --once        # daily scout + eval → memory/improve/
mag.cmd improve --status
mag.cmd promote --apply c-…   # human gate for candidates
mag.cmd research-pack …       # public URL → local pack
python main.py autorun --once --dry   # plan drainer (no execute)
python main.py verkle-audit --dry
```

**Metaphors + use cases:** `docs/FRAMEWORK_LOAD.md` §1–§3  
**Seats / habit:** `memory/improve/SEATS.md` · `memory/improve/HABIT.md`  
**Daily task:** `scripts\register_improve_task.ps1` → MagImproveDaily 08:00  

## Constitution

See `CONSTITUTION.md` → mycelial-republic `docs/CONSTITUTION.md`.
