"""Tests for mag/handoff_inbox.py."""
from __future__ import annotations

import json

from mag import handoff_inbox


def test_list_disk_handoffs(tmp_path, monkeypatch):
    qdir = tmp_path / "queue" / "handoff"
    qdir.mkdir(parents=True)
    (qdir / "peer-test-1.json").write_text(
        json.dumps({"goal": "merge PR", "from_seat": "cursor", "to_seat": "home"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(handoff_inbox, "HANDOFF_DIR", qdir)
    rows = handoff_inbox.list_disk_handoffs(limit=5)
    assert len(rows) == 1
    assert rows[0]["kind"] == "peer"
    assert "merge PR" in rows[0]["goal"]


def test_build_inbox_schema(tmp_path, monkeypatch):
    qdir = tmp_path / "queue" / "handoff"
    qdir.mkdir(parents=True)
    monkeypatch.setattr(handoff_inbox, "HANDOFF_DIR", qdir)
    payload = handoff_inbox.build_inbox(limit=5)
    assert payload.get("ok") is True
    assert payload.get("schema") == handoff_inbox.SCHEMA
    assert "scrum" in payload
    assert "items" in payload
