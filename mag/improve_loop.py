"""Cloud handoff + unified improve cycle — feeds behavioral, nervous, spider, queue.

Cloud agents file handoff JSON on disk; local cycle ingests, queues, emits training
events, refreshes nervous glance, and runs spider tick.

CLI: python main.py improve-loop cycle|cloud-handoff|ingest
REST: POST /api/v1/improve/cloud · POST /api/v1/improve/cycle
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import ROOT

HANDOFF_DIR = ROOT / "queue" / "handoff"
CLOUD_PREFIX = "cloud-"
TRAIL = ROOT / "memory" / "runs" / "improve_loop_trail.jsonl"
SCHEMA = "improve_loop.v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _trail(event: str, **fields: Any) -> None:
    TRAIL.parent.mkdir(parents=True, exist_ok=True)
    row = {"ts": _now(), "event": event, **fields}
    with TRAIL.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def write_cloud_handoff(
    *,
    goal: str = "",
    claim: str = "",
    brief: str = "",
    source: str = "cursor-cloud",
    depth: str = "simple_code",
    enqueue: bool = False,
    run_id: str | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """File a cloud-agent outcome for local improve loop ingestion."""
    goal = (goal or claim or brief or "").strip()
    if not goal:
        return {"ok": False, "error": "goal, claim, or brief required"}

    HANDOFF_DIR.mkdir(parents=True, exist_ok=True)
    rid = run_id or uuid.uuid4().hex[:10]
    path = HANDOFF_DIR / f"{CLOUD_PREFIX}{rid}.json"
    if claim and not goal.startswith("[improve]"):
        goal = f"[improve] {claim.strip()}"

    payload: dict[str, Any] = {
        "schema": "cloud_handoff.v1",
        "run_id": rid,
        "ts": _now(),
        "source": source,
        "goal": goal[:500],
        "claim": (claim or goal)[:300],
        "brief": (brief or "")[:2000],
        "depth": depth,
        "parent": "cloud",
        "meta": meta or {},
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    _trail("cloud_handoff", path=path.name, goal=goal[:120], source=source)

    try:
        from mag.operator_inbox import log_behavioral_event

        log_behavioral_event(
            kind="cloud_handoff",
            detail=goal[:300],
            session_id=source,
            provider="cloud",
            phase="filed",
        )
    except Exception:
        pass

    out: dict[str, Any] = {"ok": True, "path": str(path), "run_id": rid, "goal": goal}
    if enqueue:
        out["cycle"] = run_improve_cycle(source="cloud", drain_one=True)
    return out


def ingest_cloud_handoffs(*, limit: int = 10) -> list[dict[str, Any]]:
    """List unprocessed cloud handoffs (newest first)."""
    if not HANDOFF_DIR.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for p in sorted(HANDOFF_DIR.glob(f"{CLOUD_PREFIX}*.json"), reverse=True)[:limit]:
        try:
            h = json.loads(p.read_text(encoding="utf-8"))
            h["_path"] = p.name
            rows.append(h)
        except Exception:
            continue
    return rows


def run_improve_cycle(
    *,
    source: str = "local",
    max_improve: int = 2,
    drain_one: bool = False,
    spider_inject: bool = False,
    scout: bool = False,
) -> dict[str, Any]:
    """One improve cycle — behavioral + queue + nervous + spider + training events."""
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "ts": _now(),
        "source": source,
        "ok": True,
    }

    if scout:
        try:
            from mag.improve import scout as improve_scout

            report["scout"] = improve_scout(dry=False)
        except Exception as exc:
            report["scout_error"] = str(exc)[:200]

    handoffs = ingest_cloud_handoffs(limit=5)
    report["cloud_handoffs_pending"] = len(handoffs)

    try:
        from mag.governor_autorun import fill_queue

        filled = fill_queue(max_improve=max_improve, max_handoff=3)
        report["fill"] = {
            "improve": len(filled.get("improve") or []),
            "handoff": len(filled.get("handoff") or []),
            "skipped": len(filled.get("skipped") or []),
            "detail": filled,
        }
    except Exception as exc:
        report["fill_error"] = str(exc)[:200]
        report["ok"] = False

    if drain_one:
        try:
            from mag.orchestrator import drain_once

            report["drain"] = drain_once()
        except Exception as exc:
            report["drain_error"] = str(exc)[:200]

    try:
        from mag.operator_inbox import log_behavioral_event

        n_imp = (report.get("fill") or {}).get("improve", 0)
        log_behavioral_event(
            kind="improve_cycle",
            detail=f"source={source} improve_queued={n_imp} handoffs={len(handoffs)}",
            provider=source,
            phase="cycle",
        )
    except Exception:
        pass

    try:
        from mag.training_events import emit

        emit(
            "autorun_cycle",
            input_data={"source": source, "cloud_handoffs": len(handoffs)},
            action={"max_improve": max_improve, "drain_one": drain_one},
            outcome={
                "improve_queued": (report.get("fill") or {}).get("improve", 0),
                "handoff_queued": (report.get("fill") or {}).get("handoff", 0),
            },
            pattern_tags=["improve_loop", f"source_{source}"],
        )
    except Exception:
        pass

    try:
        from mag.spider import tick

        report["spider"] = tick(dry=False, inject=spider_inject)
    except Exception as exc:
        report["spider_error"] = str(exc)[:200]

    try:
        from mag.nervous_system import build_glance

        report["nervous"] = {
            "ok": build_glance(write=True).get("ok"),
            "integral_ok": build_glance(write=False).get("integral_ok"),
        }
    except Exception as exc:
        report["nervous_error"] = str(exc)[:200]

    _trail("cycle", source=source, report_summary={
        k: report.get(k) for k in ("fill", "drain", "spider", "nervous", "cloud_handoffs_pending")
    })
    return report


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    ap = argparse.ArgumentParser(prog="improve-loop")
    sub = ap.add_subparsers(dest="cmd")

    pc = sub.add_parser("cycle", help="Run one improve cycle (queue + nervous + spider)")
    pc.add_argument("--source", default="local")
    pc.add_argument("--max-improve", type=int, default=2)
    pc.add_argument("--drain", action="store_true")
    pc.add_argument("--scout", action="store_true")
    pc.add_argument("--spider-inject", action="store_true")
    pc.add_argument("--json", action="store_true")

    ph = sub.add_parser("cloud-handoff", help="File cloud agent handoff JSON")
    ph.add_argument("--goal", default="")
    ph.add_argument("--claim", default="")
    ph.add_argument("--brief", default="")
    ph.add_argument("--source", default="cursor-cloud")
    ph.add_argument("--enqueue", action="store_true")
    ph.add_argument("--json", action="store_true")

    pi = sub.add_parser("ingest", help="List pending cloud handoffs")
    pi.add_argument("--json", action="store_true")

    args = ap.parse_args(argv)
    if args.cmd == "cycle":
        res = run_improve_cycle(
            source=args.source,
            max_improve=args.max_improve,
            drain_one=bool(args.drain),
            spider_inject=bool(args.spider_inject),
            scout=bool(args.scout),
        )
        print(json.dumps(res, indent=2, default=str))
        return 0 if res.get("ok") else 1
    if args.cmd == "cloud-handoff":
        res = write_cloud_handoff(
            goal=args.goal,
            claim=args.claim,
            brief=args.brief,
            source=args.source,
            enqueue=bool(args.enqueue),
        )
        print(json.dumps(res, indent=2, default=str))
        return 0 if res.get("ok") else 1
    if args.cmd == "ingest":
        rows = ingest_cloud_handoffs()
        print(json.dumps(rows, indent=2, default=str) if args.json else json.dumps(rows, indent=2))
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    import sys

    sys.exit(main())
