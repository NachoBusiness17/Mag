# Mag Operator Map

**Canonical “how it works” for Nacho.**  
When docs disagree, this file + disk artifacts win.

Commitment: `operator-map-001` · Updated with governor/autorun dashboard (2026-08)

---

## 1. One picture

```
┌─────────────────────────────────────────────────────────────┐
│  DISK = the program                                         │
│  queue/todo.md · agent_state · improve · handoff/*.json     │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  GOVERNOR = brain (mag/governor.py + mag/governor_autorun) │
│  fill queue → plan → score → execute → verify → trail       │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  ROUTING = nervous system (mag/coordination.py + providers)  │
│  depth → provider → dispatch | delegate | orchestrator      │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  WORKERS = hands (ollama · DeepSeek · vast · orchestrator)  │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  DASHBOARD :8765 = window (routes · quota · autorun card)   │
│  shared_activity.jsonl = who did what (visibility)            │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Two loops (do not confuse them)

| Loop | What starts it | Interval | Purpose |
|------|----------------|----------|---------|
| **Companion** | `mag lab` always | ~120s | Legacy `sense → judge → act` on policy/todo |
| **Governor autorun** | `MAG_DRAINER=1` or dashboard drainer toggle | ~5s | Fill → plan → route → execute framework |

**Dashboard:** Body tab → **Governor & autorun** card shows which is ON.

| Pill | Meaning |
|------|---------|
| `GOVERNOR AUTORUN: ON` | Drainer enabled + autorun thread or supervisor drainer running |
| `GOVERNOR: enabled but not running` | Pref on, no process — start `mag lab` or `mag autorun` |
| `GOVERNOR AUTORUN: OFF` | Set `MAG_DRAINER=1` or toggle Auto-drain |

---

## 3. Work enters the system

| Source | Path | Who picks it up |
|--------|------|-----------------|
| Operator todo | `queue/todo.md` lines `- [ ] [mag] …` | Governor `run_cycle` |
| Agent state | `memory/agent_state/LATEST.json` `next_moves` | Autorun `fill_queue` + governor |
| Improve scout | `memory/improve/` candidates | Autorun `fill_queue` |
| Cloud/handoff | `queue/handoff/*.json` | Autorun `fill_queue` |
| Dashboard | Chat, `POST /api/v1/orchestrator/queue` | Orchestrator queue |
| You typing | Interactive agent window | Manual seat (not governor) |

---

## 4. Routing (depth → provider → action)

Classifier: `mag/coordination.py` → `classify_depth(goal)`

| Depth | Example | Seat | Auto-execute? |
|-------|---------|------|---------------|
| `scut` | doctor, status, brief | ollama | Yes — dispatch |
| `simple_code` | small fix, one file | ollama | Yes — dispatch |
| `heavy_code` | implement, refactor | deepseek / vast | Yes — delegate or orchestrator queue |
| `plan` | architecture, roadmap | Grok TUI | No — files context pack |
| `overview` | ecosystem map | Grok TUI | No — files context pack |

Provider pick: `models/quota.py` → `pick_provider(job)` using `configs/providers.yaml` budgets.

Skills: `configs/skills.yaml` + IJL beads under `memory/improve/pins/skills/` — attached to context pack, not routing.

**Dashboard:** Governor card → **Depth routing** table.

---

## 5. Dashboard map (`http://127.0.0.1:8765`)

Open dock → **Body** (status tab).

| Section | What you see |
|---------|--------------|
| **Governor & autorun** | ON/OFF, last cycle, queue list, routing table |
| **Coordination** | Cross-seat activity feed (`state/shared_activity.jsonl`) |
| **Governance** | Drainer toggle, steer buttons |
| **Routes** | Provider keys + Mag budget % |
| **Workers (48h)** | Orchestrator sub-agents |
| **Ops overview** | Supervisor + fleet + queue counts |
| **Desks & drainer** | Mirror desk, Autopilot once |

Other tabs:

| Tab | Use |
|-----|-----|
| **Chat** | Talk to Mag; Agent/Talk modes; **breadcrumbs** dock (deferred steering) |
| **Workers** (`/static/agents.html`) | Spawn/kill/steer sub-agents |
| **Orchestrate** | Full quota table + probe |

Auto-refresh: Body tab reloads every **60s** when open.

---

## 5b. Steering: breadcrumbs vs emergency steer

Two channels — use breadcrumbs by default; reserve `!steer` for interrupts.

| Channel | When it lands | API / UI | Agent behavior |
|---------|---------------|----------|----------------|
| **Breadcrumb** | Next checkpoint (between tool rounds) | Chat tab → **Breadcrumbs** dock · `POST /api/v1/operator-inbox` | Incorporate into current search/plan — do not restart |
| **Refine breadcrumb** | Same checkpoint + orchestrator queue | Checkbox **Refine agent** on drop | Spawns `breadcrumb-refine` sub-agent to develop the idea |
| **Path drop** | Same | `@memory/path.md` or `file:path` in breadcrumb box | Expands file excerpt into the crumb (≤1200 chars) |
| **Emergency steer** | Immediately (mid-round) | Body → Governance · `POST /api/v1/governance` `{cmd: "!pause"}` | Pigeonhole — breaks stride on purpose |

**Disk:** `memory/operator_inbox.json` (pending crumbs) · drained by `mag.agent_cli` at checkpoint via `operator_inbox.drain_pending_at_checkpoint`.

**Layman:** Drop a note while the agent is working — it picks it up at the next breath, not mid-tool. Check **Refine agent** if you want a background worker to riff the idea.

---

## 6. CLI quick reference

```text
mag.cmd lab                    # dashboard + companion + autorun if MAG_DRAINER=1
mag.cmd autorun                # continuous governor loop
mag.cmd autorun --once --dry   # plan only (no execute)
mag.cmd autorun --once         # one fill/plan/execute tick
mag.cmd governor --run 3       # governor only (no fill)
mag.cmd autopilot              # improve queue + one governor cycle
mag.cmd coordinate "goal"      # classify + launch worker
mag.cmd dispatch "goal"        # route to cheapest seat
mag.cmd orchestrator queue add "goal"
```

---

## 7. Truth files (when UI lies, read disk)

| File | Contents |
|------|----------|
| `memory/runs/governor_trail.jsonl` | Governor decide/execute audit |
| `memory/runs/governor_autorun_trail.jsonl` | Autorun fill/plan/drain ticks |
| `state/shared_activity.jsonl` | Cross-seat visibility |
| `memory/runs/orchestrator/queue/*.json` | Queued goals |
| `logs/quota_state.json` | Provider usage vs yaml budgets |
| `watch/heartbeat.json` | Lab alive + `autorun_on` flag |

---

## 8. Daily desk (recommended)

```powershell
# .env
MAG_DRAINER=1
DEEPSEEK_API_KEY=sk-...

launch_desk.cmd
# → backend :8000 · mag lab :8765 · autorun · DeepSeek agent window
```

Check dashboard Body → Governor card shows **ON**.  
Add work: `- [ ] [mag] your task` in `queue/todo.md`.

---

## 9. Related docs

- [`docs/HOW_TO_MAG_DASHBOARD.md`](HOW_TO_MAG_DASHBOARD.md) — layman dashboard guide  
- [`docs/DNA.md`](DNA.md) — residual / beads / FIND-FILE-LOAD  
- [`docs/ref/PRODUCT_VISION_AUTORUN.md`](ref/PRODUCT_VISION_AUTORUN.md) — governor product statement  
- [`AGENTS.md`](../AGENTS.md) — harness rules for agents  
