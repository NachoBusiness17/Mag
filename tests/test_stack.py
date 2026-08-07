"""Agent stack viewport — services, fleet, REST outputs."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mag import stack as stk


def test_build_stack_payload_shape(monkeypatch):
    def fake_power():
        return {
            "headline": "3/4 services up",
            "stack_up": True,
            "power_off": False,
            "services": {"backend": True, "dashboard": True, "mirror": False},
            "fleet": {"running": 2, "total": 4},
            "switchboard_summary": "ok",
            "supervisor": {"pids": {"lab": 1234}},
        }

    def fake_nervous(**_kw):
        return {
            "ok": True,
            "integral_ok": True,
            "body": {"ollama_11434": True},
        }

    def fake_cursor():
        return {"holder": "local", "remote_asleep": True, "turn": 1, "local_wake_pending": False}

    def fake_trust():
        return {"tier": 0, "ui_smoke_score": "7/7"}

    def fake_feed(**_kw):
        return {
            "paths": {"desk-local": "memory/working/desk-local_feed.jsonl"},
            "entries": [
                {"ts": "2026-08-05T12:00:00+00:00", "source": "desk-local", "preview": "Hello stack"},
            ],
        }

    def fake_chronicle():
        return {
            "updated": "2026-08-05",
            "events": [{"ts": "2026-08-05T11:00:00+00:00", "kind": "pulse", "layman": "Lab pulse"}],
        }

    import mag.chronicle as ch
    import mag.desk_dialogue as dd
    import mag.nervous_system as ns
    import mag.power as pw
    import mag.seat_feed as sf

    monkeypatch.setattr(pw, "stack_status", fake_power)
    monkeypatch.setattr(ns, "build_glance", fake_nervous)
    monkeypatch.setattr(dd, "read_cursor", fake_cursor)
    monkeypatch.setattr(dd, "read_trust_status", fake_trust)
    monkeypatch.setattr(sf, "unified_seat_feed", fake_feed)
    monkeypatch.setattr(ch, "build_chronicle_payload", fake_chronicle)

    payload = stk.build_stack_payload(feed_limit=10, agent_limit=5)
    assert payload["schema"] == "mag_stack.v1"
    assert payload["ok"] is True
    assert payload["headline"] == "3/4 services up"
    assert payload["integral_ok"] is True
    assert isinstance(payload["triad"], list)
    assert "supervisor" in payload
    assert isinstance(payload["fleet"], dict)
    assert any(s["id"] == "ollama" for s in payload["services"])
    assert any(s["id"] == "supervisor_lab" for s in payload["services"])
    assert any(a["kind"] == "desk_local" for a in payload["agents"])
    assert any(a["kind"] == "desk_remote" for a in payload["agents"])
    assert payload["outputs"]
    assert payload["outputs"][0]["api"] in ("GET /api/v1/seat-feed", "GET /api/v1/chronicle")
    assert payload["poll_seconds"] == 10


def test_h_stack_handler():
    from dashboard.rest import h_stack

    code, body = h_stack({"limit": "5"}, None)
    assert code == 200
    assert body["ok"] is True
    assert body["schema"] == "mag_stack.v1"
    assert isinstance(body["services"], list)
    assert isinstance(body["agents"], list)
    assert isinstance(body["outputs"], list)
