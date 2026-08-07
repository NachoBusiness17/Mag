"""Voice scratch pad tests."""
from __future__ import annotations

from unittest.mock import patch

from mag import voice_scratch as vs


def test_append_then_commit(tmp_path, monkeypatch):
    monkeypatch.setattr(vs, "PAD_DIR", tmp_path / "pads")
    sid = "scratch-test-1"
    a = vs.append_draft(sid, "hello there")
    assert a["ok"] and a["pad"]["draft"]
    b = vs.append_draft(sid, "and more")
    assert "more" in b["pad"]["draft"]
    gen = b["pad"]["generation"]

    fake = {
        "ok": True,
        "answer": "I hear you.",
        "speak_text": "I hear you.",
        "seat": "local",
        "route": "conversation",
        "history_turns": 2,
    }
    with patch("mag.voice_turn.handle_voice_turn", return_value=fake):
        out = vs.commit_and_wake(sid, force_generation=gen)
    assert out["ok"] is True
    assert out["cancelled"] is False
    assert "hear" in (out.get("answer") or "").lower()


def test_stale_commit_cancelled(tmp_path, monkeypatch):
    monkeypatch.setattr(vs, "PAD_DIR", tmp_path / "pads")
    sid = "scratch-stale"
    vs.append_draft(sid, "first")
    gen1 = vs.load_pad(sid)["generation"]
    vs.append_draft(sid, "kept talking")
    gen2 = vs.load_pad(sid)["generation"]
    assert gen2 != gen1

    with patch("mag.voice_turn.handle_voice_turn") as m:
        out = vs.commit_and_wake(sid, force_generation=gen1)
        assert out.get("cancelled") is True
        m.assert_not_called()


def test_handle_scratch_actions(tmp_path, monkeypatch):
    monkeypatch.setattr(vs, "PAD_DIR", tmp_path / "pads")
    sid = "scratch-api"
    r = vs.handle_scratch({"session_id": sid, "action": "append", "text": "hi"})
    assert r["ok"]
    r2 = vs.handle_scratch({"session_id": sid, "action": "status"})
    assert r2["pad"]["draft"]
    r3 = vs.handle_scratch({"session_id": sid, "action": "clear"})
    assert r3.get("cleared")
