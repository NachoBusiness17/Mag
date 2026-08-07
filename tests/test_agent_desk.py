"""Tests for agent desk shared canvas + peer lane."""
from __future__ import annotations

import json
from pathlib import Path

import mag.agent_desk as ad


def test_write_and_read_desk(tmp_path, monkeypatch):
    desk = tmp_path / "memory" / "working" / "agent_desk.md"
    monkeypatch.setattr(ad, "DESK_PATH", desk)
    monkeypatch.setattr(ad, "ROOT", tmp_path)
    out = ad.write_desk("# goal\nship v3")
    assert out["ok"] is True
    assert "ship v3" in out["text"]
    assert desk.is_file()


def test_peer_lane_excerpt_from_session(tmp_path, monkeypatch):
    import mag.chat_source as cs

    sess_dir = tmp_path / "memory" / "agent_sessions"
    sess_dir.mkdir(parents=True)
    path = sess_dir / "desk-deepseek.json"
    path.write_text(
        json.dumps(
            {
                "messages": [
                    {"role": "user", "content": "scan improve"},
                    {"role": "assistant", "content": "found growth cycle"},
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cs, "AGENT_SESS_DIR", sess_dir)
    excerpt = ad.peer_lane_excerpt("desk-deepseek")
    assert "scan improve" in excerpt
    assert "found growth cycle" in excerpt


def test_append_desk_section(tmp_path, monkeypatch):
    desk = tmp_path / "memory" / "working" / "agent_desk.md"
    monkeypatch.setattr(ad, "DESK_PATH", desk)
    monkeypatch.setattr(ad, "ROOT", tmp_path)
    ad.write_desk("# Agent desk\n\n## Goal\nbuild v3\n")
    out = ad.append_desk_section("Remote (DeepSeek)", "TL;DR: done", author="deepseek")
    assert "TL;DR: done" in out["text"]
    assert "### DeepSeek · deepseek" in out["text"]
    assert "## Remote (DeepSeek)" not in out["text"]


def test_append_desk_meta_raw(tmp_path, monkeypatch):
    desk = tmp_path / "memory" / "working" / "agent_desk.md"
    monkeypatch.setattr(ad, "DESK_PATH", desk)
    monkeypatch.setattr(ad, "ROOT", tmp_path)
    ad.write_desk("# Agent desk\n\n## Goal\nbuild v3\n\n## Operator notes\n")
    out = ad.append_desk_meta_raw("### DeepSeek Meta-A · tone\nKeep instructions short.\n")
    assert "## Meta" in out["text"]
    assert "### DeepSeek Meta-A · tone" in out["text"]
    assert "Keep instructions short." in out["text"]


def test_desk_preflight_blocks_run_shell():
    from mag.agent_cli import _preflight_tool

    ok, reason = _preflight_tool("run_shell", {"command": "echo hi"}, session_id="desk-deepseek")
    assert ok is False
    assert "desk seat" in reason.lower()
