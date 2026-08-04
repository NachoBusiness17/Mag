"""Write handoff.v1 packet for Grok and pause.

L2 scarce lane: writes the packet AND, when the Grok open harness (CLI) is
installed, runs it headless so the escalation is a real task, not a parked
file. Set MAG_ESCALATE_HARNESS=0 to keep the park-only behavior.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from audit import log_event, sync_current
from config import HANDOFF_DIR, RESULTS_DIR
from handoff.schema import new_handoff, write_handoff
from state import AgentState


def escalate_grok_node(state: AgentState) -> dict:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    slug = "task"
    goal = (state.get("goal") or "task")[:40]
    for ch in goal:
        if ch.isalnum():
            slug += ch.lower()
        elif ch in " -_" and not slug.endswith("-"):
            slug += "-"
    handoff_id = f"{ts}-{slug[:48]}"
    return_path = str(RESULTS_DIR / f"{handoff_id}.json")

    # Prefer local brief over raw chat dump (resource harness)
    brief = ""
    try:
        from mag.lanes import latest_brief_text

        brief = (state.get("brief") or latest_brief_text() or "")[:3500]
    except Exception:
        brief = str(state.get("brief") or "")[:3500]

    facts = [
        f"local last_result (truncated): {(state.get('last_result') or '')[:1200]}",
        f"critique: {(state.get('critique') or '')[:600]}",
    ]
    if brief:
        facts.insert(0, f"local brief (primary context):\n{brief}")

    data = new_handoff(
        handoff_id=handoff_id,
        goal=state.get("goal") or "",
        ask=(
            "High-priority specialist work. Use the local brief as primary context "
            "(do not require full chat). Execute the goal with full tools. "
            "Return JSON to return_path with keys: handoff_id, ok, summary, deliverable."
        ),
        tier=state.get("tier") or "T3",
        success_checks=state.get("success_checks")
        or ["summary present", "ok true or explicit blocker"],
        inputs={
            "paths": [],
            "facts": facts,
            "constraints": [
                "Respect data tiers; do not exfiltrate T0/T1 to free APIs",
                "This is L2 scarce lane — do hard work only; leave scutwork to local Mag",
            ],
        },
        done_so_far=[f"tools: {len(state.get('tool_trace') or [])} calls"],
        return_path=return_path,
    )
    path = HANDOFF_DIR / f"{handoff_id}.json"
    write_handoff(path, data)

    out = {
        "handoff_id": handoff_id,
        "status": "escalated",
        "last_result": f"Wrote handoff {path}",
    }

    # Live tasking: when the Grok open harness (CLI) is installed, run the
    # handoff headless NOW instead of only parking a file for the operator.
    # Disable per-run with env MAG_ESCALATE_HARNESS=0.
    harness = None
    if os.environ.get("MAG_ESCALATE_HARNESS", "1").strip() not in ("0", "false", "no"):
        try:
            from harness.grok_cli import escalate_via_harness, harness_available

            if harness_available():
                hres = escalate_via_harness(
                    goal=state.get("goal") or "",
                    context=brief[:12000] or "",
                    cwd=ROOT,
                    max_turns=12,
                    handoff_id=handoff_id,
                    timeout=600,
                )
                harness = {
                    "ok": bool(hres.get("ok")),
                    "summary": (hres.get("summary") or "")[:600],
                    "result_path": hres.get("result_path"),
                    "error": (hres.get("error") or "")[:300] or None,
                    "exit_code": hres.get("exit_code"),
                }
                if hres.get("ok"):
                    out["status"] = "escalated_grok_ran"
                    out["last_result"] = (
                        "Grok harness ran: " + (harness["summary"] or "done")
                    )
                else:
                    out["last_result"] = (
                        "Wrote handoff (grok harness unavailable/failed): "
                        + (harness["error"] or "unknown")
                    )
        except Exception as e:  # harness must never break the handoff path
            harness = {"ok": False, "error": str(e)[:300]}

    out["grok_harness"] = harness
    log_event(
        {
            "node": "escalate_grok",
            "handoff_id": handoff_id,
            "path": str(path),
            "harness": harness,
        }
    )
    sync_current({**state, **out})
    return out
