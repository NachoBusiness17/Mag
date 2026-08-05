# Mag — Framework load order (for humans and LLMs)

**Commitment:** `framework-load-001`  
**As-of:** 2026-08-05  
**Status:** Alpha — load this before acting on the repo  
**One job:** Tell any reader **what to read, in what order**, with **metaphors** and **examples**.

**Point any model here:** `docs/FRAMEWORK_LOAD.md`  
**Short pointer at repo root:** `LOAD.md`

---

## 0. Copy-paste activation (any LLM seat)

```text
LOAD Mag framework — read in order:
  1. docs/FRAMEWORK_LOAD.md (this file — navigation + metaphors)
  2. docs/ref/MAG_PROJECT_PROPOSAL.md (where we are / where we're going)
  3. docs/ref/OPERATOR_CARD.md (FIND · FILE · LOAD — daily doors)
  4. AGENTS.md (python env + commands — do not skip)

Then run: mag.cmd context-pack (or python main.py context-pack)
Then: ONE job from queue/todo.md or operator goal.

Law: residual on disk is truth; chat is heat. T0/T1 never remote.
FILE outcomes before session ends — not chat scroll.
```

---

## 1. The office metaphor (layman map)

Mag is a **private records office** on your computer — not a chat app.

| Mag piece | Metaphor | Layman use |
|-----------|----------|------------|
| **Office dashboard** (`:8765`) | Front window of the building | "Is everything OK? What happened yesterday?" |
| **Bead / residual** | Filed workday folder | "What did I actually do that day?" |
| **Pack** | Briefing envelope for a visitor | "Here's what matters — don't read my whole life" |
| **Queue / todo** | In-tray on the desk | "Do this next" |
| **Router** | Receptionist | Sends work to the right room (cheap local vs expensive specialist) |
| **Ollama / gemma** | Janitor | Sorts mail, summaries, routing — always on, cheap |
| **DeepSeek agent** | Skilled contractor | Code and tool loops when janitor can't |
| **Grok** | Expensive consultant | Hard judgment only — scarce |
| **Orchestrator** | Shift supervisor | Spawns workers; one crash doesn't kill the building |
| **Autorun / drainer** | Night shift | Fills in-tray and works while you're away (if enabled) |
| **Container** | Locked vault room | Agent hands stay inside; your whole house isn't exposed |
| **Improve loop** | Suggestion box + review | Scouts ideas; **you** approve changes (promote) |
| **FKB** | Mistake log + fix cards | "We failed this way before — try this remedy" |
| **Verkle / tip** | Seal on the filing chain | "The chain of records is intact" |
| **Constitution / tiers** | Building code | What must never leave the building (T0/T1) |

**You are not the building.** You are the **owner**. Models are **visitors** with a pack, not roommates with memory.

---

## 2. Load order (read these files in sequence)

### Tier 0 — Boot (5 min) — **do not skip**

| # | File | Function |
|---|------|----------|
| 0 | **`docs/FRAMEWORK_LOAD.md`** | This navigation map |
| 1 | **`docs/ref/MAG_PROJECT_PROPOSAL.md`** | Full proposal: alpha status, v2/v3 path |
| 2 | **`docs/ref/OPERATOR_CARD.md`** | FIND · FILE · LOAD daily doors |
| 3 | **`AGENTS.md`** | Python env law + command cheatsheet |
| 4 | **`docs/DNA.md`** | What "filed" means — residual constitution |

**After read:** `mag.cmd doctor` · `mag.cmd context-pack`

### Tier 1 — Operating (when doing work)

| # | File | When |
|---|------|------|
| 5 | `memory/briefs/latest.md` | Current dossier (L0) |
| 6 | `memory/attention.md` | What matters now |
| 7 | `queue/todo.md` | In-tray jobs |
| 8 | `memory/bonds_active.md` | Carry to next session |
| 9 | `memory/improve/SEATS.md` | Who does what (janitor vs consultant) |
| 10 | `HANDOFF_MAG_AGENT_TODOS.md` | Merge order, rituals, agent queue |

### Tier 2 — Role-specific (load if your job needs it)

