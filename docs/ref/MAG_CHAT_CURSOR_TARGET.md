# Mag Chat — Cursor-like target (v3/v4)

**Commitment:** `mag-chat-cursor-target-001`  
**As-of:** 2026-08-05  
**Status:** Planning — operator direction  
**Parents:** `DASHBOARD_DESIGN.md` · `MAG_v3_SWARM_VISION.md` · `MAG_V4_CONDUCTOR_LOOP_DRAFT.md` · `LAYMAN_OFFICE_VISION.md`

**One breath:** Dashboard Chat should feel like **this Cursor window** — one conversation, streaming agent, workspace tools, steer while running — while Mag still **files outcomes to disk** and spider still **notices loops** without turning chat into memory or telemetry.

---

## 1. Honest diagnosis (why Chat feels useless today)

| Symptom | Root cause |
|---------|------------|
| Send → spin → error or garbage | **No seat preflight.** Agent hangs on missing `DEEPSEEK_API_KEY`; Ask falls back to heuristic paste when Ollama is down. UI does not say *why* before you wait. |
| Four modes + seat dropdown + steer + guidance queue | **Expert chrome on a consumer job.** Cursor has one compose box; Mag exposes Agent / Ask / Dispatch / Tangent plus three steer channels. |
| Chat history vanishes / feels fake | **`localStorage` only** (`mag_chat_v1`). Not filed; not join-keyed; not visible to spider or improve. |
| Board feels disconnected | **Board demoted** to Status → “Rare depth.” Kanban + live scraps exist but are not in the chat flow. |
| Spider “works” but you never see it | **Backend-only.** `spider.tick()` → trail + optional pigeonhole steer. No Office/Chat status line. Improve cycle runs spider with `inject=false`. |
| Proof-of-concept vibe | **Right architecture, wrong polish.** Streaming SSE, operator inbox, agent tools, pack injection — all wired — but failure modes and UX bury the happy path. |

Spider is a valid v3 proof: it notices stall, plan theater, operator_active. Chat is the **operator face** — it must work even when spider is silent.

---

## 2. Target: “This interface here” (Cursor) mapped to Mag

Cursor (what you like) | Mag equivalent (what we build)
---|---
Single chat thread, streaming | **One primary pane** — Agent mode default; Ask/Dispatch demoted to chips or `/ask` |
@ files / codebase context | **Pack chip** — “brief + N paths” from `context-pack`; attach file → upload → session |
Agent runs tools | **Already there** — `api_agent_turn` + SSE `/api/v1/agent/stream` |
Follow-up while agent runs | **Guidance queue** — keep, but *inside* compose (Cursor-style queued message), not a second textarea dock |
Sub-agents / background tasks | **Fleet strip** — link to `/static/agents.html` or inline drawer; spawn from chat |
Status / problems subtle | **Spider + loop health one-liner** under compose — not chat messages |
Outcomes persist | **File on done** — `/save` or auto-knot on terminal tool; chat scroll is heat, knot is DNA |
Plain “is it working?” | **Seat preflight bar** — green/yellow/red from `GET /api/v1/doctor` + selected seat |

**Mag law unchanged:** chat scroll ≠ memory. Cursor-like UX; residual/Verkle/ideas still own DNA.

---

## 3. Information architecture (v4 Chat)

```text
┌─────────────────────────────────────────────────────────────┐
│ Office (Home)          │  optional: Ideas / Days sidebar    │
├────────────────────────┴────────────────────────────────────┤
│ CHAT (primary when working)                                 │
│  [seat ●] [pack: brief+3]                    [fleet · 2]    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ message log (streamed)                               │   │
│  │  user · agent · [tool traces collapsed]              │   │
│  └─────────────────────────────────────────────────────┘    │
│  spider: OK · loop: clear · last leaf: knot-…                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ compose (Enter send · Shift+Enter newline)           │   │
│  │ + file · queued: 1 follow-up at checkpoint           │   │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

**Demote / hide by default:** economy bar, four mode pills, duplicate steer input, Board as separate maze.

**Board scraps:** live panel *beside* chat (collapsible), not buried under Status — brief, attention, todo, `live_from_grok` tail.

---

## 4. Spider’s role (keep — extend visibility)

| Layer | Job | UI surface |
|-------|-----|------------|
| Spider | Notice stall, autorun burst, plan theater, operator_active | **Status strip** + Office one-liner (v4) |
| Loop-audit | Mine trail for waste patterns | Body / Improve; feeds training_patterns |
| Operator inbox | Human breadcrumbs at checkpoint | **Compose queue badge** |
| Governance `!steer` | Immediate mid-turn | **Single** steer affordance (not three) |

v4 rule stands: **loop-audit + spider for observability**, not chat-as-telemetry. Spider signals appear as **one line of status**, not fifty bot messages.

Open wiring (from `MAG_NEXT_CODING_RUN` C5): spider → switchboard `steer_drop` tier, not raw `post_steer`.

---

## 5. Build order (RUN rows — v4-first)

| # | RUN | Seat | Outcome |
|---|-----|------|---------|
| C1 | **Seat preflight** — before send, `GET /api/v1/doctor` + seat key check; block with fix text | Cursor | No more 10-minute hangs |
| C2 | **Chat chrome collapse** — default Agent; Ask/Dispatch/Tangent → overflow menu; merge steer into one control | Cursor | Cursor-like simplicity |
| C3 | **Pack visibility chip** — show brief hash + path count on compose; refresh on Reset | Cursor | “@ context” without jargon |
| C4 | **Spider status strip** — last tick summary + link to trail; poll every 30s | Cursor | PoC becomes visible |
| C5 | **Session file** — `memory/sessions/dashboard_chat.jsonl` append-only; join keys on terminal | Cursor | Chat useful to improve, not DNA |
| C6 | **Board beside chat** — collapsible scraps panel; same data as `board_pack()` | Cursor | Board useful again |
| C7 | **clear-ui as opt-in default** — `state/mag_preferences.json` → `chat_layout: cursor` | Cursor | Layman path from LAYMAN_OFFICE |
| C8 | **Auto-knot on agent done** — optional “file this turn” when tools wrote artifacts | DeepSeek | FIND→FILE from chat |

Pattern ids: `seat_unavailable`, `chat_session_filed`, `spider_status_surface`. Eval: send with no API key → error &lt;2s; send with key → stream &lt;5s to first delta.

---

## 6. Non-goals

- Chat scroll as cold DNA or training export
- Replacing Cursor cloud agent — Mag chat is **local office + own API keys**
- Spider spam in message log
- Auto-promote from chat transcripts
- Grok token burn for Ask (local biographer stays L0)

---

## 7. Acceptance (operator can demo in 2 minutes)

1. Open Chat → seat bar shows green or clear red fix (“set DEEPSEEK_API_KEY”).  
2. Send “list open items in queue/todo.md” → streams tools + answer.  
3. Queue follow-up while running → drains at checkpoint.  
4. Spider line updates when autorun stalls (or “OK” when quiet).  
5. Board scraps visible without digging Status.  
6. `/save` or done → knot or residual edge filed; path shown in reply.

---

## 8. One-line for external research

> Make Mag dashboard Chat behave like Cursor’s agent pane (stream, pack, tools, steer) while spider/loop-audit stay observability layers and filing stays on disk — fix preflight and collapse chrome before new features.

**Related:** `docs/ref/onepagers/05-wiring-gaps.md` · `docs/ref/RESEARCH_BRIEF_V3_V4.md` · `dashboard/static/index.clear-ui.html`
