# Release gate log (operator soil)

Append-only graduation gates recorded via:

```powershell
python main.py release record --version v2 --gate run_a --ok --note "routing_smoke 9/9"
```

Also emits `release_milestone` to `memory/training/events.jsonl`.

Registry: `configs/releases.yaml` · Notes: `docs/ref/releases/`