| Role | Files |
|------|-------|
| **Implementer** | `docs/ref/MAG_v2_PLAN.md` · `configs/modules.yaml` |
| **Research / v3** | `docs/ref/MAG_v3_RESEARCH_PLAN.md` · `docs/ref/MAG_v3_BACKLOG.md` · **`docs/ref/MAG_v3_SWARM_VISION.md`** · **`docs/ref/MAG_SWITCHBOARD_VISION.md`** |
| **Multi-seat build** | `docs/ref/MAG_BUILD_PIPELINE.md` · `docs/ref/MAG_FACTORY_PILOT.md` · `docs/ref/BUILD-TEMPLATE.md` |
| **Mobile voice** | `docs/ref/MAG_MOBILE_VOICE_SPEC.md` |
| **Jones agent fleet** | `docs/ref/JONES_AGENT_FLEET_PACK.md` · `docs/ref/MAG_AGENT_ERROR_CATALOG.md` |
| **LLM onboarding (paste pack)** | **`docs/ref/MAG_LLM_FEED_PACK.md`** — GitHub links + system prompts |
| **Next coding run** | **`docs/ref/MAG_NEXT_CODING_RUN.md`** — subsystems map + RUN A–D order |
| **Behavioral compounding** | **`docs/ref/MAG_BEHAVIORAL_COMPOUNDING.md`** — how steps auto-emerge, surface, resurrect |
| **Ponytail / Caveman skills** | `docs/ref/PONYTAIL_CAVEMAN_SKILLS.md` · `python main.py skill-seat` |
| **v4 theory** | `docs/ref/MAG_v4_THEORY.md` |
| **Layman UI** | `docs/HOW_TO_MAG_DASHBOARD.md` · **`docs/ref/LAYMAN_OFFICE_VISION.md`** (Grove + custom layout v3) |
| **Container install** | `docs/CONTAINER.md` |
| **Agentic steals** | `docs/ref/AGENTIC_LANDSCAPE_2026.md` · **`docs/ref/MAG_STEAL_AUTOPILOT.md`** |
| **Strike / chord** | `docs/ref/strike_origin.md` · `docs/ref/MAG_Activation.md` |
| **Seat handoff** | `memory/handoff/ACTIVATION.md` |

### Tier 3 — Depth (only when referenced)

`docs/ref/memory_verkle_map.md` · `CONSTITUTION.md` · `docs/ref/DECISION_LAYERS.md` · `docs/ZEITGEIST.md`

**Do not load Tier 3 by default.** Pack-first means small surface, not entire repo in context.

---

## 3. Three doors (every use case starts here)

From `OPERATOR_CARD.md` — if you remember nothing else:

```text
FIND  →  get real material (posts, exports, files — as presented)
FILE  →  write durable record on disk (bead, trail, dig leaf)
LOAD  →  hand AI a small pack (context-pack), not chat history
```

### Use cases (layman)

| I want to… | Door | Example |
|------------|------|---------|
| See if Mag is healthy | LOAD | Open `http://127.0.0.1:8765/` · Office tab |
| Ask "what was I doing?" | LOAD | `mag.cmd ask "what was I doing?"` |
| Start Grok/DeepSeek with context | LOAD | `mag.cmd context-pack` → paste pack + one goal |
| Queue overnight work | FILE | Add line to `queue/todo.md` · `MAG_DRAINER=1` · `mag.cmd autorun` |
| Code in Cursor while Mag waits | LOAD | `MAG_OPERATOR_ACTIVE=1` · `launch_cursor_seat.cmd` |
| Research a public URL | FIND+FILE | `mag.cmd research-pack --ask "…" --url "…"` |
| Improve Mag itself (gated) | FILE | `mag.cmd improve --once` · human `promote --apply` |
| Check what failed before | LOAD | `python main.py fkb stats` |
| Audit history gaps | FIND | `python main.py verkle-audit --dry` |
| Run one agent job | LOAD | `mag.cmd run "goal"` or `orchestrator run "goal"` |

---

## 4. Command cheatsheet (copy-paste)

**Always use Mag python** — never bare `python` on PATH (often Hermes venv).

```powershell
# Windows home PC (preferred)
mag.cmd doctor
mag.cmd lab                          # Office http://127.0.0.1:8765/
mag.cmd context-pack                 # pack for any seat
mag.cmd ask "what was I doing?"
mag.cmd brief
mag.cmd bonds
mag.cmd improve --once
mag.cmd improve --status
python main.py autorun --once --dry  # plan overnight work (no execute)
python main.py route "goal"          # after PR #8 merge
python main.py verkle-audit --dry
python main.py ponytail-audit
```

