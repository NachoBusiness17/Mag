# FILE block — paste at end of ANY seat session (Cursor cloud, Slack, tablet, Grok)

Mag only counts work that is **FILEd** to disk → residual DNA → Verkle leaf.  
Chat heat without FILE is invisible to the office.

## Required end-of-session block

```text
FILE for Mag residual:
- What turned (3 bullets)
- Open loops
- Paths / commits touched
- One next move
- Commitment slug
```

## How to FILE (pick one)

### A — Home machine CLI (after git pull / cloud work)

```powershell
mag.cmd seat-file --seat cursor-cloud-<run-id> --source cloud --file-block @-
# paste FILE block, Ctrl+Z Enter (Windows) or pipe from file

python main.py summarize-session --all-agents
```

### B — REST from tablet / automation (home Mag running)

```bash
curl -X POST http://<HOME-IP>:8765/api/v1/handoff/file \
  -H "Authorization: Bearer $MAG_REMOTE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"FILE for Mag:\n- turned: …\n- next move: …","source":"tablet","device":"ipad"}'
```

`FILE for Mag` blocks **auto-commit a Verkle leaf**. Short todos go to `queue/todo.md` only.

### C — Full transcript (Cursor cloud / Slack bot → home)

```bash
curl -X POST http://127.0.0.1:8765/api/v1/seat/file \
  -H "Content-Type: application/json" \
  -d '{
    "seat": "cursor-bc123",
    "source": "cursor-cloud",
    "provider": "cursor",
    "messages": [
      {"role":"user","content":"goal"},
      {"role":"assistant","content":"what changed"}
    ]
  }'
```

### D — Cursor IDE (local — hooks)

SessionEnd → `watch/cursor_hook.py` → `summarize-session --source cursor`  
Ensure `.cursor/hooks.json` is wired (`launch_cursor_seat.cmd`).

## Verify

```powershell
python main.py pack-status
# complete = residual + card + commit + leaf
```

Days tab → latest bead. Tip leaves should increment.

## Law

**Decoder ≠ boundary.** Cloud agents file code to GitHub; **Mag files meaning** to Verkle.  
Both: `git pull` + `seat-file` / `handoff/file` on the home machine.
