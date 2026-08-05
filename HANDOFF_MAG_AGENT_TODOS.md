# Handoff — Mag Agent TODOs (master queue)

**Commitment:** `handoff-mag-agent-todos-001`  
**As-of:** 2026-08-05  
**Job:** Single operational handoff for agents, autorun, and human operator — merges roadmap, open PRs, Verkle audit, agentic steals, and abandoned work.

**Activation:** `python main.py verkle-audit --full` · `docs/ref/MAG_v2_PLAN.md` · this file.

> **Note:** Referenced as `\workspace\HANDOFF_MAG_AGENT_TODOS.md` on Windows home PC — same file at repo root.

---

## 0. North star (one paragraph)

Mag is a **freedom lattice**: layman Office at the front, intelligent router/autorun/FKB behind it, residual on disk. v2 ships when merge #8–#11 land, autorun card speaks human, Verkle history is audited weekly, and agentic industry patterns are **stolen as contracts** (persistence, guardrails, evaluator, compaction) — never as a second orchestrator or weight train.

---

## 1. Merge order (do first)

| Order | PR | Branch | Blocks |
|-------|-----|--------|--------|
| 1 | **#8** | `cursor/unified-router-e2ce` | Honest seat matrix |
| 2 | **#9** | `cursor/failure-kb-e2ce` | Loop → remedy |
| 3 | **#10** | `cursor/mag-autorun-v1-e2ce` | Intelligent drainer |
| 4 | **#11** | `cursor/mag-v2-plan-e2ce` | Plan + verkle-audit + agentic map |

**After merge on home PC:**

```powershell
mag.cmd doctor
.\.venv\Scripts\python.exe scripts\routing_smoke.py
python main.py verkle-audit --dry
python main.py autorun --once --dry
```

---

## 2. Verkle history — full analysis (cued)

### What exists now

| Layer | Command | Time (6 leaves) |
|-------|---------|-----------------|
| Deterministic audit | `python main.py verkle-audit` | <1s |
| Lattice store | `python main.py lattice-backfill` | <1s |
| Ticket reconcile | `python main.py verkle-audit` (built-in) | <1s |
| Full pass + synth | `python main.py verkle-audit --full` | **15–25 min** home PC (gemma4) |
| Query | `python main.py lattice-query --summary` | <1s |

### Scheduled automation (register on home PC)

| Task | When | Command |
|------|------|---------|
| **MagImproveDaily** | Mon–Fri 08:00 | `mag.cmd improve --once` |
| **MagVerkleWeekly** | Sat 09:00 | `python main.py verkle-audit --full` |
| **MagAutorun** | AFK | `MAG_DRAINER=1` + `python main.py autorun` |

Saturday = `catchup` rotation in `configs/improve.yaml` — reopens failed candidates + full Verkle audit.

### Autorun integration

`governor_autorun.fill_queue` now enqueues `[verkle]` goals from `verkle_gaps()` (warn/error severity).

Outputs:

- `memory/improve/daily/{date}-verkle-audit.json`
- `memory/improve/daily/{date}-verkle.md` (with `--full` / `--synth`)

---

## 3. Agentic landscape — what to implement (2025–2026)

**Deep dive:** `docs/ref/AGENTIC_LANDSCAPE_2026.md`

### Steal list (priority order)

