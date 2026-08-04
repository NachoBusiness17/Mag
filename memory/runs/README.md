# memory/runs — warm-mid trail substrate

**Not DNA.** Cold truth stays `memory/biography/residual/`.  
Runs are one goal + one seat for minutes–hours.

| File | Role |
|------|------|
| `active.json` | Pointer to open run (at most one) |
| `{run_id}/run.json` | `mag_run.v1` — seat lock, proactivity, bounds, `run_commit` on close |
| `{run_id}/trail.jsonl` | `mag_trail_event.v1` — append-only events + optional `core` |
| `{run_id}/progress.md` | Artifact handoff (initializer + cores) — warm pre-leaf |
| `related_runs.jsonl` | Closed-run cards → bonds (lattice edge, not tip) |

```text
python main.py trail start "goal" --seat local --proactivity narrow
python main.py trail append "decision …" --kind decision --core "{\"type\":\"decision\",\"text\":\"…\"}"
python main.py trail check-seat --seat remote   # expect fail if locked local
python main.py trail pack
python main.py context-pack                     # includes run_trail excerpt
python main.py trail close --reason done
```

Compose steals: trail integrity · seat purity · proactivity dial · pack-first.  
See `docs/templates/FEATURE_COMPOSE.md`.
