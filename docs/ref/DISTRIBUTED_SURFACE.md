# Distributed surface — multi-device glue

**Commitment:** `distributed-surface-glue-001`  
**As-of:** 2026-08-04  
**Parents:** `SOVEREIGN_STACK.md` · `COORDINATION.md` · `DNA.md` · `CONTAINER.md`  
**Operator runbook:** `memory/handoff/HOME_MACHINE.md`  
**Config:** `configs/distributed_surface.yaml`

---

## Problem

Mag's boundary is **local disk** (`memory/`, `state/`, `queue/`). The product surface is **`:8765` REST + dashboard**.

Cursor Cloud / web tablet agents clone **GitHub only** — they do not see your soil, Ollama, or resume contract. That is the wrong seat for Mag HQ.

**Goal:** any device (phone, tablet, laptop, cloud decoder) can **viewport** your Mag office and **FILE** back — without making a cloud VM the boundary.

---

## Architecture (target)

```text
┌─────────────────────────────────────────────────────────────┐
│  HOME MACHINE (canonical boundary)                          │
│  memory/ · state/ · queue/ · Ollama                         │
│  python main.py lab  →  :8765  (/api/v1/*)                  │
└───────────────┬─────────────────────────────────────────────┘
                │  LAN / Tailscale / tunnel (G3)
    ┌───────────┼───────────┬──────────────┐
    ▼           ▼           ▼              ▼
  Tablet     Laptop      cursor_bridge   Cloud decoder
  browser    browser     MAG_URL=…       (scarce; FILE back)
```

| Layer | Rule |
|-------|------|
| **Boundary** | Home machine disk — never GitHub-only for residual |
| **Viewport** | Any client with HTTP to `:8765` |
| **Decoder** | Grok / DeepSeek / Cursor Cloud — stateless, pack-first |
| **Glue** | handoff ingest + coordination feed + optional soil sync |

**Not the goal:** Cursor Cloud VM as primary office. **Is the goal:** reach your real Mag from anywhere.

---

## Phases (ordered)

### G0 — Plan + runbook (this commit)

| Deliverable | Done when |
|-------------|-----------|
| This doc | committed |
| `configs/distributed_surface.yaml` | phase + paths declared |
| `memory/handoff/HOME_MACHINE.md` | operator can pull and follow |
| Links from README / SOVEREIGN_STACK | discoverable |

### G1 — FILE handoff ingest (shipped)

| Deliverable | Done when |
|-------------|-----------|
| `POST /api/v1/handoff/file` | accepts FILE block / goal text from any client |
| Writes `queue/todo.md` and/or `memory/working.md` | existing scheme — governor sees `[mag]` lines |
| `GET /api/v1/surface` | returns phase, bind hint, last inbound |
| `mag/distributed_surface.py` | single module for ingest + status |
| Tests | `tests/test_distributed_surface.py` green |

**Body example:**

```json
{
  "text": "FILE for Mag residual:\n- turned: …\n- open loops: …\n- next move: wire G2 auth",
  "source": "tablet",
  "device": "ipad-safari"
}
```

### G2 — Remote auth (safety before wide bind)

| Deliverable | Done when |
|-------------|-----------|
| `MAG_REMOTE_TOKEN` env | required on POST write routes when `MAG_BIND_HOST != 127.0.0.1` |
| `Authorization: Bearer …` | on handoff, coordination POST, agent, dispatch |
| Read routes | still OK on LAN without token (or configurable) |
| Test | POST without token → 401 when remote bind |

**Law:** never expose unauthenticated write endpoints on `0.0.0.0`.

### G3 — Reachability (operator network)

| Deliverable | Done when |
|-------------|-----------|
| `launch_dashboard_lan.cmd` | documented as dev/LAN path (exists) |
| `MAG_PUBLIC_URL` | echoed in `/api/v1/surface` for clients |
| Tailscale / Cloudflare tunnel | documented in HOME_MACHINE (operator choice) |
| `watch/cursor_bridge.py` | `MAG_URL=$MAG_PUBLIC_URL` works from remote Cursor |

**Default container:** stays `127.0.0.1` per `CONTAINER.md`. Remote reach = explicit operator opt-in.

### G4 — Soil sync (optional, second machine)

| Deliverable | Done when |
|-------------|-----------|
| `soil_paths` in config | `memory/`, `state/`, `queue/` listed |
| Syncthing / git-private / rsync doc | one recommended path in HOME_MACHINE |
| Conflict rule | **newest FILE wins** for handoff; residual = human merge |
| Not required for G1–G3 | home machine can be sole canonical |

---

## REST surface (target)

| Method | Path | Phase | Role |
|--------|------|-------|------|
| GET | `/api/v1/surface` | G1 | Plan phase, bind URL, inbound count |
| POST | `/api/v1/handoff/file` | G1 | Ingest FILE block from any device |
| GET | `/api/v1/coordination` | done | Shared activity feed |
| POST | `/api/v1/coordination` | done | Heartbeat from any seat |
| POST | `/api/v1/seat/task` | done | Unified tasking (cursor_bridge) |
| GET | `/api/v1/context-pack` | done | LOAD for cold seats |

Index: `GET /api/v1/` — add handoff + surface lines when G1 ships.

---

## Seat rules (unchanged)

1. **Cloud agents** (Cursor web, Slack `@Cursor`) = L2 code workers on **git** — not Mag HQ.
2. **Mag dashboard** from tablet = viewport on **home soil** — correct HQ.
3. **Handoff FILE** from tablet → `memory/handoff/inbound/` → next `context-pack` includes it.
4. **T0/T1** never leave home machine in remote suggestions (existing law).

---

## Acceptance (glue complete = G1–G3)

| ID | Check |
|----|--------|
| D1 | Tablet on same LAN opens `http://<home-ip>:8765/` and sees Office |
| D2 | Tablet POSTs FILE block → file appears in `memory/handoff/inbound/` |
| D3 | `context-pack` or org-review mentions last inbound handoff |
| D4 | Remote bind requires `MAG_REMOTE_TOKEN` on writes |
| D5 | `cursor_bridge.py pack` works with `MAG_URL` pointed at home |
| D6 | Cloud agent PR does not replace residual DNA on disk |

---

## Explicit non-goals

- Slack bot in Mag core (use Cursor Slack integration for cloud code only)
- GitHub as residual boundary
- Always-on public internet expose without auth
- Full real-time soil sync in v1 (G4 is optional)

---

## One line

**Home machine owns soil; every other device is a viewport or a decoder that FILES back — glue makes that reachable, not Cursor's VM.**
