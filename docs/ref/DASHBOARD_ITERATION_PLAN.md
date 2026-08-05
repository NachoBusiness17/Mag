# Dashboard iteration plan — v2 base for v3

**Commitment:** `dashboard-iteration-plan-001`  
**As-of:** 2026-08-05  
**Parents:** `DASHBOARD_DESIGN.md` · `HOW_TO_MAG_DASHBOARD.md` · `LAYMAN_OFFICE_VISION.md` · `strike_origin.md`  
**Job:** Simplify Office to what **works**, fix bugs, complete v2 cleanup — **foundation v3 builds on**.

---

## 0. Purpose (from v1 inspiration)

v1 gave **activation grammar** (strike, sovereign mirror, witness posts). v2 gave **cold vertex** (residual + tip + pack). The dashboard must be a **viewport**, not a second DNA store.

| v1 leaf | Dashboard expression |
|---------|---------------------|
| Strike the chord | LOAD pack + one job — Chat with context, not scroll |
| Sovereign mirror | Office **Been · Now · Going** from residual `session_card` + `chord` |
| Witness spine (`spine_posts.json`) | Story tab — public activation, disk tip is truth |
| History Recorder → residual | Days tab — bead list + residual path on every card |
| Marble OS / 7 tools | Demote expert panels; one router behind Chat |
| FIND · FILE · LOAD | Office CTAs + provenance paths visible |

**Law:** Summary first, files second, spectacle never last (`DASHBOARD_DESIGN.md`).

---

## 1. What works today (keep and harden)

| Surface | API | Data source |
|---------|-----|-------------|
| **Office** | `GET /api/v1/home` | tip, latest_bead, bonds, ship, verify, launch_pad |
| **Days** | `GET /api/v1/overview` | `registry.jsonl` + residual |
| **Ideas** | `GET /api/v1/ideas` | `idea_graph` nodes |
| **Chat** | `POST /api/v1/agent/stream` | context-pack + agent_cli |
| **Body** | `router-status`, `governance`, `seats` | nervous_system shape |
| **Pulse** | `GET /api/v1/chronicle` | attention, seat feed |
| **Story** | `GET /api/v1/story` | filed narrative + witness |
| **Workers** | `/static/agents.html` | orchestrator fleet |

These map to **COLD + VIEWPORT** — the v3 base.

---

## 2. What's broken or misleading (fix list)

### P0 — operator trust (this branch)

| Bug | Fix |
|-----|-----|
| UTF-8 mojibake in buried panels (`â€"`, `Ã—`) | Correct em-dash / symbols in `index.html` |
| Workers tab button calls `setTab("agents")` — no such panel | Open `/static/agents.html` |
| Autorun status exists (`mag/autorun_status.py`) but not on Office | Wire into `/api/v1/home` + Office card |
| 11 dock tabs vs design spec (5) | **Core 5** visible; **More** expands depth tabs |
| Phoenix shown when ship OK | Already gated — verify after home API fix |

### P1 — reachability

| Issue | Fix |
|-------|-----|
| Blast, Lattice panels orphaned (no nav) | Body → Lab instruments **or** remove dead HTML |
| Grove API unused | v3 widget — defer; document in plan |
| `GET /api/catch-up` deprecated | Chat uses POST; remove GET alias or redirect |
| Lattice lab hard-coded Windows path | Guard + honest error on Linux |

### P2 — v2 graduation (needs PR #8–#10 on main)

| Gap | Subsystem |
|-----|-----------|
| Autorun card copy (Working / Paused / Last cycle) | Phase 1 `MAG_v2_PLAN` |
| Tier refuse visible in Status | Phase 2 |
| `GET /api/v1/autorun` dedicated endpoint | REST completeness |

---

## 3. Target IA (tesuji-002 — v3 builds here)

```text
Status strip: ship · health · refresh · catch-up (when needed)

Dock CORE (always):
  Office · Days · Ideas · Chat · Status

Dock MORE (one click):
  Diary · Story · Pulse · Canvas

External (links):
  Workers · Shell
```

