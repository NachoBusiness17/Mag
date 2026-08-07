"""Voice turn conversation tests."""
from __future__ import annotations

from unittest.mock import patch

from mag import voice_turn as vt


def test_handle_voice_turn_empty():
    out = vt.handle_voice_turn({})
    assert out["ok"] is False
    assert "empty" in out["error"].lower()


def test_handle_voice_turn_auto_status_uses_local(tmp_path, monkeypatch):
    trail = tmp_path / "voice_trail.jsonl"
    sess = tmp_path / "voice_sessions"
    monkeypatch.setattr(vt, "TRAIL_PATH", trail)
    monkeypatch.setattr(vt, "SESSIONS_DIR", sess)
    fake = {
        "ok": True,
        "text": "Mag is up. Desk looks healthy.",
        "model": "gemma4",
        "usage": {"prompt_tokens": 5, "completion_tokens": 8},
    }

    with patch("models.providers.chat_provider", return_value=fake):
        with patch("mag.voice_turn._voice_context", return_value="Pulse: ok"):
            out = vt.handle_voice_turn({"text": "how is mag", "session_id": "voice-test"})

    assert out["ok"] is True
    assert out["seat"] == "local"
    assert "Mag" in out["answer"]
    assert out.get("speak_text")
    assert out.get("conversation") is True
    assert out.get("history_turns", 0) >= 2
    assert trail.is_file()


def test_conversation_remembers_prior_turn(tmp_path, monkeypatch):
    trail = tmp_path / "voice_trail.jsonl"
    sess = tmp_path / "voice_sessions"
    monkeypatch.setattr(vt, "TRAIL_PATH", trail)
    monkeypatch.setattr(vt, "SESSIONS_DIR", sess)
    calls = []

    def fake_chat(provider, system, user, **kwargs):
        calls.append(user)
        return {
            "ok": True,
            "text": "Got it, working on the desk UI." if len(calls) == 1 else "Yes, still the desk UI from before.",
            "model": "gemma4",
            "usage": {},
        }

    with patch("models.providers.chat_provider", side_effect=fake_chat):
        with patch("mag.voice_turn._voice_context", return_value=""):
            a = vt.handle_voice_turn(
                {"text": "let's work on the desk UI", "session_id": "voice-mem", "seat": "local"}
            )
            b = vt.handle_voice_turn(
                {"text": "what were we talking about", "session_id": "voice-mem", "seat": "local"}
            )

    assert a["ok"] and b["ok"]
    assert "desk UI" in calls[1] or "desk" in calls[1].lower()
    assert b["history_turns"] >= 4


def test_clear_session(tmp_path, monkeypatch):
    sess = tmp_path / "voice_sessions"
    monkeypatch.setattr(vt, "SESSIONS_DIR", sess)
    monkeypatch.setattr(vt, "TRAIL_PATH", tmp_path / "trail.jsonl")
    with patch("models.providers.chat_provider", return_value={"ok": True, "text": "hi", "usage": {}}):
        with patch("mag.voice_turn._voice_context", return_value=""):
            vt.handle_voice_turn({"text": "hello", "session_id": "voice-clr", "seat": "local"})
    out = vt.handle_voice_turn({"session_id": "voice-clr", "clear_session": True, "text": "x"})
    assert out.get("cleared") is True
    data = vt.load_session("voice-clr")
    assert data.get("turns") == []


def test_handle_voice_turn_deepseek_when_forced(tmp_path, monkeypatch):
    trail = tmp_path / "voice_trail.jsonl"
    monkeypatch.setattr(vt, "TRAIL_PATH", trail)
    monkeypatch.setattr(vt, "SESSIONS_DIR", tmp_path / "vs")
    fake = {
        "ok": True,
        "text": "Mag is running.",
        "model": "deepseek-chat",
        "usage": {"prompt_tokens": 10, "completion_tokens": 12},
    }

    with patch("models.providers.chat_provider", return_value=fake):
        with patch("mag.voice_turn._voice_context", return_value="Pulse: ok"):
            out = vt.handle_voice_turn(
                {"text": "how is mag", "session_id": "voice-test", "seat": "deepseek"}
            )

    assert out["ok"] is True
    assert out["seat"] == "deepseek"
    assert out["route"] == "frontier"


def test_handle_voice_turn_heavy_auto_deepseek(tmp_path, monkeypatch):
    trail = tmp_path / "voice_trail.jsonl"
    monkeypatch.setattr(vt, "TRAIL_PATH", trail)
    monkeypatch.setattr(vt, "SESSIONS_DIR", tmp_path / "vs")
    fake = {
        "ok": True,
        "text": "I would start by isolating the failing test.",
        "model": "deepseek-chat",
        "usage": {},
    }

    with patch("models.providers.chat_provider", return_value=fake):
        with patch("mag.voice_turn._voice_context", return_value=""):
            out = vt.handle_voice_turn(
                {
                    "text": "debug this stack trace and implement a fix",
                    "session_id": "voice-heavy",
                }
            )

    assert out["ok"] is True
    assert out["seat"] == "deepseek"


def test_tts_clip_shortens():
    long = "Sentence one. " * 80
    clip = vt._tts_clip(long, max_chars=120)
    assert len(clip) <= 120
