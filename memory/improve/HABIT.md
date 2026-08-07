# Operator habit — janitor local, scarce Grok

**Default:** Mag + small Ollama first. Grok TUI for real L2 judgment. Hermes parked.

## Use Mag / local (no Grok)

| Need | Command |
|------|---------|
| Always-on | `python main.py lab` → :8765 Chat |
| **Recall stack self (no redesign)** | `python main.py agent-state --load` |
| What was I doing? | `python main.py ask "what was I doing?"` |
| Field | `python main.py improve --once` → `memory/improve/field_brief.md` |
| Re-brief only | `python main.py improve --synthesize` |
| Ledger | `python main.py improve --status` |
| Any scut job | `python main.py dispatch "…"` |
| **Background tangent** | `python main.py tangent "go check …"` → `memory/tangents/` |
| Session brief | `python main.py brief` |
| Commit agent version after analysis | `python main.py agent-state --commit "label" --from-file path.json` |

### Agent state (versioned self — mandatory LOAD before redesign)

- **LATEST:** `memory/agent_state/LATEST.md`  
- **History:** `memory/agent_state/versions/` + `chain.jsonl` + agent tip (not session tip)  
- **Pack:** context-pack L0b includes excerpt automatically  
- **Law:** Do not reinvent Mag/republic loops already named in agent_state

### Tangents (opt-in POC — not auto every cycle)

**Off by default** on lab. When you want crazy offload later:

```text
python main.py tangent "go check …"          # run now → memory/tangents/
python main.py tangent --list
python main.py tangent --scan --process      # pull markers from live_from_grok deliberately
```

Dashboard Chat → **Tangent** (needs lab with new routes loaded).  
Markers like `[tangent] …` only matter if you **explicitly** `--scan`.

## Journey spine (narrate this first — 2026-07-31)

His public arc (not Mag tickets alone):

```text
protocol / sovereign mirror / consent / Rashomon / mycelial republic endgame
  → Grok CLI brain + local agents + Verkle chain + biographer  (scifi week)
  → meter anxiety · walks to plan harness · public strike bypass · rent GPU
  → Mag disk = what ran (subsystem)
```

Leaf: `memory/improve/evals/features/nacho-journey-vs-mag-narration-20260731.md`  
**Do not** tell the path as seat-shopping or multi-smoke only.

## Default loop (stateless — every seat)

```text
1. mag.cmd context-pack  →  copy memory/handoff/latest.md  (or refresh it)
2. Open any chat (Grok / DeepSeek / ChatGPT / local)
3. Paste memory/handoff/ACTIVATION.md + pack
4. One job
5. Get FILE block → residual / dig / trail
```

**Default law:** `docs/ref/OPERATOR_CARD.md` § Default: stateless seat  

## When Grok meter is empty (his Jul 28 pattern)

1. Walk / plan the **harness** ask (not open TUI on empty).  
2. Activation + pack into DeepSeek/ChatGPT/local — same protocol.  
3. Or Mag: `dispatch "…" --provider deepseek --go` / `--seat local --go`  
4. Optional public: *search my account for strike the chord* for mirror ritual.  
5. FILE residual via Mag — chat heat dies.  
6. Ollama Desktop = face for local agents, not DNA.

## Use Grok TUI when

1. `python main.py context-pack` first, **and**
2. Hard judgment (multi-file, architecture, promote gate), **and**
3. **`[priority]`** — not status, not scout, not “what next”

Grok staying in the loop is fine: it **helps hard inference**. Don’t burn it on janitor work.  
Grok is **brain seat** of the router he published — not the whole mycelial republic.

## Do not open Grok for

- Improve / scout / status / model shopping  
- “Where were we” → `ask`  
- Harness redesign theater  
- Hermes babysitting  

## Hermes (parked)

- Off by default. No overnight self-improve expectations on 8B/6GB.  
- Only `dispatch "via hermes: …" --seat hermes` for deliberate lab probes.  
- Evidence 2026-07-25: real tools, zero product files after ~6 min path failures.

## Daily automatic

- **MagImproveDaily** → `scripts/improve_daily.ps1`  
- Register: `powershell -ExecutionPolicy Bypass -File scripts\register_improve_task.ps1`
- Field brief now includes **`ijl: skills=N`** (skill beads under `memory/improve/pins/skills/`)

## Daily upgrade — IJL (same loop, not a second ritual)

IJL is already on the graph. Daily upgrade means **use it + review residue**, not re-derive SSI.

