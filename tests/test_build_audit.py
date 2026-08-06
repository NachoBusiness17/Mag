"""Tests for mag/build_audit.py — RUN B factory pilot."""
from __future__ import annotations

import json

import pytest

from mag import build_audit


def test_build_record_schema():
    rec = build_audit.build_record(
        "factory-audit-json",
        verdict="pass",
        spec_path="queue/handoff/BUILD-factory-audit-json.md",
        commands=["pytest -q"],
        diff_stat=" 1 file changed",
    )
    assert rec["schema"] == "build_audit.v1"
    assert rec["slug"] == "factory-audit-json"
    assert rec["verdict"] == "pass"
    assert rec["spec_path"].endswith(".md")
    assert rec["commands"] == ["pytest -q"]


def test_write_and_load_round_trip(tmp_path, monkeypatch):
    audit_dir = tmp_path / "runs" / "build_audit"
    factory_dir = tmp_path / "factory"
    monkeypatch.setattr(build_audit, "AUDIT_DIR", audit_dir)
    monkeypatch.setattr(build_audit, "FACTORY_DIR", factory_dir)
    monkeypatch.setattr(build_audit, "ROOT", tmp_path)

    res = build_audit.write_audit(
        "test-slug",
        verdict="fix",
        spec_path="docs/spec.md",
        note="round trip",
    )
    assert res["ok"]
    assert (audit_dir / "test-slug.json").is_file()
    assert (factory_dir / "build_audit-test-slug.json").is_file()

    loaded = build_audit.load_audit("test-slug")
    assert loaded is not None
    assert loaded["verdict"] == "fix"
    assert loaded["note"] == "round trip"


def test_dry_run_no_file(tmp_path, monkeypatch):
    audit_dir = tmp_path / "runs" / "build_audit"
    monkeypatch.setattr(build_audit, "AUDIT_DIR", audit_dir)
    monkeypatch.setattr(build_audit, "FACTORY_DIR", tmp_path / "factory")

    res = build_audit.write_audit("dry-slug", verdict="pass", dry=True)
    assert res["ok"] and res.get("dry")
    assert not (audit_dir / "dry-slug.json").exists()


def test_invalid_verdict():
    with pytest.raises(ValueError, match="verdict"):
        build_audit.build_record("x", verdict="maybe")


def test_load_missing():
    assert build_audit.load_audit("nonexistent-slug-xyz") is None
