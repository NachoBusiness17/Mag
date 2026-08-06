"""Tests for desk orchestrator."""
from __future__ import annotations

import mag.desk_orchestrator as dor


def test_orchestrate_empty_question():
    out = dor.orchestrate("")
    assert out["ok"] is False


def test_orchestrate_calls_chat(monkeypatch):
    monkeypatch.setattr(
        dor,
        "read_desk",
        lambda: {"text": "canvas note"},
    )
    monkeypatch.setattr(
        dor,
        "peer_lane_excerpt",
        lambda *a, **k: "[user] hello",
    )
    monkeypatch.setattr(
        "models.registry.model_for",
        lambda role: "gemma:2b",
    )

    def fake_chat(role, system, user, temperature=0.2):
        assert role == "orchestrator"
        assert "canvas note" in user
        assert "hello" in user
        return "### TL;DR\nok"

    monkeypatch.setattr("llm.chat", fake_chat)
    out = dor.orchestrate("what should I do?")
    assert out["ok"] is True
    assert "TL;DR" in out["answer"]
    assert out["model"] == "gemma:2b"
