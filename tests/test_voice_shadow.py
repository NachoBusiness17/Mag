"""Voice shadow scout tests."""
from __future__ import annotations

from unittest.mock import patch

from mag import voice_shadow as vs


def test_shadow_context_empty_until_ready(tmp_path, monkeypatch):
    monkeypatch.setattr(vs, "SHADOW_DIR", tmp_path)
    sid = "sh-1"
    assert vs.shadow_context_for_local(sid) == ""
    vs.save_shadow(sid, {"status": "ready", "brief": "FACTS: SAM is Resizable BAR", "trigger": "smart access"})
    ctx = vs.shadow_context_for_local(sid)
    assert "SAM" in ctx or "Resizable" in ctx
    assert "Background scout" in ctx


def test_start_skips_phatic(tmp_path, monkeypatch):
    monkeypatch.setattr(vs, "SHADOW_DIR", tmp_path)
    out = vs.start_shadow_scout("sh-2", "thanks")
    assert out.get("status") == "skipped"


def test_start_kicks_thread(tmp_path, monkeypatch):
    monkeypatch.setattr(vs, "SHADOW_DIR", tmp_path)

    def fake_chat(*a, **k):
        return {"ok": True, "text": "FACTS: test\nREADY LINE: ready", "model": "deepseek"}

    with patch("models.providers.chat_provider", side_effect=fake_chat):
        out = vs.start_shadow_scout("sh-3", "what is AMD smart access memory")
        assert out.get("status") == "running"
        # wait briefly for daemon
        import time

        for _ in range(30):
            st = vs.shadow_status("sh-3")
            if st.get("status") in ("ready", "failed"):
                break
            time.sleep(0.05)
        st = vs.shadow_status("sh-3")
        assert st.get("status") == "ready"
        assert st.get("has_brief") is True
