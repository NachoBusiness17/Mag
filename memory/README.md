# Memory layout (local operator soil)

This folder is **your machine's live state**. The GitHub repo ships **code + seed templates** only.

After clone:

1. Directories exist via `.gitkeep` — Mag creates files on first `lab`, `boot`, or chat session.
2. Copy `memory/operator_directives.md` is the autonomy contract (safe to customize).
3. Never commit `.env`, API keys, or filled `memory/biography/` residuals.

## Tracked seeds (in repo)

| Path | Purpose |
|------|---------|
| `handoff/ACTIVATION.md` | Operator activation note |
| `handoff/DEEPSEEK_START.md` | DeepSeek seat bootstrap |
| `operator_directives.md` | Autonomy contract (context pack L0c) |
| `improve/GOAL.md`, `HABIT.md`, `SEATS.md`, `MIRROR.md` | Improve loop framework |
| `boot/REPUBLIC_LAUNCH.md` | Fresh-clone entry → Mycelial Republic |
| `viewports/.gitkeep` | Cursor Canvas manifests land here (`canvas-sync`) |
| `lattice/.gitkeep` | Queryable lattice store (`lattice-backfill`) |
| `runs/README.md` | Run trail convention |

Everything else under `memory/` is gitignored and created at runtime.
