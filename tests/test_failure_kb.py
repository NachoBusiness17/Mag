"""Tests for mag.failure_kb — dedupe, query, auto-draft remedy."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mag import failure_kb as fkb


@pytest.fixture(autouse=True)
def _isolate_fkb(tmp_path, monkeypatch):
    log_path = tmp_path / "failure_kb.jsonl"
    index_path = tmp_path / "signatures.json"
    remedy_dir = tmp_path / "remedies"
    monkeypatch.setattr(fkb, "LOG_PATH", log_path)
    monkeypatch.setattr(fkb, "INDEX_PATH", index_path)
    monkeypatch.setattr(fkb, "REMEDY_DIR", remedy_dir)
    monkeypatch.setattr(fkb, "AUTO_DRAFT_THRESHOLD", 3)
    yield


def test_log_failure_dedupes_signature():
    for _ in range(2):
        fkb.log_failure(kind="tool_fail", tool="write_file", detail="missing path", error="preflight")
    idx = json.loads(fkb.INDEX_PATH.read_text(encoding="utf-8"))
    sigs = idx["signatures"]
    assert len(sigs) == 1
    only = next(iter(sigs.values()))
    assert only["count"] == 2
    assert only["tool"] == "write_file"


def test_query_by_tool():
    fkb.log_failure(kind="tool_fail", tool="write_file", detail="bad shape", error="arguments")
    fkb.log_failure(kind="tool_fail", tool="run_python", detail="too short", error="preflight")
    hits = fkb.query("shape", tool="write_file")
    assert len(hits) == 1
    assert hits[0]["tool"] == "write_file"


def test_auto_draft_remedy_on_threshold(monkeypatch):
    monkeypatch.setattr("mag.remedy.REMEDY_DIR", fkb.REMEDY_DIR)
    for _ in range(3):
        fkb.log_failure(kind="collapse", tool="grep_tool", detail="5x identical grep", error="collapse")
    idx = json.loads(fkb.INDEX_PATH.read_text(encoding="utf-8"))
    rec = next(iter(idx["signatures"].values()))
    assert rec.get("remedy_id")
    card = fkb.REMEDY_DIR / f"{rec['remedy_id']}.md"
    assert card.is_file()
    assert "grep_tool" in card.read_text(encoding="utf-8")


def test_surface_hits_skips_single_occurrence():
    fkb.log_failure(kind="tool_fail", tool="write_file", detail="once", error="x")
    hits = fkb.surface_hits(goal="implement write_file patch")
    assert hits == []


def test_surface_hits_includes_recurring():
    for _ in range(3):
        fkb.log_failure(kind="tool_fail", tool="write_file", detail="missing path", error="preflight")
    hits = fkb.surface_hits(goal="write_file", limit=2)
    assert len(hits) == 1
    assert hits[0]["source"] == "failure_kb"
    assert "×3" in hits[0]["tip"]


def test_format_block_nonempty():
    for _ in range(2):
        fkb.log_failure(kind="tool_fail", tool="write_file", detail="x", error="y")
    recs = fkb.query("write_file", limit=1)
    block = fkb.format_block(recs)
    assert "FAILURE KB" in block
