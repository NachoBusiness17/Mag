"""Unit tests that do not require Ollama."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from handoff.schema import new_handoff, validate_handoff, write_handoff
from tools import dispatch
from tools.filesystem import list_dir, read_file


def test_list_memory():
    r = list_dir("memory")
    assert r["ok"] is True
    assert r["exit_code"] == 0


def test_read_locus():
    r = read_file("memory/locus.md")
    assert r["ok"] is True
    assert "sovereign" in r["output"].lower() or "Quixote" in r["output"]


def test_dispatch_unknown():
    r = dispatch("nope", {})
    assert r["ok"] is False


def test_handoff_schema(tmp_path: Path):
    data = new_handoff(
        handoff_id="test-1",
        goal="x",
        ask="y",
        return_path=str(tmp_path / "r.json"),
    )
    ok, errs = validate_handoff(data)
    assert ok, errs
    p = tmp_path / "h.json"
    write_handoff(p, data)
    assert p.is_file()
    assert p.with_suffix(".md").is_file()
