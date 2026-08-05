# Mag version registry

**Commitment:** `mag-version-registry-001`  
**As-of:** 2026-08-05  
**Machine truth:** `configs/releases.yaml`  
**Behavioral trail:** `memory/improve/releases/gates.jsonl` (operator) + `memory/training/events.jsonl` (`release_milestone`)

**Job:** Index every major version, its release notes, direction artifacts, and graduation gates — so v3/v4/v5 iterate from filed history, not chat.

---

## Version map (operator definitions)

| ID | Meaning | Status | Release notes |
|----|---------|--------|---------------|
| **v1** | **Grok/X** era that spawned the project | shipped | [RELEASE_NOTES_v1.md](RELEASE_NOTES_v1.md) |
| **v2** | **This repo** in `projects/` — database + harness | shipped | [RELEASE_NOTES_v2.md](RELEASE_NOTES_v2.md) |
| **v3** | **Planning** — substrate we're building next | in_progress | [RELEASE_NOTES_v3.md](RELEASE_NOTES_v3.md) |
| **v4** | Mold — process before volume | planned | template |
| **v5** | Pipe — GSTD, Vast, XRPL | planned | [MAG_v5_PIPE.md](../MAG_v5_PIPE.md) |

**Witness:** [WITNESS_SPINE.md](WITNESS_SPINE.md) · [strike_origin.md](../strike_origin.md)  
**Subprocess map:** [MAG_VERSION_SUBPROCESS_MAP.md](MAG_VERSION_SUBPROCESS_MAP.md)

---

## Version map (artifacts)

---

## Artifacts each version needs

| Layer | Artifact | v1 | v2 | v3 | v4 | v5 |
|-------|----------|:--:|:--:|:--:|:--:|:--:|
| Release notes | `RELEASE_NOTES_vN.md` | ✓ | ✓ | ✓ | TBD | TBD |
| Run sheet / plan | NEXT_CODING_RUN / vN_PLAN | — | ✓ | ✓ | draft | pipe |
| Behavioral gates | `release record` CLI | — | run_a | factory, chat | eval | probe |
| Training pattern | `release_milestone` events | — | ✓ | ✓ | ✓ | ✓ |
| Backlog defer row | `MAG_v3_BACKLOG.md` §6 | — | — | ✓ | ✓ | v5 rows |

---

## Behavioral memory — how versions compound

```text
Release notes (L1 FILE, git)
    ↓
release record → gates.jsonl + training event (L2 SCORE)
    ↓
improve scout / behavioral_synth themes (L2)
    ↓
promote → RUN row / template clause (L3 habit)
    ↓
next RELEASE_NOTES_vN (L1)
```

**Rule:** Gate passed on disk before release notes claim "shipped."

---

## Operator commands

```powershell
python main.py release status
python main.py release notes v2
python main.py release record --version v2 --gate run_a --ok --note "routing_smoke 9/9"
python main.py training-events --stats --pattern release_milestone
```

---

## Amend protocol

1. Edit release notes + bump `as-of` in front matter  
2. Update `configs/releases.yaml` status/gates  
3. `release record` for each gate crossed  
4. One line in `memory/decisions_log.jsonl` if direction changes  

---

*Template: [RELEASE_NOTES_TEMPLATE.md](RELEASE_NOTES_TEMPLATE.md)*
