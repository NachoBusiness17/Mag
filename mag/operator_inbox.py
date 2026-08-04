"""Operator inbox — deferred guidance while the agent is working.

Operator types in the dashboard guidance dock (or API), hits Enter to queue.
At the next checkpoint (between tool rounds / model calls), the seat drains
pending notes and either:
  - applies clear direction (decision matrix / operator_directives), or
  - asks Socratic clarifying questions tied to the current task.

Errors during tool loops are logged to logs/behavioral_events.jsonl for the
behavioral-analysis framework (scout mines them like decisions_log).
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import ROOT

INBOX_PATH = ROOT / "memory" / "operator_inbox.json"
EVENTS_PATH = ROOT / "logs" / "behavioral_events.jsonl"

# Vague inputs → Socratic clarify at checkpoint (not raw inject)
_VAGUE = {
    "continue", "go", "next", "fix it", "keep going", "yes", "no", "stop",
    "help", "wait", "hold on", "actually", "nevermind", "nvm",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> dict[str, Any]:
    if not INBOX_PATH.is_file():
        return {"committed": [], "processed": []}
    try:
        data = json.loads(INBOX_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"committed": [], "processed": []}
    except (json.JSONDecodeError, OSError):
        return {"committed": [], "processed": []}


def _save(data: dict[str, Any]) -> None:
    INBOX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INBOX_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def status() -> dict[str, Any]:
    data = _load()
    pending = [x for x in data.get("committed") or [] if x.get("status") == "pending"]
    return {
        "ok": True,
        "schema": "operator_inbox.v1",
        "pending": pending,
        "pending_n": len(pending),
        "processed_n": len(data.get("processed") or []),
        "path": _display_path(INBOX_PATH),
        "layman": (
            f"{len(pending)} note(s) queued — agent reads these at the next checkpoint, "
            "not mid-tool. Clear direction applies; vague notes get Socratic clarify."
        ),
    }


def pending_hints() -> list[str]:
    """Non-destructive read of queued guidance for governor / decision matrix."""
    return [
        str(x.get("text") or "").strip()
        for x in (_load().get("committed") or [])
        if x.get("status") == "pending" and str(x.get("text") or "").strip()
    ]


def commit_guidance(
    text: str,
    *,
    source: str = "dashboard",
    kind: str = "guidance",
    refine: bool = False,
    path: str | None = None,
) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        return {"ok": False, "error": "empty guidance"}
    data = _load()
    item = {
        "id": f"inbox-{datetime.now(timezone.utc).strftime('%H%M%S')}",
        "text": text[:4000],
        "source": source,
        "kind": kind,
        "refine": bool(refine),
        "path": path,
        "status": "pending",
        "ts": _now(),
    }
    committed = list(data.get("committed") or [])
    committed.append(item)
    data["committed"] = committed[-50:]
    _save(data)
    return {"ok": True, "item": item, "pending_n": sum(1 for x in committed if x.get("status") == "pending")}


def clear_pending() -> dict[str, Any]:
    data = _load()
    kept = [x for x in data.get("committed") or [] if x.get("status") != "pending"]
    data["committed"] = kept
    _save(data)
    return {"ok": True, "cleared": True}


def _is_ambiguous(text: str) -> bool:
    low = text.strip().lower().rstrip(".!?")
    if low in _VAGUE:
        return True
    if len(text.strip()) < 12:
        return True
    if "?" in text and len(text) < 80:
        return True
    # lacks a verb/object heuristic
    if not re.search(r"\b(focus|stop|use|fix|build|wire|add|remove|read|write|skip|ignore|priorit)\w*", low):
        if len(text) < 40:
            return True
    return False


def _socratic_questions(guidance: str, task: str) -> list[str]:
    g = guidance.strip()[:200]
    t = (task or "current work")[:120]
    return [
        f"How does this guidance relate to your active task ({t})?",
        f"What is the single concrete next action implied by: «{g}»?",
        "Does this override the blueprint, or refine how you execute the current step?",
        "What would 'done' look like after applying this note?",
    ]


def _current_task_hint() -> str:
    # Authoritative first: state/CURRENT.md is the live resume contract the seat
    # writes as a byproduct of its tool loop (see mag.agent_cli._sync_current).
    # Reading its ## Goal field kills the guess-by-scanning-prose thrash.
    current = ROOT / "state" / "CURRENT.md"
    if current.is_file():
        try:
            in_goal = False
            for line in current.read_text(encoding="utf-8", errors="replace").splitlines():
                s = line.strip()
                if s.startswith("## Goal"):
                    in_goal = True
                    continue
                if in_goal:
                    if s.startswith("## "):
                        break
                    if s:
                        return s[:160]
        except OSError:
            pass
    # Fallback: prose-scan only if the live contract is absent.
    for path in (
        ROOT / "memory" / "working.md",
        ROOT / "memory" / "agent_state" / "LATEST.md",
    ):
        if path.is_file():
            try:
                for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                    s = line.strip()
                    if s.startswith("- ") and len(s) > 10:
                        return s[:160]
            except OSError:
                pass
    return "active agent turn"


def drain_pending_at_checkpoint(*, task_hint: str = "") -> list[dict[str, Any]]:
    """Drain pending inbox items into actions for the agent loop."""
    from mag.compass import record_decision

    data = _load()
    task = task_hint or _current_task_hint()
    actions: list[dict[str, Any]] = []
    processed = list(data.get("processed") or [])
    committed = list(data.get("committed") or [])

    for item in committed:
        if item.get("status") != "pending":
            continue
        text = str(item.get("text") or "").strip()
        if not text:
            item["status"] = "skipped"
            continue
        ambiguous = _is_ambiguous(text)
        if ambiguous:
            questions = _socratic_questions(text, task)
            actions.append({
                "action": "socratic",
                "id": item.get("id"),
                "text": text,
                "questions": questions,
                "task_hint": task,
            })
            record_decision(
                "operator inbox checkpoint",
                text,
                "socratic clarify — ambiguous queued guidance",
            )
        else:
            actions.append({
                "action": "apply",
                "id": item.get("id"),
                "text": text,
                "task_hint": task,
                "kind": item.get("kind") or "guidance",
                "refine": bool(item.get("refine")),
                "path": item.get("path"),
            })
            record_decision(
                "operator breadcrumb checkpoint",
                text,
                "applied queued breadcrumb — incorporate without breaking stride",
            )
            if item.get("refine"):
                try:
                    from mag.orchestrator import enqueue

                    goal = f"[refine breadcrumb] {text[:500]}"
                    rec = enqueue(goal, provider="deepseek", tag="breadcrumb-refine")
                    actions.append({
                        "action": "refine_spawn",
                        "id": item.get("id"),
                        "queue_id": rec.get("queue_id"),
                        "goal": goal[:200],
                    })
                except Exception as e:
                    actions.append({
                        "action": "refine_failed",
                        "id": item.get("id"),
                        "error": str(e)[:120],
                    })
        item["status"] = "processed"
        item["processed_at"] = _now()
        processed.append({**item, "action": "socratic" if ambiguous else "apply"})
    data["committed"] = committed
    data["processed"] = processed[-100:]
    _save(data)
    return actions


def log_behavioral_event(
    *,
    kind: str,
    detail: str,
    tool: str | None = None,
    error: str | None = None,
    phase: str | None = None,
    session_id: str | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> None:
    """Feed the overseeing / improve pipeline with seat errors.

    session_id/provider/model identify the seat that produced the event so
    the behavioral-analysis pipeline can attribute failures to a run.
    """
    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": _now(),
        "kind": kind,
        "detail": (detail or "")[:500],
        "tool": tool,
        "error": (error or "")[:300] if error else None,
        "phase": phase,
        "session_id": session_id,
        "provider": provider,
        "model": model,
    }
    try:
        with EVENTS_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass
    # Mirror high-signal failures into decisions log for compass case law
    if kind in ("tool_fail", "collapse", "degenerate", "seat_crash"):
        try:
            from mag.compass import record_decision

            record_decision(
                f"behavioral {kind}",
                detail[:200],
                f"logged {EVENTS_PATH.name} — remedy/candidate pipeline may rank",
            )
        except Exception:
            pass


def apply_actions_to_messages(
    messages: list[dict[str, Any]], actions: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Inject drained inbox actions into the conversation."""
    out = list(messages)
    for a in actions:
        if a.get("action") == "apply":
            text = a.get("text") or ""
            kind = a.get("kind") or "guidance"
            label = "BREADCRUMB" if kind == "breadcrumb" else "GUIDANCE"
            refine_note = ""
            if a.get("refine"):
                refine_note = (
                    "\nA refine sub-agent was queued on the orchestrator to develop this idea — "
                    "fold its output if useful."
                )
            out.append({
                "role": "user",
                "content": (
                    f"[OPERATOR {label} — dropped on your path, not mid-tool]\n{text}\n\n"
                    "Incorporate into your current line of work: search, riff, or adjust plan — "
                    "do not restart from scratch unless the note demands it. "
                    "Apply per operator_directives (memory/operator_directives.md)."
                    f"{refine_note}"
                ),
            })
        elif a.get("action") == "socratic":
            qs = a.get("questions") or []
            qblock = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(qs))
            out.append({
                "role": "user",
                "content": (
                    f"[OPERATOR GUIDANCE — queued, needs clarify]\n{a.get('text')}\n\n"
                    f"Current task context: {a.get('task_hint')}\n\n"
                    "Answer these briefly in one paragraph, then continue autonomously:\n"
                    f"{qblock}"
                ),
            })
    return out
