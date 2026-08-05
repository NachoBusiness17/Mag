"""Tests for mag.ponytail_audit."""
from __future__ import annotations

from mag.ponytail_audit import format_report, run_audit


def test_run_audit_returns_schema():
    res = run_audit(hints=False)
    assert res.get("schema") == "ponytail_audit.v1"
    assert res.get("ok") is True
    assert res.get("ladder_compliance", {}).get("ok") is True


def test_format_report_lean_or_findings():
    res = run_audit(hints=False)
    text = format_report(res)
    assert text


def test_no_duplicate_depth_job_map_definition():
    res = run_audit(hints=False)
    high_dup = [
        f for f in res.get("findings") or []
        if f.get("tag") == "dup" and f.get("severity") == "high"
    ]
    assert not high_dup
