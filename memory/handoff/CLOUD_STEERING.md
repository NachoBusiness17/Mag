# Cloud steering — Cursor brain → home Mag → DeepSeek hands

**Pull after `git pull`.** Parent: `docs/ref/DISTRIBUTED_SURFACE.md` · Bridge: `watch/cursor_bridge.py`

---

## What this fixes

Cursor Cloud is **not** Mag HQ — but it **must not ignore** Mag. Cloud agents are a **steering seat**: plan here, **execute on home** via the REST bridge so DeepSeek tokens and local janitors run as designed.

Without `MAG_PUBLIC_URL`, cloud agents only see GitHub and default to Cursor's check-in loop. That feels like betrayal of the product. Wire reachability once; every cloud run steers home first.

---

## Operator setup (once)

### 1. Home PC

```powershell
set MAG_REMOTE_TOKEN=pick-a-long-secret
set MAG_BIND_HOST=0.0.0.0
launch_dashboard_lan.cmd
# or Tailscale IP — prefer Tailscale over raw LAN
```

Enable autorun (optional but matches zero-check-in goal):

```powershell
set MAG_DRAINER=1
mag.cmd lab
# dashboard → Drainer ON; governor eats queue/todo.md [mag] lines
```

### 2. Cursor Cloud environment secrets

In Cursor → Cloud Agent → Environment (or team secrets):

| Name | Value |
|------|--------|
| `MAG_PUBLIC_URL` | `http://<tailscale-or-home-ip>:8765` |
| `MAG_REMOTE_TOKEN` | same secret as home |

Optional: `MAG_BRIDGE_TIMEOUT=300` for long delegate turns.

Template: `configs/cloud_steering.env.example`

**Home verify (prints secrets to paste):**

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify_cloud_steering.ps1
# or: mag.cmd cloud-steering-verify
```

### 3. Verify from any machine

```bash
export MAG_PUBLIC_URL=http://100.x.x.x:8765
export MAG_REMOTE_TOKEN=your-secret
python watch/cursor_bridge.py status
# reachable: true
```

---

## Cloud agent ritual (every run)

```bash
# 1. Can I reach HQ?
python watch/cursor_bridge.py status

# 2. Pull operator context from home soil (not GitHub)
python watch/cursor_bridge.py pack

# 3. Steer execution — DeepSeek tool loop on home
python watch/cursor_bridge.py steer "implement X per queue/todo" \
  --mode delegate --provider deepseek --seat cursor-cloud --pack

# 4. Or enqueue for drainer/governor (no check-in)
python watch/cursor_bridge.py steer "wire Y into verkle" --mode handoff --seat cursor-cloud
```

| Mode | When |
|------|------|
| `delegate` | Code + Mag tools on home (DeepSeek) |
| `queue` | Background orchestrator drain |
| `handoff` | FILE → `working.md` + `[mag]` todo for governor |
| `dispatch` | Let Mag classify depth/seat |

**Only edit the GitHub clone directly** when `status` returns `reachable: false` and the operator wants a PR from afar. Merge on home → `git pull` → `mag.cmd seat-file`.

---

## Why cloud “won’t use Mag” today

| Blocker | Fix |
|---------|-----|
| No `MAG_PUBLIC_URL` in cloud env | Set secrets (above) |
| Home not listening on LAN/Tailscale | `launch_dashboard_lan.cmd` + G3 |
| Agent instructions ignored bridge | `AGENTS.md` cloud steering section |
| Bridge had no auth / `steer` entry | shipped in `cursor_bridge.py` |

This cloud VM cannot reach your home network until **you** expose `:8765` and set secrets. The framework was always designed for steering — the missing piece was **reachability + agent contract**, not a different architecture.

---

## After cloud work

```powershell
git pull
mag.cmd context-pack
mag.cmd seat-file --seat cursor-cloud-<run-id> --source cloud
```

**Law:** outcomes on home disk. You steer; Mag executes.
