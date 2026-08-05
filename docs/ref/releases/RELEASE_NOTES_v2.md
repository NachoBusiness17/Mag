# Mag v2 — Release notes

**Commitment:** `mag-release-v2-001`  
**Version:** 2.0.0-plan → 2.x graduation  
**As-of:** 2026-08-05  
**Status:** **Partial** — code on branches **#8–#11**; home `main` merge gate not closed  
**Registry:** `configs/releases.yaml` → `id: v2`

**Honesty:** v2 is **designed and branch-shipped**; v2 **graduation** = RUN A ritual green on home PC. Do not call v2 product-complete until Phase 0 acceptance passes.

---

## Card

**Title:** Mag v2 — freedom lattice  
**Blurb:** Self-improving agent lattice: layman Office door, silent router, forkable beads. Lessig modalities + ponytail/caveman discipline.

**One line:** *Write one line in todo → AFK → morning card tells truth → merge green on home PC.*

---

## Shipped (on branches — merge to `main`)

| PR | Delivers | Module |
|----|----------|--------|
| **#8** | Unified `route.v2`, `main.py route/decide`, loop escalation | `mag/router.py` |
| **#9** | Failure KB, remedy cards, behavioral wiring | `mag/failure_kb.py` |
| **#10** | Governor autorun, operator pause, FKB in scoring | `mag/governor_autorun.py` |
| **#11** | v2 plan, verkle-audit, agentic landscape map | `mag/verkle_audit.py` |

**Also filed (docs + surface):**
- `MAG_v2_PLAN.md` — phases + acceptance
- `MAG_OS_v2.md` — governance card, Phoenix triggers
- `docs/ref/lessig_1_6.md` — law/norm/market/architecture
- Ponytail + caveman audit CLIs
- `routing_smoke.py` — seat matrix smoke

---

## In progress (v2 exit criteria — not done)

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 0 | Merge #8→#10 on `main` | **Gate** — operator home PC |
| 1 | Autorun card on dashboard (`GET /api/v1/autorun`) | UI partial |
| 2 | Single route path all entry points | #8 merges |
| 2 | Tier refuse integration tests | planned |
| 3 | improve daily + verkle weekly scheduled | ops doc |
| 5 | Fork README — second clone path | open |

---

## Behavioral lessons filed (v2 → v3)

| Episode | Lesson | Carried to |
|---------|--------|------------|
| Same goal spawned 8× | Dedupe + orphan reap | orchestrator, switchboard |
| Plan theater 100+× | Loop-audit + fingerprint | v4 eval cases |
| Fragmented routers | route.v2 everywhere | RUN A |
| "Alpha pretend" | Honest labels | direction artifact v2 |
| Agent env confusion | FRAMEWORK_LOAD order | AGENTS.md law |

---

## v2 graduation gate (record with behavioral memory)

```powershell
mag.cmd doctor
.\.venv\Scripts\python.exe scripts\routing_smoke.py
python main.py verkle-audit --dry
python main.py autorun --once --dry
python main.py release record --version v2 --gate run_a --ok --note "home PC ritual green"
```

Gate id: `run_a` · See `configs/releases.yaml` → `v2.gates`

---

## Verify after merge

```powershell
python main.py route "test goal" --dry
python main.py autorun --once --dry
pytest tests/test_router.py tests/test_failure_kb.py tests/test_autorun_v1.py -q
```

---

## Artifacts for v3/v4/v5

| Doc | Role |
|-----|------|
| `docs/ref/MAG_DIRECTION_ARTIFACT_v2.md` | Direction after v2 |
| `docs/ref/MAG_NEXT_CODING_RUN.md` | RUN A–D order |
| `HANDOFF_MAG_AGENT_TODOS.md` | Merge order |
| `docs/ref/MAG_BEHAVIORAL_COMPOUNDING.md` | Episode → habit |

---

*Parent: `docs/ref/releases/VERSION_REGISTRY.md`*
