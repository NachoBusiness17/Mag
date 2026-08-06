"""Tests for turn-based desk dialogue (Local ↔ DeepSeek, no tools)."""
from __future__ import annotations

import json

import pytest

import mag.desk_dialogue as dd


def test_parse_sections_reply_and_canvas():
    raw = """### Reply
Hello DeepSeek — let's align on the goal.

### Canvas edit
### Local - align
We should focus on ping-pong dialogue only.
"""
    reply, canvas = dd._parse_sections(raw)
    assert "Hello DeepSeek" in reply
    assert "### Local - align" in canvas


def test_parse_sections_fallback_canvas_from_reply():
    reply, canvas = dd._parse_sections("Short reply without sections.")
    assert reply == "Short reply without sections."
    assert canvas == ""


def test_parse_sections_chess_move_becomes_canvas():
    reply, canvas = dd._parse_sections("I'll play 2. Nf3 developing the knight.", speaker="local")
    assert "Nf3" in reply
    assert "Local" in canvas and "move" in canvas


def test_looks_like_game_move():
    assert dd._looks_like_game_move("1. e4 e5")
    assert dd._looks_like_game_move("Black responds with Nc6")
    assert not dd._looks_like_game_move("hello")


def test_parse_sections_labeled_fallback_for_long_local():
    reply, canvas = dd._parse_sections("x" * 100, speaker="local")
    assert "### Local ·" in canvas


def test_dialogue_turn_local_mock(tmp_path, monkeypatch):
    desk = tmp_path / "memory" / "working" / "agent_desk.md"
    desk.parent.mkdir(parents=True)
    desk.write_text("# Agent desk\n\n## Goal\nTest ping-pong\n\n## Dialogue\n", encoding="utf-8")
    cursor = tmp_path / "memory" / "working" / "agent_desk_cursor.json"
    log = tmp_path / "memory" / "working" / "agent_desk_dialogue.jsonl"

    monkeypatch.setattr(dd, "ROOT", tmp_path)
    monkeypatch.setattr(dd, "CURSOR_PATH", cursor)
    monkeypatch.setattr(dd, "DIALOGUE_LOG", log)

    import mag.agent_desk as ad

    monkeypatch.setattr(ad, "ROOT", tmp_path)
    monkeypatch.setattr(ad, "DESK_PATH", desk)

    fake_text = """### Reply
Local here — ready to converse.

### Canvas edit
### Local - opening
Let's test the shared canvas turn-taking.
"""

    class _FakeLLM:
        def __init__(self, **kwargs):
            pass

        def invoke(self, _messages):
            return type("R", (), {"content": fake_text})()

    monkeypatch.setitem(__import__("sys").modules, "langchain_ollama", type("M", (), {"ChatOllama": _FakeLLM})())
    monkeypatch.setattr("llm._chat_http", lambda *a, **k: fake_text)
    monkeypatch.setattr(
        dd,
        "_invoke_local_llm",
        lambda **kw: (
            fake_text,
            "logged",
            {"speaker": "local", "elapsed_ms": 50, "model": "test-model", "provider": "local"},
        ),
    )

    res = dd.dialogue_turn("local", operator_note="kick off", canvas=desk.read_text(encoding="utf-8"))
    assert res["ok"] is True
    assert res["speaker"] == "local"
    assert "ready to converse" in res["reply"]
    assert "### Local - opening" in res["canvas"]
    assert res["cursor"]["holder"] == "local"
    assert cursor.is_file()
    assert res.get("timing", {}).get("elapsed_ms") == 50


