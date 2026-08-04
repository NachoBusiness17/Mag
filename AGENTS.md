# local_sovereign_agent — harness rules

This project is the **Mag Resource Harness** (standalone product home): local Ollama **janitors** first (`gemma:2b` scut, `gemma4` short worker), **remote specialist scarce** for hard inference, Hermes **parked**, biographer + orchestrator.

**DNA:** residual + registry + leaf = filed workdays (`docs/DNA.md`). Lab is optional ops.  
**Zeitgeist:** beads (this repo) + forest (mycelial-republic) — `docs/ZEITGEIST.md`. No core-mirror throne.

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
```

**Seats / habit (token bleed):** `memory/improve/SEATS.md` · `memory/improve/HABIT.md`  
**Daily task:** `scripts\register_improve_task.ps1` → MagImproveDaily 08:00  


## Constitution

See `CONSTITUTION.md` → mycelial-republic `docs/CONSTITUTION.md`.

## Cursor Cloud specific instructions

This VM is **Linux**, so the Windows helpers in this file (`mag.cmd`, `mag.ps1`, `.venv\Scripts\python.exe`, `scripts\ensure_venv.ps1`) do **not** apply. Use the repo venv interpreter directly: `.venv/bin/python main.py <cmd>` (equivalent to `mag.cmd <cmd>`). Dependencies (`requirements.txt`) are installed into `.venv` by the startup update script.

- **Run the product (dashboard + REST):** `.venv/bin/python main.py lab` → http://127.0.0.1:8765/ (integral = watch + companion + dashboard). Do not also run `watch`/`mag`/`dashboard` separately.
- **Tool/Agent loop needs a second service:** `lab` does **not** start the FastAPI tool backend. Run it separately: `.venv/bin/python -m backend.server` → http://127.0.0.1:8000/ (`/health`, `/run_task`). Without it, the dashboard Chat/Agent tool calls and `tests/test_repack_integration.py` fail with `backend not reachable at http://127.0.0.1:8000`.
- **Ollama (L0) is not available here.** Health/`doctor` will show `L0_ollama` not OK and `multi-smoke` will fail — expected. Anything needing local models (`brief`, `ask`, `run`, `dispatch`, `multi-smoke`) will not work without an Ollama server + `gemma:2b`/`gemma4:latest`. File-backed features work fully without it: ideas/topic board (`/api/v1/ideas`), sessions/registry, REST reads, and the tool backend (`write_file`/`read_file`/etc.).
- **Tests:** `.venv/bin/python -m pytest`. Two known-flaky soak tests — `tests/test_supervision_soak.py::test_kill_child_parent_survives` and `::test_gpipes_pipe_status_kill_list` — can fail in this sandbox: a killed child stays a zombie until the monitor thread reaps it on its ~5s `proc.poll()` cycle, which races the test's 5s `_wait_dead` bound. Not a code/setup defect. Run the full suite with `backend.server` up so the repack tests pass.
- **venv system dep:** creating `.venv` requires the `python3.12-venv` (ensurepip) apt package.
