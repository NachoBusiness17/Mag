"""Distributed surface glue — multi-device viewport on home soil.

Commitment: distributed-surface-glue-001
Plan: docs/ref/DISTRIBUTED_SURFACE.md

Writes use the existing Mag scheme — no parallel todo throne:
  - goals/tasks  → queue/todo.md  ([mag] lines, governor-visible)
  - FILE blocks  → memory/working.md append (open loops / residual heat)
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import ROOT, bind_host

CONFIG_PATH = ROOT / "configs" / "distributed_surface.yaml"
TODO_PATH = ROOT / "queue" / "todo.md"


def _load_yaml() -> dict[str, Any]:
    if not CONFIG_PATH.is_file():
        return {}
    try:
        import yaml  # type: ignore

        return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def phase() -> str:
    return str(_load_yaml().get("phase") or "G0")


def todo_path() -> Path:
    cfg = _load_yaml()
    rel = ((cfg.get("paths") or {}).get("todo") or "queue/todo.md")
    return ROOT / rel


def working_path() -> Path:
    cfg = _load_yaml()
    rel = ((cfg.get("paths") or {}).get("working") or "memory/working.md")
    return ROOT / rel


def max_handoff_chars() -> int:
    cfg = _load_yaml()
    try:
        return int((cfg.get("handoff") or {}).get("max_chars") or 24000)
    except (TypeError, ValueError):
        return 24000


def _slug(s: str, n: int = 24) -> str:
    out = re.sub(r"[^a-zA-Z0-9]+", "-", (s or "device").strip().lower()).strip("-")
    return (out[:n] or "device").rstrip("-")


def _extract_next_move(body: str) -> str | None:
    """Pull 'next move' from a FILE block if present."""
    for line in body.splitlines():
        low = line.strip().lower()
        if low.startswith("- next move:") or low.startswith("next move:"):
            return line.split(":", 1)[-1].strip()[:240]
    return None


def _looks_like_file_block(body: str) -> bool:
    low = body.lower()
    if "file for mag" in low:
        return True
    if body.count("\n") >= 2 and any(
        ln.strip().startswith("- ") for ln in body.splitlines() if ln.strip()
    ):
        return True
    return False


def _append_todo(line: str, *, marker: str = "mag") -> Path:
    path = todo_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = f"- [ ] [{marker}] {line.strip()}\n"
    if path.is_file():
        existing = path.read_text(encoding="utf-8")
        if entry.strip() in existing:
            return path
        path.write_text(existing.rstrip() + "\n" + entry, encoding="utf-8")
    else:
        path.write_text(f"# Todo\n\n{entry}", encoding="utf-8")
    return path


def _append_working(body: str, *, source: str, device: str) -> Path:
    path = working_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    block = f"\n\n## Remote FILE · {ts} · {source}/{device}\n\n{body.strip()}\n"
    if path.is_file():
        path.write_text(path.read_text(encoding="utf-8").rstrip() + block, encoding="utf-8")
    else:
        path.write_text(f"# Working\n{block}", encoding="utf-8")
    return path


def ingest_file_block(
    text: str,
    *,
    source: str = "unknown",
    device: str = "unknown",
    kind: str = "auto",
) -> dict[str, Any]:
    """Route remote input into queue/todo.md and/or memory/working.md."""
    body = (text or "").strip()
    if not body:
        return {"ok": False, "error": "empty text"}
    if len(body) > max_handoff_chars():
        return {"ok": False, "error": f"text exceeds {max_handoff_chars()} chars"}

    tag = f"[{_slug(device)}]"
    k = (kind or "auto").strip().lower()
    wrote: list[str] = []

    if k == "todo" or (k == "auto" and not _looks_like_file_block(body) and "\n" not in body):
        path = _append_todo(f"{tag} {body}")
        wrote.append(str(path.relative_to(ROOT)).replace("\\", "/"))
        return {
            "ok": True,
            "routed": "todo",
            "paths": wrote,
            "bytes": len(body),
            "source": source,
            "device": device,
        }

    wpath = _append_working(body, source=source, device=device)
    wrote.append(str(wpath.relative_to(ROOT)).replace("\\", "/"))

    nxt = _extract_next_move(body)
    if nxt:
        tpath = _append_todo(f"{tag} {nxt}")
        wrote.append(str(tpath.relative_to(ROOT)).replace("\\", "/"))

    return {
        "ok": True,
        "routed": "file+todo" if nxt else "working",
        "paths": wrote,
        "bytes": len(body),
        "source": source,
        "device": device,
    }


def _todo_open_preview(limit: int = 5) -> list[str]:
    path = todo_path()
    if not path.is_file():
        return []
    return [
        ln.strip()
        for ln in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if ln.strip().startswith("- [ ]")
    ][:limit]


def surface_status() -> dict[str, Any]:
    """Status for GET /api/v1/surface — phase, bind hints, canonical paths."""
    import os

    cfg = _load_yaml()
    remote = cfg.get("remote") or {}
    port = int(remote.get("port") or 8765)
    host = bind_host(str(remote.get("bind_host") or "127.0.0.1"))
    public = (os.environ.get("MAG_PUBLIC_URL") or remote.get("public_url") or "").strip()
    return {
        "ok": True,
        "commitment": "distributed-surface-glue-001",
        "phase": phase(),
        "plan": "docs/ref/DISTRIBUTED_SURFACE.md",
        "runbook": "memory/handoff/HOME_MACHINE.md",
        "bind": {"host": host, "port": port},
        "public_url": public or None,
        "paths": {
            "todo": str(todo_path().relative_to(ROOT)).replace("\\", "/"),
            "working": str(working_path().relative_to(ROOT)).replace("\\", "/"),
        },
        "todo_open_preview": _todo_open_preview(),
        "auth": {
            "token_env": ((cfg.get("auth") or {}).get("token_env") or "MAG_REMOTE_TOKEN"),
            "required_on_remote_bind": bool((cfg.get("auth") or {}).get("require_token_on_remote_bind")),
        },
    }