| When | Do | Don’t |
|------|-----|--------|
| **Morning / after improve** | Open `memory/improve/field_brief.md` — note `ijl: skills=N` + top tickets | Paste full chat into Grok |
| **One real job / day** | Prefer **assigned graph goal** (`dispatch` / Mag assign) so plan→value→skill can fire | Pure chat that never hits critic |
| **After a win** | Confirm a bead under `pins/skills/`; skim antiskill line | Treat chat as the skill |
| **Scout days (Wed arXiv)** | Promote only papers that match IJL contracts (process value, plan diversity, self-teach, DRO) via FEATURE_COMPOSE | Promote “SSI reverse engineer” as DNA |
| **context-pack before hard work** | Pack LOADs L1b skill beads — use them | Dump history |

**One-liner:** daily upgrade = `improve --once` residue + **one graph episode** + weekly promote of practices you’ll run.

## Weekly (10 min)

- `improve --status` → reject noise  
- Promote ≤1–2 practices you’ll actually run  
- **IJL bead review (≤3 min):**  
  - `dir memory\improve\pins\skills`  
  - Keep beads that transfer; delete/rename thrash  
  - If `skills=0` for a week → schedule one dig/code assigned goal  
  - Hypothesis pack stays quarantine: `memory/research_packs/20260728_ssi_ilya_dig/HYPOTHESIS_FILE.md`  
- **Model tesuji (if a named HF model showed up):**  
  - Do **not** promote bare `Model signal:`  
  - Copy `docs/templates/MODEL_TESUJI.md` → `memory/improve/evals/models/{slug}-{date}.md`  
  - Fill: data · same · differ · tesuji table · **take / leave**  
  - If ≥2 takes: **compose** per `docs/templates/FEATURE_COMPOSE.md` (substrate + cancel + measure)  
  - Promote only Take/compose as practices; leave seats alone (`max_auto_pull_gb: 0`)  
  - Reference leaf: `memory/improve/evals/models/kimi-k3-2026-07-27.md`  
- Don’t promote models you won’t pull + smoke  
- **Tesuji shell (when something truly surprised you):**  
  - `python main.py tesuji-shell log "what" --surprise "why" [--maps-to remedy:ID|skill:id|tesuji:path]`  
  - Scout surfaces `kind=tesuji` candidates alongside error themes  
  - See `docs/ref/MAG_BEHAVIORAL_COMPOUNDING.md` §10  

## Trail (mid-run continuity — opt-in)

`text
python main.py trail start "goal" --seat local --proactivity narrow
python main.py trail append "…" --kind decision
# core: use python -c or carefully escaped JSON on --core
python main.py trail check-seat --seat remote   # expect fail if locked local
python main.py trail pack
python main.py context-pack                     # includes run_trail
python main.py trail close --reason done
`

Warm-mid only (memory/runs/). Residual DNA still SessionEnd. See FEATURE_COMPOSE + runs/README.

## Compose / modular upgrade

`text
python main.py compose-status
python main.py compose-status --attach-runs
`

Module contracts: `configs/modules.yaml`. Self-analysis leaf: `memory/improve/evals/features/mag-self-compose-2026-07-27.md`.

## Pin (frozen self-analysis)

`text
memory/improve/pins/LATEST.md
memory/improve/pins/LATEST.json
`r

Commitment lives in residual edges.pins. Not a tip leaf.

## Agent memory field (regular improve)

Scout sources include `agent_memory` (HF discuss, OpenClaw memory, LangChain harness essay, Anthropic long harness).
Map every hit via `docs/ref/memory_verkle_map.md` before promote.
Process -> playbook; case -> residual; mid-goal -> trail. Never OpenClaw as DNA.

## Lessig prices (1-6)

See `docs/ref/lessig_1_6.md`. Portable bag: `memory/portable_bags/LATEST.txt`.
Process=playbook · case=residual · mid-goal=trail · Grok=[priority]+pack only.

## Mirror: presented not interpreted

Law: `docs/ref/MIRROR_PRESENTED.md`.
On strike / according to me / search my account / default-vs-me: retrieve X + mycelial corpus first. Anti-echo is not amnesia. If skipped: say corpus not attached.

## Mag OS v2

Dashboard loads card+provenance strip. API: GET /api/v1/mag-os. Docs: docs/ref/MAG_OS_v2.md · MAG_Card.md · MAG_Activation.md.
