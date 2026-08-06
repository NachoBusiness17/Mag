"""TV-safe display payload."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mag import display as disp


def test_build_display_payload_shape(tmp_path, monkeypatch):
    desk = tmp_path / "memory" / "working" / "agent_desk.md"
    desk.parent.mkdir(parents=True)
    desk.write_text(
        "## Goal\n\nShip the roku viewport\n\n## Dialogue\n\n### Local · hi\nHello\n",
        encoding="utf-8",
    )
    trust = tmp_path / "memory" / "working" / "agent_desk_trust_status.json"
    trust.write_text(
        json.dumps({"tier": 0, "ui_smoke_score": "7/7", "baseline_score": "1/4"}),
        encoding="utf-8",
    )
    cursor = tmp_path / "memory" / "working" / "agent_desk_cursor.json"
    cursor.write_text(
        json.dumps({"holder": "local", "remote_asleep": True}),
        encoding="utf-8",
    )

    monkeypatch.setattr(disp, "DESK_PATH", desk)
    monkeypatch.setattr(disp, "TRUST_PATH", trust)
    monkeypatch.setattr(disp, "CURSOR_PATH", cursor)

    def fake_chronicle():
        return {
            "ok": True,
            "content": "# Pulse\n\nLab is running",
            "updated": "2026-08-05",
            "events": [{"layman": "Cursor bridge activity", "preview": "bridge"}],
        }

    def fake_nervous(**_kw):
        return {
            "ok": True,
            "integral_ok": True,
            "body": {"dashboard_8765": True, "ollama_11434": True},
            "desk_trust": json.loads(trust.read_text(encoding="utf-8")),
        }

    import mag.chronicle as ch
    import mag.nervous_system as ns

    monkeypatch.setattr(ch, "build_chronicle_payload", fake_chronicle)
    monkeypatch.setattr(ns, "build_glance", fake_nervous)

    payload = disp.build_display_payload()
    assert payload["schema"] == "mag_display.v1"
    assert payload["headline"]
    assert payload["desk"]["goal"] == "Ship the roku viewport"
    assert payload["desk"]["cursor"].startswith("local")
    assert "DeepSeek asleep" in payload["desk"]["cursor"]
    assert payload["events"]
    assert payload["poll_seconds"] == 15


def test_h_display_handler():
    from dashboard.rest import h_display

    code, body = h_display({}, None)
    assert code == 200
    assert body["ok"] is True
    assert body["schema"] == "mag_display.v1"
