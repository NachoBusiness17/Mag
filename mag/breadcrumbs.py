"""Breadcrumbs — drop notes in the agent's path without breaking stride.

Operator drops a short note (or @file path) while the seat is working.
At the next checkpoint the seat absorbs it, incorporates into search/plan,
or spawns a refine sub-agent when requested.

Backed by operator_inbox.json (same queue, breadcrumb semantics in UI).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from config import ROOT

from mag import operator_inbox as inbox


def _resolve_path_drop(text: str) -> tuple[str, str | None]:
    """Expand @relative/path or file:path into text + path field."""
    raw = (text or "").strip()
    rel: str | None = None
    if raw.startswith("@"):
        rel = raw[1:].strip().split()[0]
    elif raw.lower().startswith("file:"):
        rel = raw[5:].strip().split()[0]
    else:
        return text, None
    if not rel:
        return text, None
    p = Path(rel) if Path(rel).is_absolute() else ROOT / rel
    try:
        p = p.resolve()
        p.relative_to(ROOT.resolve())
    except (ValueError, OSError):
        return f"{raw}\n\n(file outside repo or missing)", rel
    if not p.is_file():
        return f"@{rel}\n\n(file not found on disk)", rel
    try:
        body = p.read_text(encoding="utf-8", errors="replace")[:1200]
    except OSError as e:
        return f"@{rel}\n\n(read error: {e})", rel
    rel_s = str(p.relative_to(ROOT)).replace("\\", "/")
    return (
        f"Breadcrumb path: `{rel_s}`\n\n```\n{body}\n```\n\n"
        f"Incorporate if relevant to current search — riff or refine, do not restart.",
        rel_s,
    )


def drop_breadcrumb(
    text: str,
    *,
    source: str = "dashboard",
    refine: bool = False,
    path: str | None = None,
) -> dict[str, Any]:
    """Queue a breadcrumb for the next agent checkpoint."""
    expanded, auto_path = _resolve_path_drop(text)
    return inbox.commit_guidance(
        expanded,
        source=source,
        kind="breadcrumb",
        refine=bool(refine),
        path=path or auto_path,
    )


def status() -> dict[str, Any]:
    st = inbox.status()
    st["schema"] = "breadcrumbs.v1"
    st["layman"] = (
        f"{st.get('pending_n', 0)} breadcrumb(s) on the path — "
        "agent picks them up at the next checkpoint without breaking stride."
    )
    return st


def pending_hints() -> list[str]:
    return inbox.pending_hints()
