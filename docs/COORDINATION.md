# Cross-seat coordination

Mag routes work by **depth** so Grok, DeepSeek, and local janitors each do what they are good at — without burning tokens on the wrong seat.

## Depth → seat map

| Depth | Seat | Launch | Use for |
|-------|------|--------|---------|
| `overview` | Grok TUI | Pack only | Big-picture maps, interlinking, ecosystem |
| `plan` | Grok TUI | Pack only | Architecture, tradeoffs, code planning |
| `heavy_code` | DeepSeek | Delegate / queue | Multi-step coding, refactors, tests |
| `simple_code` | Local (Ollama) | Dispatch | Small edits, one-file fixes |
| `scut` | Local | Dispatch | Status, bonds, brief, doctor |

## Shared visibility

All seats append to **`state/shared_activity.jsonl`**. Every context pack includes the last few rows so DeepSeek agents see what Cursor/Grok/Mag are doing.

```powershell
# Read feed
curl -s http://127.0.0.1:8765/api/v1/coordination

# DeepSeek / Cursor bridge
python watch/cursor_bridge.py activity
python watch/cursor_bridge.py coordinate "implement lattice query API" --dry
python watch/cursor_bridge.py coordinate "implement lattice query API" --background
```

Post heartbeat from any seat:

```powershell
curl -s -X POST http://127.0.0.1:8765/api/v1/coordination ^
  -H "Content-Type: application/json" ^
  -d "{\"seat\":\"deepseek\",\"depth\":\"heavy_code\",\"goal\":\"refactor seats.py\",\"status\":\"running\"}"
```

## CLI

```powershell
python main.py coordinate "big picture map of Mag and republic" --dry
python main.py coordinate "fix typo in README" 
python main.py coordinate "implement orchestrator heal loop" --background
python main.py coordinate "plan dashboard Body tab" --depth plan
```

## REST

```http
POST /api/v1/coordinate
{
  "goal": "implement canvas bridge tests",
  "seat": "deepseek",
  "depth": "heavy_code",
  "launch": true,
  "background": false
}
```

```http
GET /api/v1/coordination?limit=20
POST /api/v1/coordination  { "seat", "depth", "goal", "status" }
```

## Token rules (encoded in classifier)

1. **Never auto-run Grok** — overview/plan return a pack excerpt; operator pastes into TUI with `[priority]`.
2. **Heavy → DeepSeek** — tool loop or orchestrator queue (`--background`).
3. **Simple / scut → local** — Ollama janitor via `dispatch`.
4. **Context pack L0e** — coordination excerpt injected automatically.

## Dashboard

**Body** tab loads `/api/v1/coordination` — running seats + recent activity.

## Container

Works inside Docker — activity file lives on mounted `state/` volume.

## Multi-device (tablet / remote seat)

Home machine owns soil. Other devices are viewports or decoders.

| Action | How |
|--------|-----|
| Plan + phases | `docs/ref/DISTRIBUTED_SURFACE.md` |
| Pull directions on home PC | `memory/handoff/HOME_MACHINE.md` |
| Surface status | `GET /api/v1/surface` |
| FILE from tablet | `POST /api/v1/handoff/file` |
| LAN dashboard | `launch_dashboard_lan.cmd` |

See also: `memory/improve/SEATS.md`, `docs/ref/SOVEREIGN_STACK.md`, `watch/cursor_bridge.py`.
