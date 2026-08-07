"""Voice turn — cast / mobile STT text → DeepSeek answer (fast enough for speech).

Schema: mag_voice_turn.v1 — see docs/ref/MAG_MOBILE_VOICE_SPEC.md
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from config import ROOT

SCHEMA = "mag_voice_turn.v1"
TRAIL_PATH = ROOT / "memory" / "runs" / "voice_trail.jsonl"

VOICE_SYSTEM = """You are Mag — the operator's home agent on voice mode.
Reply in 1-3 short sentences suitable for text-to-speech.
No markdown, no bullet lists, no code blocks unless explicitly asked.
Be direct, warm, and conversational."""


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _voice_seat(body: dict[str, Any]) -> str:
    raw = str(body.get("seat") or os.environ.get("MAG_VOICE_SEAT") or "deepseek").strip().lower()
    if raw in ("local", "ollama", "janitor"):
        return "local"
    return "deepseek"


def _voice_context() -> str:
    try:
        from mag.display import build_display_payload

        d = build_display_payload()
        parts: list[str] = []
        if d.get("headline"):
            parts.append(f"Pulse: {d['headline']}")
        desk = d.get("desk") or {}
        if desk.get("goal"):
            parts.append(f"Desk goal: {desk['goal']}")
        tail = desk.get("dialogue_tail") or []
        if tail:
            parts.append(f"Recent desk: {' · '.join(str(x) for x in tail[-2:])}")
        return "\n".join(parts)
    except Exception:
        return ""


def _append_trail(row: dict[str, Any]) -> None:
    TRAIL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TRAIL_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, default=str) + "\n")


def _answer_deepseek(transcript: str, *, session_id: str) -> dict[str, Any]:
    ctx = _voice_context()
    user = f"{ctx}\n\nOperator said: {transcript}" if ctx else transcript
    try:
        from mag.desk_timing import Timer, extract_provider_tokens, make_timing
        from models.providers import chat_provider

        timer = Timer()
        res = chat_provider(
            "deepseek",
            VOICE_SYSTEM,
            user,
            tier="T2",
            max_tokens=280,
            temperature=0.35,
        )
        if not res.get("ok"):
            return {
                "ok": False,
                "error": str(res.get("error") or "deepseek failed"),
                "seat": "deepseek",
                "route": "frontier",
            }
        answer = str(res.get("text") or res.get("content") or "").strip()
        model = res.get("model")
        tin, tout = extract_provider_tokens(res.get("usage"))
        timing = make_timing(
            speaker="voice",
            elapsed_ms=timer.elapsed_ms(),
            tokens_in=tin,
            tokens_out=tout,
            model=str(model) if model else None,
            provider="deepseek",
        )
        return {
            "ok": bool(answer),
            "answer": answer,
            "seat": "deepseek",
            "route": "frontier",
            "provider": "deepseek",
            "model": model,
            "used_llm": True,
            "timing": timing,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200], "seat": "deepseek", "route": "frontier"}


def _answer_local(transcript: str, *, session_id: str) -> dict[str, Any]:
    from mag.ask import ask

    result = ask(transcript, session_id=session_id, use_llm=True, speak=False)
    return {
        "ok": bool(result.get("ok")),
        "answer": str(result.get("answer") or result.get("error") or "").strip(),
        "seat": "local",
        "route": "janitor",
        "provider": "local",
        "used_llm": bool(result.get("used_llm")),
        "not_in_store": bool(result.get("not_in_store")),
    }


def handle_voice_turn(body: dict[str, Any] | None) -> dict[str, Any]:
    body = body or {}
    text = str(body.get("text") or body.get("transcript") or "").strip()
    session_id = str(body.get("session_id") or "").strip() or f"voice-{uuid4().hex[:10]}"
    seat = _voice_seat(body)

    if not text:
        return {"ok": False, "schema": SCHEMA, "error": "empty transcript — pass text"}

    if seat == "local":
        result = _answer_local(text, session_id=session_id)
    else:
        result = _answer_deepseek(text, session_id=session_id)
        if not result.get("ok") and os.environ.get("MAG_VOICE_FALLBACK_LOCAL", "").lower() in (
            "1",
            "true",
            "yes",
        ):
            result = _answer_local(text, session_id=session_id)
            result["fallback"] = "local"

    answer = str(result.get("answer") or result.get("error") or "").strip()
    out: dict[str, Any] = {
        "ok": bool(result.get("ok")),
        "schema": SCHEMA,
        "session_id": session_id,
        "transcript": text,
        "answer": answer,
        "seat": result.get("seat", seat),
        "route": result.get("route", "frontier" if seat == "deepseek" else "janitor"),
        "speak": True,
        "provider": result.get("provider"),
        "model": result.get("model"),
        "used_llm": bool(result.get("used_llm")),
        "timing": result.get("timing"),
    }
    if result.get("fallback"):
        out["fallback"] = result["fallback"]
    if result.get("not_in_store") is not None:
        out["not_in_store"] = result.get("not_in_store")
    if not out["ok"]:
        out["error"] = result.get("error") or "voice turn failed"

    try:
        from mag.training_events import emit

        emit(
            "voice_turn",
            join={"session_id": session_id, "seat": out["seat"]},
            input_data={"transcript": text[:500], "channel": body.get("channel") or "cast"},
            action={"route": out["route"], "seat": out["seat"], "provider": out.get("provider")},
            outcome={"ok": out["ok"], "answer_chars": len(answer)},
            pattern_tags=["cast", "voice_poc", out["seat"]],
            tier_max="T2",
        )
    except Exception:
        pass

    _append_trail(
        {
            "ts": _utc(),
            "session_id": session_id,
            "transcript": text[:500],
            "answer": answer[:800],
            "ok": out["ok"],
            "seat": out["seat"],
            "channel": body.get("channel") or "cast",
        }
    )
    return out
