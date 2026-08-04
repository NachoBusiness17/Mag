"""Behavioral-error awareness tests — self-contained (fresh-clone safe)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import mag.improve as imp


@pytest.fixture
def behavioral_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Seed minimal behavioral sources so tests pass without live operator memory."""
    daily = tmp_path / "memory" / "improve" / "daily"
    daily.mkdir(parents=True)
    (daily / "2026-08-04-behavioral.md").write_text(
        "## T1 — preflight block\nAvoid: retry same tool\n\n"
        "## T2 — collapse loop\n\n"
        "## T3 — steer silence\n\n"
        "## T4 — repack empty\n\n"
        "## T5 — seat crash\n",
        encoding="utf-8",
    )
    dec = tmp_path / "memory" / "decisions_log.jsonl"
    dec.parent.mkdir(parents=True, exist_ok=True)
    dec.write_text(
        json.dumps(
            {
                "timestamp": "2026-08-04T12:00:00Z",
                "context": "steer doesn't work at all on dashboard",
                "outcome": "fixed inbox API",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    logs = tmp_path / "logs"
    logs.mkdir(parents=True)
    (logs / "seat_crashes.log").write_text(
        "Traceback (most recent call last):\n  File test.py\nValueError: boom\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(imp, "ROOT", tmp_path)
    return tmp_path


def test_behavioral_candidates_mines_leaves(behavioral_fixture):
    rows = imp._behavioral_candidates("2026-08-04")
    leaf_rows = [r for r in rows if "Behavioral leaf" in r.get("claim", "")]
    assert leaf_rows
    leaf = leaf_rows[0]
    assert "5 recurring seat-error themes" in leaf["claim"]
    assert "T1" in leaf["detail"] and "T5" in leaf["detail"]
    assert leaf["kind"] == "risk"


def test_behavioral_candidates_mines_decisions_log(behavioral_fixture):
    rows = imp._behavioral_candidates("2026-08-04")
    dec_rows = [r for r in rows if "Decisions log" in r.get("claim", "")]
    assert dec_rows
    assert "operator-visible failure steers" in dec_rows[0]["claim"]
    assert dec_rows[0]["kind"] == "risk"


def test_behavioral_candidates_mines_crash_log(behavioral_fixture):
    rows = imp._behavioral_candidates("2026-08-04")
    crash_rows = [r for r in rows if "Seat crash log" in r.get("claim", "")]
    assert crash_rows
    assert "real crash blocks" in crash_rows[0]["claim"]
    assert crash_rows[0]["kind"] == "risk"


def test_mag_internal_includes_behavioral(behavioral_fixture):
    rows = imp._mag_internal_candidates("2026-08-04")
    kinds = [r.get("kind") for r in rows]
    assert "risk" in kinds
    claims = " ".join(r.get("claim", "") for r in rows)
    assert "Behavioral leaf" in claims
    assert "Decisions log" in claims
    assert "Seat crash log" in claims