| # | Industry pattern | Source | Mag v2 implementation | Status |
|---|------------------|--------|----------------------|--------|
| A1 | **Durable state / resume** | OpenAI Agents SDK sessions, Google ADK | residual + trail + `run_trail` (already); add **resume contract test** | partial |
| A2 | **Sandbox / container cage** | OpenAI sandbox agents | `CONTAINER.md` + docker compose | done |
| A3 | **Guardrails parallel to execution** | OpenAI guardrails | G1–G4 gates + tier refuse + FKB block | partial (#8–#10) |
| A4 | **Handoffs / agents-as-tools** | OpenAI handoffs | `route.v2` + cursor_bridge defer — **one router, not agent chat** | partial |
| A5 | **MCP tool surface** | Anthropic Agent SDK | Expose Mag REST as MCP for external seats (optional v2.1) | open |
| A6 | **Planner → worker → evaluator** | Anthropic long-running harness | `governor_autorun` fill/plan/execute + **pytest evaluator seat** | partial |
| A7 | **Context compaction** | OpenAI + Anthropic | `context-pack` + trail cores — **no full chat in pack** | done |
| A8 | **Structured artifacts between sessions** | Anthropic harness | residual JSON + knot leaf + `*-verkle.md` synth | **new: verkle-audit** |
| A9 | **Built-in tracing** | All SDKs | `governor_autorun_trail`, `behavioral_events`, FKB | done |
| A10 | **Subagent isolation** | OpenAI parallel sandboxes | orchestrator spawn + container — **not host roam** | done |
| A11 | **Human-in-loop on irreversible** | Agency shape | L3 gate + `operator_active` pause | done (#10) |
| A12 | **Eval / promote gate** | Mag improve | `promote --apply` — never auto lanes | done |

### Explicit non-steals

- Second orchestrator beside Mag
- Auto model weight pull (`max_auto_pull_gb: 0`)
- Agent-to-agent chat as coordination (use pack + trail — Elias rope)
- Grok/DeepSeek as default for scut

---

## 4. Open tickets (reconciled)

Run: `python main.py verkle-audit` → `reconcile` section.

### Roadmap (ORG_ROADMAP)

| ID | Title | Status | Next action |
|----|-------|--------|-------------|
| A1 | org-review / Operate | ✅ done | — |
| A2 | Hard private → remote refuse | 🟡 partial | Add integration test post-#8 merge |
| A3 | Seat matrix in dispatch | 🟡 partial | Mark done after #8; update `operator_os.py` |
| A4 | Context-pack freshness | 🟡 partial | #10 autorun refresh |
| B1 | Inter-day graph (0.95) | 🟡 partial | `lattice-backfill` + graph in dashboard (wired) |
| B2 | Evolution API + UI | 🟡 partial | Multi-day chart on dashboard |
| O3 | n_leaves ≥ 20 | 🔴 open | **use-time** — file sessions |
| 2.0 | verify-leaf | 🔴 open | Implement after 1.0 |

### Open PRs

| PR | Title | Agent action |
|----|-------|--------------|
| #8 | Unified router | Review + merge |
| #9 | Failure KB | Merge after #8 |
| #10 | Mag Autorun v1 | Merge after #9 |
| #11 | v2 plan + verkle-audit | Merge after #10 |

### Abandoned (do not resurrect without explicit operator ask)

| Item | Why |
|------|-----|
| `lattice-loop` + sovereign-mirror-scaffold | External dep not in container; instrument-only |
| `lattice-loop --backfill` dead handler | Remove or wire in cleanup PR |
| Hermes as default python | Parked per AGENTS.md |
| Full Verkle physics (KZG/PEPS) | Non-goal |

### Improve candidates

```bash
python main.py improve --once
python main.py improve --status
python main.py promote --apply c-<id>   # human gate
```

Ledger: `memory/improve/candidates.jsonl` (created on first scout).

### Queue

`queue/todo.md` — one line + `[mag]` tag. Autorun fill reads improve + agent_state + handoff + verkle gaps.

---

## 5. v2 phase checklist (from MAG_v2_PLAN)

| Phase | Focus | Key deliverable |
|-------|-------|-----------------|
| **0** | Single install | Merge #8–#11 |
| **1** | Layman Office | Autorun card + `GET /api/v1/autorun` |
| **2** | Lattice hardening | Tier refuse test; one route path |
| **3** | Self-improvement | Daily improve → autorun fill |
| **3.6** | **Verkle intelligence** | `verkle-audit` weekly + autorun gaps |
| **3.7** | **Agentic contracts** | A1–A12 steal list in AGENTIC_LANDSCAPE |
| **4** | Spore spine | `memory/improve/pins/spine_posts.json` |
| **5** | Fork / forest | Empty memory template |

---

## 6. Tests (trust ritual)

```bash
.venv/bin/python -m pytest tests/test_verkle_audit.py tests/test_ponytail_audit.py \
  tests/test_router.py tests/test_failure_kb.py tests/test_autorun_v1.py -q
.venv/bin/python scripts/routing_smoke.py
.venv/bin/python main.py verkle-audit --dry
.venv/bin/python main.py ponytail-audit
.venv/bin/python main.py fkb stats
```

---

## 7. Operator modes

| Mode | Env | Use |
|------|-----|-----|
| Coding | `MAG_OPERATOR_ACTIVE=1` | Cursor owns edits |
| AFK | `MAG_OPERATOR_ACTIVE=0`, `MAG_DRAINER=1` | autorun + verkle gaps fill |
| Audit | Saturday | `verkle-audit --full` |
| Deep research | Manual | `improve --deep --minutes 60` |

---

## 8. Files touched in this handoff tranche

| File | Role |
|------|------|
| `mag/verkle_audit.py` | Audit + reconcile + synth |
| `main.py verkle-audit` | CLI |
| `mag/governor_autorun.py` | Verkle gap fill |
| `mag/lattice_dashboard.py` | graph_viewport wired |
| `docs/ref/AGENTIC_LANDSCAPE_2026.md` | Industry deep dive |
| `docs/ref/MAG_v2_PLAN.md` | Phase 3.6–3.7 |
| `HANDOFF_MAG_AGENT_TODOS.md` | This file |

---

## 9. Seat transition (2026-08-05 — cloud agent ending)

**Reality:** Cursor cloud agent access ending. Grok meter resets ~1–2 days. **Forward stack: DeepSeek + Grok + local Ollama only.**

| Job | Seat | Not |
|-----|------|-----|
| Scut, ask, brief, improve scout, routing | **L0 Ollama** (`gemma:2b`) | Grok |
| Tool loop, multi-file code, `[mag]` autorun | **DeepSeek** (`agent --provider deepseek`) | Grok |
| Architecture, promote, `[priority]` judgment | **Grok TUI** + pack | Default drain |
| IDE edits while you code | **Cursor local** + `MAG_OPERATOR_ACTIVE=1` | Autorun |
| This cloud agent | **Done** | Do not depend |

**Before meter / access loss — freeze on disk:**

```powershell
mag.cmd context-pack
mag.cmd agent-state --load
python main.py verkle-audit --dry
python main.py ponytail-audit
# Merge #8→#11 when green; pull main on home PC
```

**Activate any remote seat (stateless):**

```text
1. python main.py context-pack
2. Paste memory/handoff/ACTIVATION.md + pack (not full chat)
3. One job per session
4. FILE → residual / trail / queue — chat dies
```

**Token law:** Grok = scarce judgment only. DeepSeek = heavy code + autorun. Ollama = everything else. Never re-litigate v2 plan in Grok — point at `HANDOFF_MAG_AGENT_TODOS.md` + `MAG_v2_PLAN.md`.

---

*End handoff — update after each merge and weekly verkle-audit.*