def test_dialogue_turn_simulated_local_uses_real_protocol(tmp_path, monkeypatch):
    desk = tmp_path / "memory" / "working" / "agent_desk.md"
    desk.parent.mkdir(parents=True)
    desk.write_text("## Goal\nTest\n\n## Dialogue\n", encoding="utf-8")
    monkeypatch.setattr(dd, "CURSOR_PATH", tmp_path / "cursor.json")
    monkeypatch.setattr(dd, "DIALOGUE_LOG", tmp_path / "dialogue.jsonl")
    import mag.agent_desk as ad
    monkeypatch.setattr(ad, "DESK_PATH", desk)

    out = dd.dialogue_turn(
        "local",
        operator_note="output EXACTLY these 3 words with no other text: one two three",
        canvas=desk.read_text(encoding="utf-8"),
        local_mode="simulated",
    )

    assert out["ok"] is True
    assert out["reply"] == "one two three"
    assert out["provider"] == "simulated_local"
    assert out["local_mode"] == "simulated"
    assert out["cursor"]["wake_pending"] is True


def test_ping_pong_stops_on_failure(tmp_path, monkeypatch):
    desk = tmp_path / "memory" / "working" / "agent_desk.md"
    desk.parent.mkdir(parents=True)
    desk.write_text("## Goal\nx\n", encoding="utf-8")
    cursor = tmp_path / "memory" / "working" / "agent_desk_cursor.json"
    cursor.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(dd, "ROOT", tmp_path)
    monkeypatch.setattr(dd, "CURSOR_PATH", cursor)
    monkeypatch.setattr(dd, "DIALOGUE_LOG", tmp_path / "memory" / "working" / "agent_desk_dialogue.jsonl")

    calls = {"n": 0}

    def fake_turn(speaker, **kw):
        calls["n"] += 1
        if speaker == "local":
            return {
                "ok": True,
                "speaker": "local",
                "reply": "ok",
                "canvas_edit": "",
                "canvas": "## Goal\nx\n",
            }
        return {"ok": True, "speaker": "remote", "reply": "no", "canvas_edit": "", "canvas": "## Goal\nx\n"}

    monkeypatch.setattr(dd, "dialogue_turn", fake_turn)
    out = dd.ping_pong(rounds=1, canvas=desk.read_text(encoding="utf-8"))
    assert out["ok"] is True
    assert out["reason"] == "local_no_board_edit"
    assert len(out["turns"]) == 1


def test_remote_board_edit_wakes_local(tmp_path, monkeypatch):
    cursor = tmp_path / "memory" / "working" / "agent_desk_cursor.json"
    cursor.parent.mkdir(parents=True)
    cursor.write_text(
        '{"holder":"remote","turn":2,"local_wake_pending":true,"remote_asleep":true}',
        encoding="utf-8",
    )
    log = tmp_path / "memory" / "working" / "agent_desk_dialogue.jsonl"
    monkeypatch.setattr(dd, "ROOT", tmp_path)
    monkeypatch.setattr(dd, "CURSOR_PATH", cursor)
    monkeypatch.setattr(dd, "DIALOGUE_LOG", log)

    ok, reason = dd._local_may_wake(force=False, operator_note="")
    assert ok is True
    assert reason == "remote_board_edit_pending"

    blocked, _ = dd._local_may_wake(force=False, operator_note="")
    assert blocked is True


def test_parse_sections_strips_code_fence():
    raw = """### Reply
Ok.

### Canvas edit
```
### DeepSeek · agreed
One line.
```
"""
    reply, canvas = dd._parse_sections(raw)
    assert reply == "Ok."
    assert "### DeepSeek · agreed" in canvas
    assert "```" not in canvas


def test_parse_sections_heading_fallback():
    raw = """Sure.

### Local · opening
We should keep this canvas-only.
"""
    reply, canvas = dd._parse_sections(raw)
    assert "Sure" in reply
    assert "### Local · opening" in canvas


def test_read_operator_manual():
    m = dd.read_operator_manual()
    assert m["ok"] is True
    assert "Etiquette" in m["text"]
    assert "limitations" in m["text"].lower()


def test_compose_system_prompt_includes_etiquette():
    sys = dd._compose_system_prompt("local")
    assert "Required output shape" in sys or "Reply" in sys


def test_h_desk_dialogue_get_cursor():
    from dashboard.rest import h_desk_dialogue

    code, body = h_desk_dialogue({}, None)
    assert code == 200
    assert body["ok"] is True
    assert "holder" in body["cursor"]
    assert "manual" in body


