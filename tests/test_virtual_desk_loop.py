"""Virtual desk loop — state and planning without DeepSeek calls."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mag.virtual_desk_loop import (  # noqa: E402
    QUESTIONS,
    _next_unit,
    load_brief,
    read_state,
    run_once,
    write_state,
)


def test_brief_loads():
    text = load_brief()
    assert "ACTIVATION" in text
    assert "P0" in text
    assert len(text) > 1000


def test_next_unit_skips_done(monkeypatch, tmp_path):
    monkeypatch.setattr("mag.virtual_desk_loop.PACK_ROOT", tmp_path)
    st = read_state()
    st["done_questions"] = ["Q1", "Q2"]
    write_state(st)
    unit = _next_unit(read_state())
    assert unit is not None
    assert unit["id"] == "Q3"


def test_run_once_dry(monkeypatch, tmp_path):
    monkeypatch.setattr("mag.virtual_desk_loop.PACK_ROOT", tmp_path)
    monkeypatch.setattr("mag.virtual_desk_loop.ROOT", tmp_path)
    brief = tmp_path / "docs" / "ref" / "RESEARCH_MAG_VIRTUAL_DESK.txt"
    brief.parent.mkdir(parents=True, exist_ok=True)
    brief.write_text("ACTIVATION\nP0 research brief stub.\n" * 50, encoding="utf-8")
    monkeypatch.setattr(
        "mag.virtual_desk_loop.load_config",
        lambda: {
            "brief_paths": ["docs/ref/RESEARCH_MAG_VIRTUAL_DESK.txt"],
            "report_path": "memory/research_packs/mag_virtual_desk/REPORT.txt",
        },
    )
    res = run_once(dry=True)
    assert res.get("ok") is True
    assert res.get("dry") is True
    assert res.get("unit", {}).get("id") == "Q1"


def test_all_questions_count():
    assert len(QUESTIONS) == 10
    ids = [q["id"] for q in QUESTIONS]
    assert ids[0] == "Q1" and ids[4] == "Q5"


def test_import_export(monkeypatch, tmp_path):
    monkeypatch.setattr("mag.virtual_desk_loop.PACK_ROOT", tmp_path / "pack")
    monkeypatch.setattr("mag.virtual_desk_loop.ROOT", tmp_path)
    src = tmp_path / "export.txt"
    src.write_text(
        "Q1 Isolation model\nAnswer about queues.\nQ2 Supervision pattern\nParent child.\n",
        encoding="utf-8",
    )
    from mag.virtual_desk_loop import import_export

    res = import_export(src, source_url="https://chat.deepseek.com/share/abc123")
    assert res.get("ok") is True
    assert "Q1" in (res.get("detected_done_questions") or [])
    report = tmp_path / "memory/research_packs/mag_virtual_desk/REPORT.txt"
    assert report.is_file()
    assert "Isolation model" in report.read_text(encoding="utf-8")
