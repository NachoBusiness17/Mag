"""Voice pipeline unit tests (mocked providers)."""
from __future__ import annotations

from unittest.mock import patch

from mag import voice_pipeline as vp


def test_pipeline_happy_path():
    def fake_chat(provider, system, user, **kwargs):
        if "clean up messy" in system or "clean up" in system.lower() or "INTENT" in system:
            return {"ok": True, "text": "INTENT: status\nQUESTION: how are you\nCONSTRAINTS: none", "model": "gemma:2b"}
        if "research conductor" in system or "conductor" in system:
            return {"ok": True, "text": "1) Greet\n2) Offer help", "model": "deepseek"}
        if "after a quick team" in system or "huddle" in system:
            return {"ok": True, "text": "I'm doing well. Ready when you are.", "model": "deepseek"}
        if "real person" in system or "contractions" in system:
            return {"ok": True, "text": "I'm good — what's up?", "model": "gemma:2b"}
        return {"ok": True, "text": "fallback", "model": "x"}

    with patch.object(vp, "_chat", side_effect=fake_chat):
        out = vp.run_voice_pipeline("hey how are you")
    assert out["ok"] is True
    assert out["speak_text"]
    assert out["within_budget"] is True
    assert len(out["steps"]) == 4
    assert out["steps"][0]["step"] == "local_format"
    assert out["steps"][1]["step"] == "swarm_plan"
    assert out["steps"][2]["step"] == "swarm_answer"
    assert out["steps"][3]["step"] == "local_humanize"


def test_pipeline_survives_deepseek_fail():
    def fake_chat(provider, system, user, **kwargs):
        if provider == "ollama" and "clean" in system.lower():
            return {"ok": True, "text": "INTENT: chat\nQUESTION: hi", "model": "gemma:2b"}
        if provider == "deepseek":
            return {"ok": False, "error": "down", "text": ""}
        if provider == "ollama":
            return {"ok": True, "text": "Hey — I'm here if you need me.", "model": "gemma:2b"}
        return {"ok": False, "text": ""}

    with patch.object(vp, "_chat", side_effect=fake_chat):
        out = vp.run_voice_pipeline("hello")
    assert out.get("speak_text")
    assert out["ok"] is True