**Demoted forever (expert only):** Board, Brief, Flow, Models, Blast, Lattice, Ingest — Body → Lab instruments.

---

## 4. Office panel contract (v3 base)

Every load of `/api/v1/home` must answer in 30 seconds:

1. **Am I OK?** — `ship.status`, `health`, phoenix only if not OK  
2. **What did I do?** — `latest_bead` + `provenance.residual_rel`  
3. **What's open?** — `trajectory`, bonds, working_open  
4. **Is Mag working away?** — `autorun` card (drainer, last tick, queue n)  
5. **What next?** — primary_next + CTAs (Chat, Days, Copy pack)

**Been · Now · Going** = residual grammar from v1 chord, not invented UI copy.

---

## 5. Data structures the UI must respect

| Shape | Path | UI rule |
|-------|------|---------|
| `session_dossier.v4_chord_knot` | `memory/biography/residual/*.json` | Days card = `session_card` only until inspect |
| `mag_session_registry.v1` | `registry.jsonl` | List face |
| `verkle_tip.v1` | `verkle_tip.json` | Advanced panel only |
| `mag_context_pack.v1` | context-pack | Chat preflight; show path in Office |
| `spine_posts.v1` | `memory/improve/pins/spine_posts.json` | Story witness links |
| `nervous_system.v1` | `nervous_system.json` | Status body glance |
| `autorun_status.v1` | `mag/autorun_status.py` | Office autorun card |

**Never:** story hash as tip · chat scroll as memory · visualization without file path.

---

## 6. Execution runs (ordered)

### RUN D0 — Dashboard trust (this PR)

- [x] Plan doc (this file)
- [ ] UTF-8 fix in index.html
- [ ] Workers button fix
- [ ] Autorun on Office + home API
- [ ] Dock More toggle (core 5 + expand)
- [ ] Bump static cache query (`?v=`)

### RUN D1 — Office complete (after v2 merge #8–#10)

- [ ] Autorun card three states (Working / Paused / Idle)
- [ ] `GET /api/v1/autorun` endpoint
- [ ] Governance toggle wired to `POST /api/v1/governance`
- [ ] Acceptance: DASHBOARD_DESIGN checklist §73–77

### RUN D2 — Depth cleanup

- [ ] Remove or wire orphaned Blast/Lattice windows
- [ ] Story tab: spine_posts witness links from `spine_posts.json`
- [ ] Diary fallback removed (require `/api/v1/diary` on lab restart)
- [ ] Move server.py one-offs into rest.py

### RUN D3 — v3 layman (parallel research, not v2 blocker)

- [ ] `mag_dashboard_layout.v1` on disk (`LAYMAN_OFFICE_VISION.md`)
- [ ] Tesuji Grove widget (`GET /api/v1/grove` already exists)
- [ ] Layman mode toggle hides Verkle/lattice jargon

---

## 7. Verification

```powershell
.\mag.cmd lab
# Browser: http://127.0.0.1:8765/
# Office loads without "API failed"
# Autorun card shows drainer state
# More → Diary/Story visible
# Workers opens agents page

.\mag.cmd doctor
python scripts/routing_smoke.py
```

---

## 8. Relation to v2 cleanup + orchestration

| v2 item | Dashboard tie-in |
|---------|------------------|
| RUN A merge #8–#11 | Router honest → Status tab accurate |
| Phase 1 autorun card | RUN D1 |
| Phase 2 tier refuse | Status shows L0/L2 truth |
| Orchestrator fleet | Workers page (already separate) |

**v3 builds on:** Office answering 5 questions + Chat with pack + Days as bead browser. Everything else is depth.

---

## Related

| Doc | Role |
|-----|------|
| `DASHBOARD_DESIGN.md` | IA + acceptance |
| `HOW_TO_MAG_DASHBOARD.md` | Layman FIND/FILE/LOAD |
| `MAG_v2_PLAN.md` Phase 1 | Autorun card spec |
| `HANDOFF_MAG_AGENT_TODOS.md` | Merge gate |
| `MAG_NEXT_CODING_RUN.md` | RUN A before v3 volume |
