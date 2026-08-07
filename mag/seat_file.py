"""FILE any seat into residual DNA + Verkle leaf.

Commitment: seat-file-all-seats-001
Law: FIND → FILE → LOAD. Chat is heat; only filed workdays count.

Every decoder (Cursor cloud, Slack, tablet, Grok, local agent) must land as
memory/agent_sessions/<seat>.json then summarize_session → verkle leaf.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import ROOT
from mag.chat_source import (
    AGENT_BIO_PREFIX,
    agent_bio_id,
    agent_session_path,
    file_agent_session,
)

SEAT_SOURCES = frozenset(
    {
        "cursor",
        "cursor-cloud",
        "slack",
        "tablet",
        "cloud",
        "grok",
        "deepseek",
        "gemini",
        "external",
        "handoff",
    }
)


def _slug(seat: str, n: int = 48) -> str:
    out = re.sub(r"[^a-zA-Z0-9._-]+", "-", (seat or "external").strip().lower()).strip("-")
    return (out[:n] or "external").rstrip("-")


def seat_local_id(seat: str, *, source: str = "external") -> str:
    """Stable agent_sessions stem, e.g. cloud-cursor-bc123."""
    src = _slug(source, 16)
    sid = _slug(seat, 32)
    if sid.startswith(f"{src}-"):
        return sid
    return f"{src}-{sid}"


def file_block_to_messages(text: str, *, goal: str = "") -> list[dict[str, Any]]:
    """Turn a FILE block or handoff note into OpenAI-style messages for biographer."""
    body = (text or "").strip()
    if not body:
        return []
    user = (goal or "").strip()
    if not user:
        for line in body.splitlines():
            low = line.strip().lower()
            if low.startswith("- next move:") or low.startswith("next move:"):
                user = line.split(":", 1)[-1].strip()
                break
        if not user:
            user = body.splitlines()[0].strip()[:240] or "remote handoff"
    return [
        {"role": "user", "content": user},
        {"role": "assistant", "content": body},
    ]


def materialize_session(
    seat: str,
    messages: list[dict[str, Any]],
    *,
    provider: str = "external",
    source: str = "external",
    model: str | None = None,
    extra: dict[str, Any] | None = None,
) -> Path:
    """Write memory/agent_sessions/<seat>.json for biographer FILE."""
    local = seat_local_id(seat, source=source)
    path = agent_session_path(local)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "session_id": local,
        "provider": provider or source,
        "model": model,
        "source": source,
        "seat": seat,
        "messages": messages[-120:],
        "updated": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        payload["meta"] = extra
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def file_seat(
    seat: str,
    *,
    messages: list[dict[str, Any]] | None = None,
    file_block: str = "",
    goal: str = "",
    provider: str = "external",
    source: str = "external",
    model: str | None = None,
    use_llm: bool = False,
    force: bool = True,
    amend: bool = True,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Materialize agent session + FILE Verkle workday bead."""
    msgs = list(messages or [])
    if not msgs and file_block:
        msgs = file_block_to_messages(file_block, goal=goal)
    if not msgs:
        return {"ok": False, "error": "no messages or file_block"}

    local = seat_local_id(seat, source=source)
    path = materialize_session(
        seat,
        msgs,
        provider=provider,
        source=source,
        model=model,
        extra=extra,
    )
    res = file_agent_session(
        local,
        use_llm=use_llm,
        force=force,
        amend=amend,
    )
    res["local_session_id"] = local
    res["bio_session_id"] = agent_bio_id(local)
    res["session_path"] = str(path.relative_to(ROOT)).replace("\\", "/")
    res["seat"] = seat
    res["seat_source"] = source
    return res


def file_handoff(
    text: str,
    *,
    source: str = "handoff",
    device: str = "unknown",
    goal: str = "",
    use_llm: bool = False,
    force: bool = True,
) -> dict[str, Any]:
    """FILE a remote FILE block as a Verkle workday (after todo/working routing)."""
    seat = f"{source}-{_slug(device)}"
    return file_seat(
        seat,
        file_block=text,
        goal=goal,
        provider=source,
        source=source,
        use_llm=use_llm,
        force=force,
        extra={"device": device, "via": "handoff"},
    )
