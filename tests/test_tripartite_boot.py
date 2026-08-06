"""Tripartite boot — heart/mind/body coordination at startup."""
from __future__ import annotations

import json
from pathlib import Path

import mag.tripartite_boot as tb


def _patch_paths(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(tb, "ROOT", tmp_path)
    monkeypatch.setattr(tb, "BOOT_DIR", tmp_path / "memory" / "boot")
    monkeypatch.setattr(tb, "LATEST_JSON", tmp_path / "memory" / "boot" / "tripartite_latest.json")
    monkeypatch.setattr(tb, "LATEST_MD", tmp_path / "memory" / "boot" / "tripartite_latest.md")
    monkeypatch.setattr(tb, "BOOT_LOG", tmp_path / "logs" / "boot_coordination.jsonl")
    monkeypatch.setattr(tb, "STATE_DIR", tmp_path / "state")


def test_coordinated_boot_writes_manifest(tmp_path: Path, monkeypatch):
    _patch_paths(tmp_path, monkeypatch)

    res = tb.run_coordinated_boot(actor="pytest", seat="cursor", task_id="t-1")
    assert res.get("ok")
    assert res["heart"]["role"] == "heart"
    assert res["mind"]["role"] == "mind"
    assert res["body"]["role"] == "body"
    assert res["body"]["registering_seat"] == "cursor"
    assert tb.LATEST_JSON.is_file()
    data = json.loads(tb.LATEST_JSON.read_text(encoding="utf-8"))
    assert data["schema"] == "tripartite_boot.v1"


def test_weave_route_and_spawn(tmp_path: Path, monkeypatch):
    _patch_paths(tmp_path, monkeypatch)

    tb.run_coordinated_boot(actor="pytest")
    tb.weave_route(goal="fix seats.py", route={"depth": "heavy_code", "provider": "deepseek"}, tag="t")
    tb.weave_spawn(task_id="orc-abc", goal="fix seats.py", provider="deepseek", pid=1234)
    manifest = json.loads(tb.LATEST_JSON.read_text(encoding="utf-8"))
    assert manifest.get("weave", {}).get("last_route")
    assert manifest.get("weave", {}).get("last_spawn", {}).get("task_id") == "orc-abc"


def test_format_tripartite_excerpt(tmp_path: Path, monkeypatch):
    _patch_paths(tmp_path, monkeypatch)

    tb.run_coordinated_boot(actor="pytest", body_slots=[{"name": "dashboard", "wanted": True, "proc": None}])
    excerpt = tb.format_tripartite_excerpt()
    assert "TRIPARTITE" in excerpt
    assert "heart" in excerpt.lower()