def test_remote_blocked_without_board_edit(tmp_path, monkeypatch):
    monkeypatch.setattr(dd, "ROOT", tmp_path)
    monkeypatch.setattr(dd, "CURSOR_PATH", tmp_path / "memory" / "working" / "agent_desk_cursor.json")
    monkeypatch.setattr(dd, "DIALOGUE_LOG", tmp_path / "memory" / "working" / "agent_desk_dialogue.jsonl")
    dd._set_remote_state(asleep=True, wake_pending=False)
    res = dd.dialogue_turn("remote", operator_note="hello", canvas="## Goal\nx")
    assert res["ok"] is False
    assert "asleep" in res["error"].lower() or "board" in res["error"].lower()


def test_slow_wake_skips_remote_without_edit(tmp_path, monkeypatch):
    desk = tmp_path / "memory" / "working" / "agent_desk.md"
    desk.parent.mkdir(parents=True)
    desk.write_text("## Goal\nx\n", encoding="utf-8")
    monkeypatch.setattr(dd, "ROOT", tmp_path)
    monkeypatch.setattr(dd, "CURSOR_PATH", tmp_path / "memory" / "working" / "agent_desk_cursor.json")
    monkeypatch.setattr(dd, "DIALOGUE_LOG", tmp_path / "memory" / "working" / "agent_desk_dialogue.jsonl")
    import mag.agent_desk as ad

    monkeypatch.setattr(ad, "ROOT", tmp_path)
    monkeypatch.setattr(ad, "DESK_PATH", desk)

    def fake_local(*a, **k):
        return {
            "ok": True,
            "speaker": "local",
            "reply": "ok",
            "canvas_edit": "",
            "canvas": "## Goal\nx\n",
            "cursor": {"holder": "local", "turn": 1, "remote_asleep": True},
        }

    monkeypatch.setattr(dd, "dialogue_turn", fake_local)
    out = dd.slow_wake(operator_note="hi", canvas=desk.read_text(encoding="utf-8"))
    assert out["ok"] is True
    assert out["woke"] is False
    assert out["reason"] == "no_canvas_edit"
    assert out["remote"] is None


def test_echo_loop_auto_heal(tmp_path, monkeypatch):
    log = tmp_path / "memory" / "working" / "agent_desk_dialogue.jsonl"
    log.parent.mkdir(parents=True)
    cursor = tmp_path / "memory" / "working" / "agent_desk_cursor.json"
    cursor.write_text('{"holder":"local","turn":3,"last_speaker":"local"}', encoding="utf-8")
    rows = [
        {"speaker": "local", "reply": "Sure, here's the"},
        {"speaker": "local", "reply": "Sure, here's the"},
    ]
    log.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    monkeypatch.setattr(dd, "ROOT", tmp_path)
    monkeypatch.setattr(dd, "DIALOGUE_LOG", log)
    monkeypatch.setattr(dd, "CURSOR_PATH", cursor)

    assert dd._echo_loop_detected() is True
    healed = dd._maybe_auto_heal_echo()
    assert healed and healed.get("auto_healed") == "echo_loop"
    assert log.read_text(encoding="utf-8") == ""


def test_h_desk_dialogue_get_manual():
    from dashboard.rest import h_desk_dialogue

    code, body = h_desk_dialogue({"manual": "1"}, None)
    assert code == 200
    assert body["ok"] is True
    assert "Etiquette" in body["text"]


def test_post_desk_steer(tmp_path, monkeypatch):
    import mag.pigeonhole as ph

    monkeypatch.setattr(ph, "MAIL_ROOT", tmp_path / "mail")
    monkeypatch.setenv("MAG_DESK_STEERING", "1")
    out = dd.post_desk_steer("Focus on Goal only — one sentence.")
    assert out["ok"] is True
    lines = ph.drain_inbox(dd.DESK_MAILBOX_ID)
    assert any("Focus on Goal" in ln for ln in lines)


def test_post_desk_steer_disabled_by_default(monkeypatch):
    monkeypatch.delenv("MAG_DESK_STEERING", raising=False)
    out = dd.post_desk_steer("Should not queue.")
    assert out["ok"] is False
    assert "disabled" in out.get("error", "").lower()


