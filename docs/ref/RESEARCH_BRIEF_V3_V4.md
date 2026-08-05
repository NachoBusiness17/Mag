# Mag v3 / v4 — research brief for external LLM

**Copy everything below the line into Grok, DeepSeek, Claude, etc.**  
**As-of:** 2026-08-05 · **Repo:** Mag Resource Harness (local sovereign agent orchestrator) · **Branch:** `cursor/v3-swarm-vision-e2ce` · PR #13

---

## Your role

You are a **research analyst**, not the implementer. Produce **cited, comparative research** and **actionable recommendations** that fit Mag’s constraints. Do not invent product features that violate the non-goals. Prefer **contracts stolen from industry** over generic “use AI better” advice.

---

## 1. What Mag is (one paragraph)

Mag is a **home-PC agent harness**: local Ollama janitors first, orchestrator queue + drain, Verkle/residual session DNA on disk, context-pack for frontier seats, human **promote gate** for config changes. The operator (Nacho) uses **Grok** for scarce planning, **Cursor** for multi-file hands, **DeepSeek API** for bulk build loops on his keys. Goal: **passive planner** that files episodes, routes cheaply, and learns without chat-as-memory or silent self-modification.

---

## 2. Critical reframe: v3 vs v4 (read this first)

**Do not treat v3 as “phase 1 to complete” and v4 as “phase 2 later.”**

| Label in repo | What it actually means | Research lens |
|---------------|------------------------|---------------|
| **v3** (historical naming) | **Platform substrate** — orchestrator, autorun, router, switchboard, seats, Office dashboard, Verkle filing, improve scout, FKB | “What runtime exists?” |
| **v4** (product direction) | **Process mold** — loop discipline, seat economics, steward jobs, training patterns, actor memory, promote ladder | “What rules govern growth?” |
| **v3 backlog** (`v3-NNN`) | **Research inbox** — ideas to score, not a build checklist | “What might become patterns?” |

**v4-first doctrine:** Spec + eval + patterns **before** substrate volume. New work must answer: (1) pattern id, (2) eval case, (3) join keys, (4) auto vs draft vs human promote.

**Recommended doc merge (planning):**
- `MAG_PLATFORM.md` ← substrate (was “finish v3”)
- `MAG_V4_PRODUCT.md` ← process (conductor, loops, economics, steward)
- `MAG_RESEARCH_INBOX.md` ← backlog only

---

## 3. What is already shipped (substrate — do not re-research from scratch)

- Unified **route.v2** (depth, provider, janitor-first)
- **Orchestrator** queue + drain + spawn isolation + dedupe
- **Governor autorun** fill → plan → drain; **loop-audit** CLI
- **Failure KB**, constitutional **rails**, collapse detector in agent CLI
- **Verkle** knots + audit; **improve** scout/eval/promote gate
- **Seat registry**, power switch, cursor hooks, improve→cloud handoff
- **cost_simulator** + `configs/cost_rates.yaml`
- Planning specs: loop discipline, seat economics, local steward, seat playbook (priors), one-pagers 01–08

**Evidence of past failure (mined):** autorun replanned same queue goal 2000+× (plan theater); verkle orphan fan-out; “100+ steps” often harness ticks not one agent.

---

## 4. v4 product pillars (what research should inform)

### A. Loop discipline
Auto-detect plan theater, verkle fan-out, agent churn. Typed reflexes (pause fill, dedupe, batch backfill). Patterns in `configs/training_patterns.yaml`. Eval cases frozen — no mandatory live re-test.

### B. Seat economics
`task_estimate` on route → `cost_ledger` at terminal → weekly `seat_economics_map`. Maximize **value/outcome per USD**, not cheapest tokens.

### C. Seat intelligence (no test farm)
**Public priors** (vendor docs, community, scout URLs) in `configs/seat_playbook.yaml` → **seat_score** at route time → **posterior** from usage ledger. Record capabilities + tips for Ollama, DeepSeek, Grok, Cursor IDE, Cursor cloud agent, Composer.

### D. Local steward
Queued `[steward]` jobs (prompt catalog, bug hunt, patterns, verkle digest, engine digest). Full Verkle read local-only. **Actor memory** (persons + engines) editable/auditable like xAI memory — facts not chat dumps.

### E. Layered law (not one agent constitution)
L5 constitution → L4 rails → L3 frozen BUILD → L2 case law (FKB, decisions_log) → L1 skills → L0 reflexes. Emergence → draft → human promote.

### F. Wiring gaps (use before build)
Pack `mode` + job-aware skills; skill_seat preamble on spawn; fix broken skill paths; improve intake from loop-audit + training events.

---

## 5. Research questions (pick 2–4 per session)

### Architecture & industry
1. Who runs **multi-model stacks** (planner/builder/evaluator) successfully? What artifacts do they pass between sessions?
2. Compare **Microsoft Conductor**, **OpenAI Agents SDK**, **Anthropic long-running harness**, **Cursor swarm economics**, **Factory missions**, **OpenClaw** — what contracts to steal vs reject for a **local-first, forkable** harness?
3. How do others do **memory without chat-as-DNA** (Mem0, Zep, HF threads)? What aligns with Verkle/residual + actor facts?

