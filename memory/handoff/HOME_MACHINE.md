# HOME MACHINE — distributed Mag runbook

**Pull this file after `git pull`.**  
**Plan:** `docs/ref/DISTRIBUTED_SURFACE.md` · **Phase:** see `configs/distributed_surface.yaml`

---

## What this machine is

This PC is **Mag HQ** — the canonical boundary. Tablets, phones, and cloud agents are **viewports or decoders**, not replacements for this disk.

| Lives here (soil) | Does not live on GitHub alone |
|-------------------|-------------------------------|
| `memory/` bonds, briefs, working | residual DNA |
| `state/CURRENT.md` resume contract | live goal |
| `state/shared_activity.jsonl` | cross-seat feed |
| `queue/` handoffs | orchestrator work |

---

## Daily start (this machine)

```powershell
cd $env:USERPROFILE\Documents\projects\local_sovereign_agent
git pull
mag.cmd doctor
mag.cmd lab
# → http://127.0.0.1:8765/
```

---

## Let tablet / phone hit this machine (same Wi‑Fi)

**Phase G3 — LAN path (works today):**

```powershell
launch_dashboard_lan.cmd
# Find IPv4: ipconfig
# On tablet browser: http://<THIS-PC-IP>:8765/
```

**Safer than raw LAN (recommended next):** Tailscale on home PC + tablet → use Tailscale IP instead of public Wi‑Fi.

---

## FILE from tablet → this machine (Phase G1 — live)

```bash
curl -s -X POST http://<HOME-IP>:8765/api/v1/handoff/file \
  -H "Content-Type: application/json" \
  -d '{"text":"FILE for Mag:\n- turned: …\n- open loops: …\n- next move: …","source":"tablet","device":"ipad"}'
```

Files land in `memory/handoff/inbound/` and update `memory/handoff/latest_inbound.md`.

Check surface status:

```bash
curl -s http://127.0.0.1:8765/api/v1/surface
```

---

## Remote Cursor / cloud agent (decoder only)

Cloud agents see **GitHub**, not this disk. Use them for **code PRs**, not Mag memory.

To delegate **tool work** to Mag on this machine from another Cursor install:

```powershell
$env:MAG_URL = "http://<HOME-IP-OR-TAILSCALE>:8765"
python watch/cursor_bridge.py pack
python watch/cursor_bridge.py ask "goal from remote seat"
```

---

## Phase checklist (update as you ship)

- [x] **G0** — plan + this runbook committed
- [x] **G1** — `/api/v1/handoff/file` + `/api/v1/surface`
- [ ] **G2** — `MAG_REMOTE_TOKEN` on remote bind
- [ ] **G3** — Tailscale + `MAG_PUBLIC_URL` on home box
- [ ] **G4** — optional Syncthing for `memory/` + `state/` to second machine

---

## After cloud agent work

```powershell
git pull    # merge PRs from cloud
mag.cmd context-pack
mag.cmd bonds
# Re-read state/CURRENT.md and memory/handoff/inbound/
```

**Law:** FILE outcomes to disk. Chat is heat.
