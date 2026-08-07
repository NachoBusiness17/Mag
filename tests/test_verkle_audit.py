"""Tests for mag.verkle_audit — deterministic audit + ticket reconcile."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from mag.verkle_audit import reconcile_tickets, run_audit, verkle_gaps


def test_verkle_gaps_returns_list():
    gaps = verkle_gaps()
    assert isinstance(gaps, list)
    for g in gaps:
        assert "kind" in g
        assert "detail" in g


def test_reconcile_tickets_schema():
    out = reconcile_tickets()
    assert out.get("ok") is True
    assert out.get("schema") == "tickets_reconcile.v1"
    assert "open" in out
    assert "counts" in out
    assert isinstance(out["counts"].get("open"), int)


def test_run_audit_dry_no_write(tmp_path, monkeypatch):
    monkeypatch.setattr("mag.verkle_audit.DAILY", tmp_path / "daily")
    res = run_audit(full=False, synth=False, reconcile=True, dry=True)
    assert res.get("ok") is True
    assert res.get("schema") == "verkle_audit.v1"
    assert "gaps" in res
    assert "reconcile" in res
    assert res.get("dry") is True
    assert "report_path" not in res


def test_run_audit_writes_report(tmp_path, monkeypatch):
    monkeypatch.setattr("mag.verkle_audit.DAILY", tmp_path / "daily")
    res = run_audit(full=False, synth=False, reconcile=False, dry=False)
    assert res.get("ok") is True
    assert "report_path" in res
    report = tmp_path / "daily"
    files = list(report.glob("*-verkle-audit.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text(encoding="utf-8"))
    assert data.get("schema") == "verkle_audit.v1"
