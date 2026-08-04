#!/usr/bin/env python3
"""Synthesis Agent (the Scribe) -- third process of the Tripartite.

Writes memory/running_commentary.md for the dashboard Chronicle tab.
READ-ONLY on all sources except the chronicle file itself.

Usage:
  python synthesis_agent.py            run forever (10s refresh)
  python synthesis_agent.py --once     synthesize once and exit (smoke)
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TASKS_DIR = ROOT / "memory" / "runs" / "orchestrator" / "tasks"
ORC_LOGS = ROOT / "logs" / "orchestrator"
MAG_JSONL = ROOT / "logs" / "mag.jsonl"
KPI_JSONL = ROOT / "logs" / "kpi.jsonl"
ATTENTION = ROOT / "memory" / "attention.md"
BONDS = ROOT / "memory" / "bonds_active.md"
CHRONICLE = ROOT / "memory" / "running_commentary.md"
TMP = ROOT / "memory" / "running_commentary.md.tmp"

REFRESH_S = 10
MAX_EVENTS = 12
TERMINAL = {"done", "failed", "timeout", "stalled", "killed", "died"}

OK = "\u2705"
FAIL = "\u274c"
RUN = "\u23f3"
INFO = "\u2139\ufe0f"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _last_jsonl(path: Path, n: int = 1) -> list[dict]:
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out[-n:]


def _attention_pulse(limit: int = 6) -> list[dict]:
    if not ATTENTION.is_file():
        return []
    text = ATTENTION.read_text(encoding="utf-8", errors="replace")
    blocks = re.split(r"\n---+\n", text)
    out = []
    for block in blocks:
        m_sess = re.search(r"session:\s*`([^`]+)`", block)
        m_seat = re.search(r"seat:\s*`([^`]+)`", block)
        if not m_sess:
            continue
        sid = m_sess.group(1).strip()
        seat = (m_seat.group(1) if m_seat else "?").strip()
        if "cursor" in sid.lower():
            layman = "Cursor filed work to Mag"
            icon = OK
        elif seat == "mag_agent":
            layman = "Mag agent session filed"
            icon = OK
        else:
            layman = f"Session from {seat}"
            icon = INFO
        out.append({
            "icon": icon,
            "layman": layman,
            "technical": f"`{sid}` seat=`{seat}`",
            "proof": "memory/attention.md",
        })
        if len(out) >= limit:
            break
    return out


def _fleet_recent() -> tuple[list[dict], dict[str, int]]:
    """Running + last-24h tasks only — not soak-test graveyard."""
    if not TASKS_DIR.is_dir():
        return [], {}
    now = datetime.now(timezone.utc)
    recs = []
    counts: dict[str, int] = {"running": 0}
    for p in TASKS_DIR.glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        st = d.get("status") or "?"
        if st not in TERMINAL:
            counts["running"] = counts.get("running", 0) + 1
            recs.append(d)
            continue
        ts_raw = d.get("ended_at") or d.get("created_at") or ""
        try:
            ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
            if (now - ts).total_seconds() <= 86400:
                counts[st] = counts.get(st, 0) + 1
                recs.append(d)
        except ValueError:
            pass
    recs.sort(key=lambda d: d.get("created_at") or "", reverse=True)
    return recs[:MAX_EVENTS], counts


def _events(recs: list[dict]) -> list[dict]:
    evs = []
    for d in recs:
        st = d.get("status") or "?"
        if st in ("done", "complete", "ok"):
            icon = OK
        elif st in TERMINAL - {"done"}:
            icon = FAIL
        elif st in ("running", "queued", "spawned"):
            icon = RUN
        else:
            icon = INFO
        tag = d.get("tag") or (d.get("task_id") or "?")[:8]
        ts = (d.get("ended_at") or d.get("created_at") or "")[:19]
        goal = d.get("goal") or ""
        if not goal:
            cmd = d.get("cmd") or []
            try:
                i = cmd.index("--query")
                goal = cmd[i + 1] if i + 1 < len(cmd) else ""
            except ValueError:
                pass
        evs.append({
            "ts": ts.replace("T", " "),
            "icon": icon,
            "status": st,
            "tag": tag,
            "msg": (goal or tag)[:100],
        })
    return evs


def _activity_tail(n_logs: int = 2) -> list[str]:
    if not ORC_LOGS.is_dir():
        return []
    logs = sorted(ORC_LOGS.glob("*.out.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    out = []
    for p in logs[:n_logs]:
        try:
            lines = [l for l in p.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
        except OSError:
            continue
        if lines:
            out.append(f"{p.stem}: {lines[-1][:160]}")
    return out


def _engine_phase() -> str:
    rec = _last_jsonl(MAG_JSONL)
    if not rec:
        return "no phase record"
    r = rec[0]
    return f"{r.get('phase') or '?'} (n={r.get('n')})"


def synthesize() -> str:
    att = _attention_pulse(6)
    recs, counts = _fleet_recent()
    evs = _events(recs)
    activity = _activity_tail()
    phase = _engine_phase()
    kpi = _last_jsonl(KPI_JSONL)

    bonds_note = ""
    if BONDS.is_file():
        m = re.search(r"Ingested `([^`]+)`", BONDS.read_text(encoding="utf-8", errors="replace")[:400])
        if m:
            bonds_note = m.group(1)

    lines = [
        "# Pulse — what Mag actually saw",
        "",
        f"_File-backed {_now()} · refresh {REFRESH_S}s · "
        "sources listed at bottom · no model calls_",
        "",
        "## Plain English",
        "",
    ]

    if bonds_note:
        lines.append(f"- **Latest bonds update:** {bonds_note}")
        lines.append(f"  _Proof: memory/bonds_active.md_")
    if counts.get("running"):
        lines.append(f"- **Workers:** {counts['running']} sub-agent(s) running right now")
    else:
        lines.append("- **Workers:** none running (orchestrator idle)")
    if att:
        lines.append(f"- **Last filed session:** {att[0]['layman']} — {att[0]['technical']}")

    lines += [
        "",
        "## Filed sessions (from attention.md)",
        "",
    ]
    if att:
        for a in att:
            lines.append(f"- {a['icon']} {a['layman']} · {a['technical']}")
    else:
        lines.append("- _(no session blocks in attention.md yet)_")

    lines += [
        "",
        "## Workers (running + last 24h only)",
        "",
    ]
    if evs:
        for e in evs:
            lines.append(f"- {e['icon']} [{e['ts']}] {e['status']} `{e['tag']}` — {e['msg']}")
    else:
        lines.append("- No recent worker events")

    if activity:
        lines += ["", "## Latest log tails", ""]
        for a in activity:
            lines.append(f"- {a}")

    lines += [
        "",
        "## Engine room (technical)",
        "",
        f"- Mag phase: {phase}",
        f"- Worker counts (24h window): {dict(counts) if counts else '(none)'}",
    ]
    if kpi:
        k = kpi[0]
        lines.append(
            f"- Records KPI: {k.get('n_sessions')} sessions, "
            f"{k.get('n_leaves')} leaves, complete_pct {k.get('complete_pct')}%"
        )

    lines += [
        "",
        "---",
        "",
        "**Sources (truth):** `memory/attention.md` · `memory/bonds_active.md` · "
        "`memory/runs/orchestrator/tasks/` (24h filter) · `logs/orchestrator/*.out.log` · "
        "`logs/mag.jsonl`",
        "",
        "_Template summary only — not AI interpretation. For structured events use GET /api/v1/chronicle._",
    ]
    return "\n".join(lines)


def write_chronicle() -> None:
    body = synthesize()
    TMP.write_text(body, encoding="utf-8")
    TMP.replace(CHRONICLE)


def main() -> int:
    once = "--once" in sys.argv
    while True:
        try:
            write_chronicle()
        except Exception as e:
            print("synthesis tick failed:", e, flush=True)
        if once:
            return 0
        time.sleep(REFRESH_S)


if __name__ == "__main__":
    raise SystemExit(main())
