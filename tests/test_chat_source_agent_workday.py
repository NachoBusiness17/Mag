"""Seat-agnostic chat source: Mag agent sessions FILE as Verkle workdays."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from config import ROOT
from mag.chat_source import (
    AGENT_BIO_PREFIX,
    agent_bio_id,
    extract_turns,
    extract_turns_from_messages,
    file_agent_session,
    resolve_chat,
)


def test_agent_bio_id_stable():
    assert agent_bio_id("dashboard") == f"{AGENT_BIO_PREFIX}dashboard"
    assert agent_bio_id(f"{AGENT_BIO_PREFIX}dashboard") == f"{AGENT_BIO_PREFIX}dashboard"


def test_extract_agent_messages_skips_system():
    msgs = [
        {"role": "system", "content": "huge pack should not become operator prompt"},
        {"role": "user", "content": "file this workday bead"},
        {
            "role": "assistant",
            "content": "on it",
            "tool_calls": [
                {
                    "id": "c1",
                    "type": "function",
                    "function": {"name": "run_shell", "arguments": '{"command":"echo hi"}'},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "c1", "content": '{"ok":true}'},
        {"role": "assistant", "content": "done — residual path ready"},
    ]
    turns = extract_turns_from_messages(msgs)
    assert turns["source"] == "mag_agent"
    assert "file this workday bead" in turns["user"]
    assert not any("huge pack" in u for u in turns["user"])
    assert any("run_shell" in t for t in turns["tools"])
    assert any("done" in a for a in turns["assistant"])


def test_resolve_and_file_agent_session(tmp_path, monkeypatch):
    # Point agent dir at temp under real ROOT structure is hard; use real agent_sessions
    # with a disposable seat id.
    seat = "_pytest_agent_wd"
    from mag.chat_source import agent_session_path

    path = agent_session_path(seat)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "session_id": seat,
        "provider": "ollama",
        "model": "gemma:2b",
        "updated": "2026-08-02T18:00:00+00:00",
        "messages": [
            {"role": "system", "content": "law pack"},
            {"role": "user", "content": "pytest: wire agent chats into verkle workdays"},
            {
                "role": "assistant",
                "content": "Filing residual DNA and appending a Verkle leaf.",
            },
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    try:
        ref = resolve_chat(seat, source="mag_agent")
        assert ref is not None
        assert ref.source == "mag_agent"
        assert ref.session_id == agent_bio_id(seat)
        assert ref.path == path

        turns = extract_turns(path)
        assert "pytest: wire agent" in (turns.get("user") or [""])[0]

        res = file_agent_session(seat, use_llm=False, force=True, amend=True)
        assert res.get("ok"), res
        bio = res.get("bio_session_id") or res.get("session_id")
        assert bio == agent_bio_id(seat)
        residual = ROOT / "memory" / "biography" / "residual" / f"{bio}.json"
        assert residual.is_file(), f"missing residual {residual}"
        dossier = json.loads(residual.read_text(encoding="utf-8"))
        assert dossier.get("session_id") == bio
        seat = dossier.get("seat") or {}
        assert seat.get("source") == "mag_agent"
        assert seat.get("agnostic") is True
        assert "pytest" in str(dossier.get("tldr") or "").lower()
    finally:
        if path.is_file():
            path.unlink()
