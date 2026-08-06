"""Voice turn POC tests."""
from __future__ import annotations

import json
from unittest.mock import patch

from mag import voice_turn as vt


def test_handle_voice_turn_empty():
    out = vt.handle_voice_turn({})
    assert out["ok"] is False
    assert "empty" in out["error"].lower()


def test_handle_voice_turn_deepseek_default(tmp_path, monkeypatch):
    trail = tmp_path / "voice_trail.jsonl"
    monkeypatch.setattr(vt, "TRAIL_PATH", trail)
    fake = {
        "ok": True,
        "text": "Mag is running. Your desk is healthy.",
        "model": "deepseek-chat",
        "usage": {"prompt_tokens": 10, "completion_tokens": 12},
    }

    with patch("models.providers.chat_provider", return_value=fake):
        with patch("mag.voice_turn._voice_context", return_value="Pulse: ok"):
            out = vt.handle_voice_turn({"text": "how is mag", "session_id": "voice-test"})

    assert out["ok"] is True
    assert out["seat"] == "deepseek"
    assert out["route"] == "frontier"
    assert "Mag" in out["answer"]
    assert trail.is_file()


def test_handle_voice_turn_local_seat(tmp_path, monkeypatch):
    trail = tmp_path / "voice_trail.jsonl"
    monkeypatch.setattr(vt, "TRAIL_PATH", trail)
    fake = {"ok": True, "answer": "Local answer.", "used_llm": True}

    with patch("mag.ask.ask", return_value=fake):
        out = vt.handle_voice_turn({"text": "hello", "seat": "local"})

    assert out["ok"] is True
    assert out["seat"] == "local"
    assert out["route"] == "janitor"