def test_write_cursor_preserves_wake_flags(tmp_path, monkeypatch):
    cursor = tmp_path / "memory" / "working" / "agent_desk_cursor.json"
    cursor.parent.mkdir(parents=True)
    cursor.write_text(
        '{"holder":"remote","turn":2,"remote_asleep":true,"wake_pending":false,"local_wake_pending":true}',
        encoding="utf-8",
    )
    monkeypatch.setattr(dd, "CURSOR_PATH", cursor)
    out = dd.write_cursor("local", last_speaker="local")
    assert out.get("local_wake_pending") is True
    assert out.get("remote_asleep") is True


def test_meta_discuss_mock(tmp_path, monkeypatch):
    desk = tmp_path / "memory" / "working" / "agent_desk.md"
    desk.parent.mkdir(parents=True)
    desk.write_text("# Agent desk\n\n## Goal\nTest\n\n## Meta\n", encoding="utf-8")
    meta_log = tmp_path / "memory" / "working" / "agent_desk_meta_dialogue.jsonl"
    monkeypatch.setattr(dd, "ROOT", tmp_path)
    monkeypatch.setattr(dd, "META_DIALOGUE_LOG", meta_log)

    import mag.agent_desk as ad

    monkeypatch.setattr(ad, "ROOT", tmp_path)
    monkeypatch.setattr(ad, "DESK_PATH", desk)

    calls: list[str] = []

    def fake_meta(speaker, **kw):
        calls.append(speaker)
        return {
            "ok": True,
            "speaker": speaker,
            "reply": f"{speaker} ok",
            "canvas_edit": f"### DeepSeek Meta-A · test\nline\n" if speaker == "remote_meta_a" else "### DeepSeek Meta-B · test\nline\n",
            "canvas": desk.read_text(encoding="utf-8"),
        }

    monkeypatch.setattr(dd, "meta_dialogue_turn", fake_meta)
    out = dd.meta_discuss(rounds=1, canvas=desk.read_text(encoding="utf-8"))
    assert out["ok"] is True
    assert calls == ["remote_meta_a", "remote_meta_b"]
    assert "## Meta" in desk.read_text(encoding="utf-8")


def test_empty_streak_auto_heal(tmp_path, monkeypatch):
    log = tmp_path / "memory" / "working" / "agent_desk_dialogue.jsonl"
    log.parent.mkdir(parents=True)
    cursor = tmp_path / "memory" / "working" / "agent_desk_cursor.json"
    cursor.write_text('{"holder":"local","turn":2}', encoding="utf-8")
    rows = [
        {"speaker": "local", "reply": "", "canvas_edit": ""},
        {"speaker": "local", "reply": "", "canvas_edit": ""},
    ]
    log.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    monkeypatch.setattr(dd, "DIALOGUE_LOG", log)
    monkeypatch.setattr(dd, "CURSOR_PATH", cursor)
    assert dd._empty_streak_detected() is True
    healed = dd._maybe_auto_heal_echo()
    assert healed and healed.get("auto_healed") == "empty_streak"
    assert log.read_text(encoding="utf-8") == ""