### Economics & routing
4. Best practices for **prior + posterior** seat routing without running private benchmarks?
5. Public benchmark tables (LMSYS, OpenRouter stats, vendor sheets) — how to ingest as **cited priors** responsibly?
6. Dual-stack: **Cursor subscription for hands** + **own API keys for drain** — who documents this well?

### Process & anti-patterns
7. How do teams prevent **plan theater** and **orchestration loops** in agent systems?
8. **Promote gates** and **amend logs** for self-modifying systems — precedents?
9. What is the minimum **eval surface** when you refuse a full test farm?

### Mag-specific synthesis
10. Propose a **3-doc repo structure** (PLATFORM / V4_PRODUCT / RESEARCH_INBOX) — what moves from current v3-named docs?
11. Prioritized **RUN sequence** (10–15 rows) for remaining v4 with seat assignment (Grok/Cursor/DeepSeek/Ollama) and marginal cost band.
12. Gaps in our playbook vs public knowledge for **DeepSeek, Grok, Cursor cloud, Ollama gemma4** — draft seat card improvements with sources.

---

## 6. Non-goals (hard constraints)

- Auto-promote router, skills, or rails without human `promote --apply`
- Chat or vendor session store as cold DNA (residual/Verkle is DNA)
- Training export of raw T0/T1 private content
- Hijacking Cursor’s internal billing / MITM Composer
- Second orchestrator brain or “MS Conductor replaces mag/conductor.py”
- LMSYS-style full replication on operator hardware
- v3 backlog as mandatory completion checklist

---

## 7. Mag law (must respect in recommendations)

```text
L1 file → L2 score → L3 human promote → L4 habit → L5 constitution
One outcome per leaf (knot / test / PR / catalog row)
Janitor-first routing; Grok scarce; pack-first context
Prompt is never memory (process → playbook; case → residual)
Join keys on events: queue_id, task_id, session_id, plan_fingerprint
```

---

## 8. Key repo artifacts (if you have file access)

| Path | Content |
|------|---------|
| `docs/ref/onepagers/` | Distilled briefs 01–08 |
| `docs/ref/MAG_V4_CONDUCTOR_LOOP_DRAFT.md` | Loop + economics spec |
| `docs/ref/MAG_LOCAL_STEWARD.md` | Steward + actor memory |
| `docs/ref/MAG_SEAT_INTELLIGENCE.md` | Playbook + inference model |
| `docs/ref/MAG_LOOP_DISCIPLINE.md` | Waste patterns |
| `docs/ref/MAG_BEHAVIORAL_COMPOUNDING.md` | L1–L5 compounding |
| `docs/ref/MAG_TRAINING_DATA_SPEC.md` | Event schema |
| `docs/ref/MAG_FULL_BLAST_PLAN.md` | Grok + Cursor + Mag dual-stack |
| `docs/ref/AGENTIC_LANDSCAPE_2026.md` | Steal map |
| `docs/ref/MAG_STEAL_AUTOPILOT.md` | Who to rob |
| `configs/training_patterns.yaml` | Loop patterns (draft) |
| `configs/seat_playbook.yaml` | Seat priors + tips (draft) |
| `configs/cost_rates.yaml` | USD priors |
| `memory/improve/SEATS.md` | Canonical seat matrix |

---

## 9. Requested deliverable shape (choose one per research session)

**Option A — Comparative report (preferred for Grok)**  
2–4 pages: tables + “steal / reject / defer” per framework. End with **top 5 RUN rows** for Mag.

**Option B — Seat playbook enrichment**  
YAML or markdown patches to `seat_playbook.yaml` with **cited URLs** and confidence labels — no uncited claims.

**Option C — Doc reorg proposal**  
Outline `MAG_PLATFORM.md` + `MAG_V4_PRODUCT.md` + what to archive; no code.

**Option D — Research bibliography**  
Annotated links grouped by: orchestration, memory, economics, guardrails, eval-minimal — each with one-line “Mag slot.”

**Option E — Mermaid**  
Single diagram: v3 substrate + v4 process + data flows (estimate → ledger → playbook posterior).

---

## 10. Example opening ask (paste after this brief)

```markdown
Using the Mag v3/v4 research brief above:

**Ask:** Option A + Option B for seat routing only.

**Deliver:**
1. Comparative table: Anthropic harness, OpenAI Agents SDK, Cursor swarm, OpenClaw, Factory — columns: handoff artifact, eval boundary, memory model, promote gate, Mag slot, reject reason.
2. Draft improvements to seat cards for deepseek_api, grok_tui, cursor_cloud_agent — each tip must have source URL or label community_hearsay.
3. Recommended RUN order for v4 wiring (pack mode, loop_outcome, seat_score) with seat per RUN and rough marginal $ band.

Do not propose auto-promote or chat-as-memory. Cite sources.
```

---

## 11. One-line summary for the researcher

> **Mag v3 = what runs; v4 = how it learns and stops wasting; research should steal industry contracts into that split, enrich seat priors from public data, and sequence RUNs — not expand the v3 backlog.**

---

*End of research brief — operator may attach one-pagers or yaml files if the tool allows file upload.*
