"""Conflict-scan pass on the residual bond write path (steal c-f368762f1e82).

Before appending a new bond, scan existing bonds for same-subject opposite-
polarity relations (SubtleMemory contract: memory value is in relations, and
contradictory relations must be surfaced, not silently appended).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mag.bonds import _polarity, _subjects, scan_conflicts  # noqa: E402


def test_polarity_heuristics():
    assert _polarity("I do not consent to training that hides the cost") == -1
    assert _polarity("We support local-first path same day") == 1
    assert _polarity("The village used to do its own counting") == 0


def test_subjects_split_hyphens_and_drop_stopwords():
    s = _subjects("Multi-frame agency without single-cause collapse")
    assert "single" in s and "cause" in s and "agency" in s
    assert "the" not in s and "without" not in s


def test_conflict_fires_on_opposite_polarity_same_subject():
    existing = ["Multi-frame agency without single-cause collapse"]
    cand = "Prefer single-cause explanation for every event"
    hits = scan_conflicts(cand, existing)
    assert len(hits) == 1
    h = hits[0]
    assert h["candidate_polarity"] == 1
    assert h["existing_polarity"] == -1
    assert {"single", "cause"} <= set(h["subjects"])


def test_no_conflict_on_same_polarity_or_disjoint():
    existing = ["Mag is a bonded helper, not the hero"]
    assert scan_conflicts("Mag is a bonded helper that stays humble", existing) == []
    assert scan_conflicts("Rope knots must be made visible", existing) == []