def test_canvas_pollution_auto_heal(tmp_path, monkeypatch):
    desk = tmp_path / "memory" / "working" / "agent_desk.md"
    log = tmp_path / "memory" / "working" / "agent_desk_dialogue.jsonl"
    cursor = tmp_path / "memory" / "working" / "agent_desk_cursor.json"
    desk.parent.mkdir(parents=True)
    polluted = """# Agent desk

## Goal
Ship the desk loop.

## Dialogue

### DeepSeek · Proposed Goal
Same block twice.

### DeepSeek · Proposed Goal
Same block twice.

### Unknown ·
Bad header from L0.

## Local (orchestrator)

### orchestrator · stamp
Lane mirror pollution.

## Remote (DeepSeek)

### deepseek · stamp
Duplicate lane content.
"""
    desk.write_text(polluted, encoding="utf-8")
    cursor.write_text('{"holder":"remote","turn":8}', encoding="utf-8")
    log.write_text('{"speaker":"local","reply":"ok"}\n', encoding="utf-8")

    import mag.agent_desk as ad

    monkeypatch.setattr(dd, "ROOT", tmp_path)
    monkeypatch.setattr(dd, "DIALOGUE_LOG", log)
    monkeypatch.setattr(dd, "CURSOR_PATH", cursor)
    monkeypatch.setattr(ad, "DESK_PATH", desk)
    monkeypatch.setattr(ad, "ROOT", tmp_path)

    issues = dd._canvas_pollution_detected(polluted)
    assert "orphan_lane_sections" in issues
    assert "unknown_speaker_header" in issues
    assert "duplicate_dialogue_blocks" in issues

    healed = dd._maybe_auto_heal_desk()
    assert healed and healed.get("auto_healed") == "canvas_pollution"
    text = desk.read_text(encoding="utf-8")
    assert "## Local (orchestrator)" not in text
    assert "### Unknown ·" not in text
    assert "Ship the desk loop." in text
    assert log.read_text(encoding="utf-8") == ""


def test_turn_auto_heal_skips_canvas_pollution(tmp_path, monkeypatch):
    """Mid-turn heal must not wipe canvas — only echo/empty streak."""
    desk = tmp_path / "memory" / "working" / "agent_desk.md"
    log = tmp_path / "memory" / "working" / "agent_desk_dialogue.jsonl"
    cursor = tmp_path / "memory" / "working" / "agent_desk_cursor.json"
    desk.parent.mkdir(parents=True)
    polluted = """# Agent desk

## Goal
Chess POC

## Dialogue

### DeepSeek · Move 1
1. e4

### DeepSeek · Move 1
1. e4

## Local (orchestrator)
Bad section
"""
    desk.write_text(polluted, encoding="utf-8")
    cursor.write_text('{"holder":"local","turn":1}', encoding="utf-8")
    log.write_text('{"speaker":"local","reply":"ok"}\n', encoding="utf-8")

    import mag.agent_desk as ad

    monkeypatch.setattr(dd, "ROOT", tmp_path)
    monkeypatch.setattr(dd, "DIALOGUE_LOG", log)
    monkeypatch.setattr(dd, "CURSOR_PATH", cursor)
    monkeypatch.setattr(ad, "DESK_PATH", desk)
    monkeypatch.setattr(ad, "ROOT", tmp_path)

    assert dd._canvas_pollution_detected(polluted)
    assert dd._maybe_auto_heal_turn() is None
    assert "Chess POC" in desk.read_text(encoding="utf-8")
    assert log.read_text(encoding="utf-8").strip() != ""


def test_desk_health_check_headline():
    out = dd.desk_health_check(auto_heal=False)
    assert out["ok"] is True
    assert out.get("headline") == "Desk healthy"


def test_extract_chess_move():
    assert dd._extract_chess_move("### Local · board\n1. e4\n") == "e4"
    assert dd._extract_chess_move("no move here") == ""


def test_local_canvas_wake_ok_accepts_prose():
    prose = "### Local · note\nbuild_audit.v1 fields confirmed on canvas.\n"
    assert dd._local_canvas_wake_ok(prose) is True


def test_local_canvas_wake_ok_rejects_empty():
    assert dd._local_canvas_wake_ok("") is False
    assert dd._local_canvas_wake_ok("### Local · title\n") is False


@pytest.mark.skipif(not __import__("mag.agent_arena", fromlist=["_HAS_CHESS"])._HAS_CHESS, reason="python-chess not installed")
def test_maybe_sync_arena_from_edit(tmp_path, monkeypatch):
    import mag.agent_arena as arena

    state_path = tmp_path / "agent_arena.json"
    monkeypatch.setattr(arena, "STATE_PATH", state_path)
    arena.new_game(white="local", black="remote")
    synced = dd._maybe_sync_arena_from_edit("### Local · board\n1. e4\n", speaker="local")
    assert synced and synced.get("ok") is True
    assert synced.get("applied") == "e4"
