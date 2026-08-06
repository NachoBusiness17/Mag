"""Tests for desk agent response timing helpers."""
from __future__ import annotations

import mag.desk_timing as dt


def test_estimate_tokens():
    assert dt.estimate_tokens("hello world") == 2
    assert dt.fill_token_estimates(timing={"speaker": "local", "elapsed_ms": 1}, prompt_text="abcd", completion_text="efgh")[
        "tokens_in"
    ] == 1


def test_extract_ollama_tokens():
    tin, tout = dt.extract_ollama_tokens({"prompt_eval_count": 42, "eval_count": 17})
    assert tin == 42
    assert tout == 17
    assert dt.extract_ollama_tokens({}) == (None, None)


def test_extract_provider_tokens():
    tin, tout = dt.extract_provider_tokens({"prompt_tokens": 100, "completion_tokens": 50})
    assert tin == 100
    assert tout == 50
    tin, tout = dt.extract_provider_tokens({"input_tokens": 10, "output_tokens": 5})
    assert tin == 10
    assert tout == 5


def test_format_timing_badge():
    badge = dt.format_timing_badge(
        {"speaker": "local", "elapsed_ms": 2300, "tokens_in": 80, "tokens_out": 62}
    )
    assert badge == "Local 2.3s · 142 tok"


def test_record_and_last_by_speaker():
    dt.reset_timings()
    dt.record_timing(dt.make_timing(speaker="local", elapsed_ms=500, tokens_out=42, model="qwen-desk"))
    dt.record_timing(dt.make_timing(speaker="remote", elapsed_ms=1100, tokens_in=30, tokens_out=59))
    by = dt.last_by_speaker()
    assert by["local"]["elapsed_ms"] == 500
    assert by["remote"]["tokens_out"] == 59
    row = dt.format_timing_row(by)
    assert "Local 500ms · 42 tok" in row
    assert "DeepSeek 1.1s · 89 tok" in row


def test_dialogue_turn_includes_timing(tmp_path, monkeypatch):
    import mag.desk_dialogue as dd

    desk = tmp_path / "memory" / "working" / "agent_desk.md"
    desk.parent.mkdir(parents=True)
    desk.write_text("# Agent desk\n\n## Goal\nTest\n\n## Dialogue\n", encoding="utf-8")
    cursor = tmp_path / "memory" / "working" / "agent_desk_cursor.json"
    log = tmp_path / "memory" / "working" / "agent_desk_dialogue.jsonl"

    monkeypatch.setattr(dd, "ROOT", tmp_path)
    monkeypatch.setattr(dd, "CURSOR_PATH", cursor)
    monkeypatch.setattr(dd, "DIALOGUE_LOG", log)

    import mag.agent_desk as ad

    monkeypatch.setattr(ad, "ROOT", tmp_path)
    monkeypatch.setattr(ad, "DESK_PATH", desk)

    fake_text = """### Reply
Local here.

### Canvas edit
### Local - opening
Board edit.
"""
    timing = {"speaker": "local", "elapsed_ms": 120, "tokens_out": 33, "model": "qwen-desk"}

    monkeypatch.setattr(
        dd,
        "_invoke_local_llm",
        lambda **kw: (fake_text, "http", timing),
    )

    dt.reset_timings()
    dt.record_timing(timing)
    res = dd.dialogue_turn("local", operator_note="kick off", canvas=desk.read_text(encoding="utf-8"))
    assert res["ok"] is True
    assert res["timing"]["elapsed_ms"] == 120
    assert res["timing"]["tokens_out"] == 33
    assert dt.last_by_speaker()["local"]["elapsed_ms"] == 120