```bash
# Linux / cloud dev
.venv/bin/python main.py doctor
.venv/bin/python main.py context-pack
.venv/bin/python main.py lab
```

---

## 5. Architecture (one diagram)

```text
┌─────────────────────────────────────────────┐
│  LAYMAN — Office :8765                      │
│  "Mag is working" / "Paused while I code"   │
├─────────────────────────────────────────────┤
│  LATTICE — router → seats → orchestrator    │
│            improve · FKB · trail · pack      │
├─────────────────────────────────────────────┤
│  FREEDOM — container · tiers · constitution │
│            your disk · forkable · no throne  │
└─────────────────────────────────────────────┘
```

**Gates (only reasons to stop autorun):**  
G1 law/tiers · G2 secrets · G3 irreversible=L3 human · G4 operator coding

---

## 6. Seats (who you talk to)

| Seat | Model | Metaphor | When |
|------|-------|----------|------|
| L0 janitor | Ollama gemma:2b | Reception + mail sort | ask, brief, route, improve scout |
| L0 worker | Ollama gemma4 | Short local write | quick drafts |
| L2 agent | DeepSeek | Contractor + tools | code loops, autorun heavy jobs |
| L2 TUI | Grok | Scarce consultant | `[priority]` architecture |
| L2 IDE | Cursor | Your hands on keyboard | `MAG_OPERATOR_ACTIVE=1` |
| L3 | Human | Owner signature | delete, publish, secrets |

**Token law:** janitor first · consultant scarce · never burn Grok on scut.

---

## 7. Self-improvement loops (nested — not separate apps)

```text
improve   scout → eval → promote (you say yes to config changes)
autorun   fill → route → execute (night shift)
FKB       fail → remedy → score (mistake memory)
verkle    audit → gaps → enqueue (history honesty)
```

v3 research (scaffold on branch): resonance · spider · conductor · grove — see `MAG_v3_SWARM_VISION.md` · `python main.py v3-status`

---

## 8. FILE block (end every session)

Ask the seat for this; paste into trail / dig / next pack:

```text
FILE for Mag residual:
- What turned (3 bullets)
- Open loops
- Paths touched
- One next move
- Commitment slug
```

Chat dies. Files persist.

---

## 9. What NOT to do (LLM anti-patterns)

| Don't | Do instead |
|-------|------------|
| Treat chat as memory | FILE to residual / trail |
| Load whole repo into context | `context-pack` only |
| Use bare `python` | `.venv\Scripts\python.exe` or `mag.cmd` |
| Claim R0 / train identity in v2 | improve + promote; v3 research |
| Send T0/T1 to remote APIs | Local only |
| Invent CLI flags | Read `main.py` or AGENTS.md |
| Second orchestrator / DNA store | One router, residual on disk |
| Pretend we're out of alpha | Read `MAG_PROJECT_PROPOSAL.md` §4 |

---

## 10. Document map (quick links)

| Need | File |
|------|------|
| **Start here** | `docs/FRAMEWORK_LOAD.md` |
| Full proposal | `docs/ref/MAG_PROJECT_PROPOSAL.md` |
| Daily operator | `docs/ref/OPERATOR_CARD.md` |
| Human how-to | `docs/HOW_TO_MAG_DASHBOARD.md` |
| Agent rules | `AGENTS.md` |
| v2 roadmap | `docs/ref/MAG_v2_PLAN.md` |
| v3 research | `docs/ref/MAG_v3_RESEARCH_PLAN.md` |
| v3 swarm vision | `docs/ref/MAG_v3_SWARM_VISION.md` |
| v3 ideas list | `docs/ref/MAG_v3_BACKLOG.md` |
| Ops queue | `HANDOFF_MAG_AGENT_TODOS.md` |
| Build factory | `docs/ref/MAG_BUILD_PIPELINE.md` · `docs/ref/MAG_FACTORY_PILOT.md` |
| v4 theory | `docs/ref/MAG_v4_THEORY.md` |
| Stateless seat paste | `memory/handoff/ACTIVATION.md` |
| Card on wall | `docs/ref/MAG_Card.md` |

---

## 11. Maturity label

**Alpha.** Constitution + loops exist. v2 on branches (#8–#11). Conductor/resonance/spider = v3 research.

When in doubt: **honest files over clever chat.**

---

*End framework load — update when navigation or major phases change.*
