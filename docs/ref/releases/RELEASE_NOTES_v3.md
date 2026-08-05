# Mag v3 — Release notes (planning)

**Commitment:** `mag-release-v3-001`  
**Version:** 3.x — **what we are planning to build** on v2 substrate  
**As-of:** 2026-08-05  
**Status:** **Planned / in_progress** — not shipped; branches + run sheet only  
**Registry:** `configs/releases.yaml` → `id: v3`  
**Parent:** v2 (this repo)

**Honesty:** v3 is **agent + operator planning** — substrate (orchestrator, switchboard, pack modes, Chat, factory pilot). Do not call v3 shipped until gates in `releases.yaml` are recorded.

---

## Card

**Title:** Mag v3 — substrate build  
**Blurb:** Make the v2 repo **route, file, and speak** like a product: DeepSeek run, factory plan→build→audit, Cursor-like Chat, v3 modules merged to home `main`.

**One line:** *v3 = honest lattice + first agent interface that doesn't lie to the operator.*

---

## What v3 is (operator + planning definition)

| Not v3 | Is v3 |
|--------|-------|
| Grok origin (that's **v1**) | Orchestrator + switchboard + conductor wiring |
| The repo existing (that's **v2**) | Factory freeze gate, CHAT preflight |
| v4 mold (conductor eval) | Pack modes, steward-scope wave 1 |
| v5 forest seats | Merge #13/#15 patterns to main |

---

## Planned deliverables (from run sheet)

| Wave | Deliverable | Doc |
|------|-------------|-----|
| Gate | v2 merge ritual (prerequisite) | RUN A |
| B | Factory pilot `build_audit.v1` | `MAG_FACTORY_PILOT.md` |
| D | No `[build]` without frozen BUILD | RUN D |
| C | Training hooks, grove REST, DeepSeek run | PR #15 |
| Chat | CHAT-1–4 preflight + status | `V3_DEEPSEEK_RUN.md` §6 |
| Modules | conductor, spider, switchboard on main | `MAG_v3_BACKLOG.md` |

**Active branch:** `cursor/v3-deepseek-run-e2ce` (PR #15)

---

## v3 gates (record when true)

```powershell
python main.py release record --version v3 --gate deepseek_run --ok
python main.py release record --version v3 --gate factory_pilot --ok
python main.py release record --version v3 --gate chat_preflight --ok
```

See `configs/releases.yaml` → `v3.gates`

---

## Witness toward v3 (public)

Latest operator-linked arc:

- [2083551644239683672](https://x.com/NachoQuixotic/status/2083551644239683672?s=20) — toward v3 (ingest via `research-pack` for text)

Full spine: [WITNESS_SPINE.md](WITNESS_SPINE.md)

---

## Behavioral target (v3 → v4)

| v3 must FILE | So v4 can |
|--------------|-----------|
| Training events on spawn/terminal | Score route decisions |
| BUILD specs on disk | Conductor eval cases |
| Chat preflight honest | Seat economics visible |
| One factory audit JSON | Plan→build→audit chain proven |

---

## Not started (defer — v3 backlog only)

L-conductor train, resonance product, mobile voice, GSTD implement, XRPL tools — see `MAG_v3_BACKLOG.md`.

---

*Parent: [VERSION_REGISTRY.md](VERSION_REGISTRY.md) · Build on: [RELEASE_NOTES_v2.md](RELEASE_NOTES_v2.md)*
