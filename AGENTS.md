# local_sovereign_agent — harness rules

**LLMs: load framework first → `docs/FRAMEWORK_LOAD.md`** (or repo root `LOAD.md`) · then **`docs/ref/MAG_MYCELIAL_REPUBLIC_COMPASS.md`** (compass)

This project is the **Mag Resource Harness** (standalone product home): local Ollama **janitors** first (`gemma:2b` scut, `gemma4` short worker), **remote specialist scarce** for hard inference, Hermes **parked**, biographer + orchestrator.

**DNA:** residual + registry + leaf = filed workdays (`docs/DNA.md`). Lab is optional ops.  
**Zeitgeist:** beads (this repo) + forest (mycelial-republic) — `docs/ZEITGEIST.md`. No core-mirror throne.

## Load order (agents — do not skip)

| # | File | Why |
|---|------|-----|
| 1 | `docs/FRAMEWORK_LOAD.md` | Navigation, metaphors, use cases, commands |
| 2 | **`docs/ref/MAG_MYCELIAL_REPUBLIC_COMPASS.md`** | **Compass** — vision, agent loop, v1–v10 arc, sovereignty |
| 3 | **`docs/ref/MYCELIAL_SCIENCE_MAP.md`** | **Biology ↔ protocol** — mycelial science map |
| 4 | `docs/ref/MAG_DIRECTION_ARTIFACT_v2.md` | Phase gates, v3–v5 mold |
| 5 | `docs/ref/MAG_PROJECT_PROPOSAL.md` | Problem depth |
| 6 | `docs/ref/OPERATOR_CARD.md` | FIND · FILE · LOAD |
| 7 | `AGENTS.md` | This file — env + commands |
| 8 | `mag.cmd context-pack` | Min-token pack for your seat |

Machine arc: `configs/version_roadmap.yaml` · Version index: `docs/ref/releases/VERSION_REGISTRY.md`

Then: `memory/briefs/latest.md` · `queue/todo.md` · `HANDOFF_MAG_AGENT_TODOS.md` if implementing.

## When a specialist seat is used

- Prefer `memory/briefs/latest.md`, `memory/live_from_grok.md`, `memory/attention.md`, `queue/todo.md`.
- L2 escalate needs `[priority]` / `[L2]` (see `configs/lanes.yaml`) unless force.
- Mag escalations may call the harness or `queue/handoff/*.json` with **brief attached**, not full chat.
- Do not claim R0; T0/T1 stay local.

## Python env (do not skip)

**Default shell `python` is often Hermes** (`…\hermes-agent\venv\…`) — no Mag deps → `No module named 'langgraph'`.

**API keys (DeepSeek, etc.) go in repo-root `.env` only** — never commit, never `memory/`.  
Bootstrap: `powershell -File scripts\ensure_local_env.ps1` (Windows) or `bash scripts/ensure_local_env.sh`.

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

## Cloud / remote seat — steer Mag (do not bypass)

**You are L2-Cursor steering seat, not Mag HQ.** Home disk (`memory/`, `queue/`, Ollama, DeepSeek tool loop) lives on the operator's machine. Your job is to **route work there**, not pretend those agents do not exist.

### Every cloud or remote run — in order

1. **Probe HQ**
   ```bash
   python watch/cursor_bridge.py status
   ```
2. **If `reachable: true`** — you MUST steer home Mag before editing this GitHub clone:
   ```bash
   python watch/cursor_bridge.py steer "<operator goal>" --mode delegate --provider deepseek --seat cursor-cloud --pack
   ```
   - Tool-heavy / coding → `--mode delegate` (DeepSeek + Mag tools on home)
   - Fire-and-forget / autorun → `--mode queue` or `--mode handoff`
   - Classify + route → `--mode dispatch`
3. **If `reachable: false`** — say so explicitly. Enqueue for home (`handoff` when URL returns), or minimal clone-only PR. Never silently substitute your own loop for Mag's.

### Required Cursor Cloud secrets (operator sets once)

| Secret | Example |
|--------|---------|
| `MAG_PUBLIC_URL` | `http://100.x.x.x:8765` (Tailscale / LAN home IP) |
| `MAG_REMOTE_TOKEN` | same as home `MAG_REMOTE_TOKEN` |

See `memory/handoff/CLOUD_STEERING.md` and `configs/cloud_steering.env.example`.

### Seat matrix (use as designed)

| Work | Seat | How from cloud |
|------|------|----------------|
| Context / bonds / brief | L0 janitor | `pack` via bridge |
| Tool loop + edits on home repo | L2-agent-cli | `steer --mode delegate --provider deepseek` |
| Background autorun | Governor + drainer | `steer --mode handoff` or `queue` |
| Multi-file IDE on clone | L2-Cursor | only when HQ unreachable or operator asks for GitHub PR |

**Law:** FILE outcomes to disk on home. Chat is heat. DeepSeek and local Mag agents are the execution layer — you steer them.
