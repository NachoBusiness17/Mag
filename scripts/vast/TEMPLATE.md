# Mag Vast template — Ollama plant (Grok Build stays home)

## Architecture (do not invert)

| Seat | Where | Role |
|------|--------|------|
| **Grok Build TUI** | Your Windows PC | Sovereign judgment, hard code, chat |
| **Mag lab + BST dash** | Your PC (`:8765`) | DNA, influence, promote, trail |
| **Ollama worker** | Vast GPU instance | Hot inference only |

**Never** put Verkle tip / agent_state / private DNA only on Vast disk (interruptible).

```
[You] ── Grok Build
  │
  ├── Mag lab :8765  (DNA local)
  │     blast digs / dispatch / ask
  │
  └── SSH -L 11434:127.0.0.1:11434 ──► [Vast] Ollama :11434
```

## Hardware target (from your listing)

- **1× Quadro RTX 8000 · 48 GB VRAM** (Turing, solid Q4 inference)
- ~16 CPU / ~96 GB RAM slice (enough for embed + OS + KV if needed)
- Prefer **≥80 GB disk** on the offer (model pulls)

## Create the template (UI — recommended first)

1. Open [cloud.vast.ai/templates](https://cloud.vast.ai/templates/) → **+ New** (or edit a copy of *Ubuntu + CUDA / base*).
2. **Image** (pick one):
   - Fast start: `ollama/ollama:latest` **or**
   - Vast-friendly: `vastai/base-image:cuda-12.4.1-cudnn-devel-ubuntu22.04` + on-start installs Ollama  
   (Use on-start script below either way.)
3. **Launch mode**: **SSH** (direct SSH on if available).
4. **Docker options** (example):
   ```text
   -p 22:22 -p 11434:11434 --gpus all --shm-size=16g
   ```
5. **Disk**: 80–120 GB.
6. **On-start script**: paste contents of `onstart_mag_ollama.sh` from this folder.
7. **Env** (optional):
   ```text
   -e MAG_STACK=rtx8000_48 -e OLLAMA_HOST=0.0.0.0:11434
   ```
8. Save as **`mag-ollama-rtx8000`** (private).

### From a running good instance

If you already bootstrapped once: instance menu → **Save as Template** (or equivalent “create template from instance”). That freezes image + ports + on-start.

### API sketch

```bash
# After template exists in UI, deploy with CLI:
# vastai search offers 'gpu_ram>=48 num_gpus=1 reliability>0.98'
# vastai create instance <offer_id> --template_hash <hash> --disk 100
```

Docs: https://docs.vast.ai/guides/templates/creating-templates

## After rent — Windows (Grok Build side)

```powershell
# Terminal A — tunnel (leave open)
.\scripts\blast_connect_vast.ps1 -HostIp <IP> -Port <PORT>

# Terminal B — Mag + Grok Build world
cd $env:USERPROFILE\Documents\projects\local_sovereign_agent
$env:OLLAMA_HOST = "http://127.0.0.1:11434"
# Point lanes at 48GB stack (copy once):
# copy configs\lanes_vast_rtx8000.yaml configs\lanes.yaml   # or merge by hand
.\.venv\Scripts\python.exe main.py blast --status
.\.venv\Scripts\python.exe main.py lab
.\.venv\Scripts\python.exe main.py blast --run --bg
```

Grok Build: keep working as now. Mag BST steers digs. Grok only for `[priority]` judgment.

## Model policy for this card

See `MODEL_STACK.md` in this folder. **Default:** one strong 32B worker hot — not a tight 70B that leaves no room for context.

## Destroy / residue

Before destroy instance:

```powershell
# On PC — digs already local under memory/improve/
# Optional: rsync any /workspace/models you care about (usually skip — re-pull is fine)
```

Promote practices you will run. Kill instance so interruptible doesn’t surprise-bill.
