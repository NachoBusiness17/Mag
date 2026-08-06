"""Unsloth Studio GPU seat — mocked tests (no unsloth install required)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mag import unsloth_seat as us


def test_unsloth_exe_default_path():
    p = us.unsloth_exe()
    assert p.name in ("unsloth.exe", "unsloth")
    assert ".unsloth" in str(p)


def test_unsloth_status_not_installed(monkeypatch, tmp_path):
    fake = tmp_path / "missing.exe"
    monkeypatch.setattr(us, "unsloth_exe", lambda: fake)
    monkeypatch.setattr(us, "_read_state", lambda: {})
    monkeypatch.setattr(us, "_run_version", lambda exe: "")

    out = us.unsloth_status()
    assert out["schema"] == us.SCHEMA
    assert out["installed"] is False
    assert out["running"] is False
    assert out["seat_id"] == "unsloth-studio"


def test_unsloth_status_running(monkeypatch, tmp_path):
    exe = tmp_path / "unsloth.exe"
    exe.write_text("", encoding="utf-8")
    state_file = tmp_path / "state.json"
    monkeypatch.setattr(us, "unsloth_exe", lambda: exe)
    monkeypatch.setattr(us, "STATE_PATH", state_file)
    monkeypatch.setattr(us, "_run_version", lambda e: "unsloth 2026.7.4")
    monkeypatch.setattr(us, "_pid_alive", lambda pid: pid == 4242)
    monkeypatch.setattr(
        us,
        "_read_state",
        lambda: {"pid": 4242, "mode": "chat", "started": "2026-08-05T00:00:00+00:00"},
    )
    monkeypatch.setattr(us, "_desk_gpu_hint", lambda: {"desk_model": "gemma4-desk", "cache_models": []})

    out = us.unsloth_status()
    assert out["installed"] is True
    assert out["running"] is True
    assert out["pid"] == 4242
    assert out["mode"] == "chat"


def test_build_unsloth_payload_agent_row(monkeypatch, tmp_path):
    exe = tmp_path / "unsloth.exe"
    exe.write_text("", encoding="utf-8")
    monkeypatch.setattr(us, "unsloth_exe", lambda: exe)
    monkeypatch.setattr(us, "_read_state", lambda: {})
    monkeypatch.setattr(us, "_run_version", lambda e: "unsloth 2026.7.4")
    monkeypatch.setattr(us, "_pid_alive", lambda pid: False)
    monkeypatch.setattr(us, "_desk_gpu_hint", lambda: {"desk_model": "gemma4-desk", "cache_models": ["qwen"]})

    payload = us.build_unsloth_payload()
    row = payload["agent_row"]
    assert row["kind"] == "unsloth_gpu"
    assert row["id"] == "unsloth-studio"
    assert payload["research_row"]["id"] == "unsloth_studio"


def test_unsloth_start_spawns(monkeypatch, tmp_path):
    exe = tmp_path / "unsloth.exe"
    exe.write_text("", encoding="utf-8")
    log = tmp_path / "unsloth.log"
    state_file = tmp_path / "state.json"

    class FakeProc:
        pid = 9999

    monkeypatch.setattr(us, "unsloth_exe", lambda: exe)
    monkeypatch.setattr(us, "LOG_PATH", log)
    monkeypatch.setattr(us, "STATE_PATH", state_file)
    monkeypatch.setattr(us, "_read_state", lambda: {})
    monkeypatch.setattr(us, "_pid_alive", lambda pid: False)
    monkeypatch.setattr(us, "_run_version", lambda e: "unsloth 2026.7.4")
    monkeypatch.setattr(us, "_desk_gpu_hint", lambda: {"desk_model": "gemma4-desk", "cache_models": []})

    captured: dict = {}

    def fake_popen(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return FakeProc()

    monkeypatch.setattr(us.subprocess, "Popen", fake_popen)

    import mag.seat_registry as sr

    monkeypatch.setattr(sr, "register", lambda **kw: {"task_id": "task-test-1", **kw})

    res = us.unsloth_start(mode="chat", model="gemma-test", register_seat=True)
    assert res["ok"] is True
    assert res["pid"] == 9999
    assert captured["cmd"][0] == str(exe)
    assert "chat" in captured["cmd"]
    assert state_file.is_file()
    saved = json.loads(state_file.read_text(encoding="utf-8"))
    assert saved["pid"] == 9999
    assert saved["mag_task_id"] == "task-test-1"


def test_unsloth_stop_kills(monkeypatch, tmp_path):
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({"pid": 5555, "mag_task_id": "tid-1"}), encoding="utf-8")
    killed: list[int] = []
    alive = {5555}

    monkeypatch.setattr(us, "STATE_PATH", state_file)
    monkeypatch.setattr(us, "_pid_alive", lambda pid: pid in alive)
    monkeypatch.setattr(
        us,
        "_kill_pid",
        lambda pid: (killed.append(pid), alive.discard(pid)),
    )
    monkeypatch.setattr(us, "_run_version", lambda e: "")
    monkeypatch.setattr(us, "unsloth_exe", lambda: tmp_path / "u.exe")
    monkeypatch.setattr(us, "_desk_gpu_hint", lambda: {"desk_model": "gemma4-desk", "cache_models": []})
    monkeypatch.setattr(us, "time", type("T", (), {"sleep": staticmethod(lambda s: None)})())

    import mag.seat_registry as sr

    unregistered: list[str] = []
    monkeypatch.setattr(
        sr,
        "unregister",
        lambda tid, **kw: unregistered.append(tid) or {"ok": True},
    )

    res = us.unsloth_stop()
    assert res["ok"] is True
    assert 5555 in killed
    assert "tid-1" in unregistered


def test_h_unsloth_get():
    from dashboard.rest import h_unsloth

    code, body = h_unsloth({}, None)
    assert code == 200
    assert body.get("schema") == us.SCHEMA
    assert "agent_row" in body


def test_h_unsloth_post_stop(monkeypatch):
    from dashboard.rest import h_unsloth

    monkeypatch.setattr(us, "unsloth_stop", lambda **kw: {"ok": True, "action": "stop"})
    code, body = h_unsloth({}, {"action": "stop"})
    assert code == 200
    assert body.get("action") == "stop"
