import json

from mag import training_events as te


def _event(event_id, *, success=True, tier="T2", join="default"):
    return {
        "schema": te.SCHEMA, "event_id": event_id, "pattern": "task_lifecycle",
        "join": {"task_id": "t1"} if join == "default" else join, "input": {"goal": "do bounded work"},
        "action": {}, "outcome": {"success": success}, "tier_max": tier, "exportable": True,
    }


def test_export_only_green_joined_t2_rows(tmp_path, monkeypatch):
    source = tmp_path / "events.jsonl"
    rows = [_event("green"), _event("failed", success=False), _event("private", tier="T1"), _event("unjoined", join={})]
    source.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    monkeypatch.setattr(te, "EVENTS_PATH", source)
    dest = tmp_path / "export.jsonl"
    result = te.export_jsonl(dest=dest)
    exported = [json.loads(line) for line in dest.read_text(encoding="utf-8").splitlines()]
    assert [r["event_id"] for r in exported] == ["green"]
    assert result["n_exported"] == 1
    manifest = json.loads((tmp_path / "export.manifest.json").read_text(encoding="utf-8"))
    assert manifest["sha256"] == result["sha256"]
