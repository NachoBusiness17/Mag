"""Tests for mirror voice excerpt injection in context pack."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mag import context_pack as cp


@pytest.fixture
def mirror_jsonl(tmp_path: Path) -> Path:
    republic = tmp_path / "mycelial-republic"
    ann = republic / "data" / "annotated"
    ann.mkdir(parents=True)
    rows = [
        {
            "id": "ex-rope-1",
            "text": "Elias carried a rope through his days with unexamined knots.",
            "signal": "high",
            "knot_tags": ["rope"],
            "product_dna": "republic_governance",
        },
        {
            "id": "ex-refusal-1",
            "text": "I do not consent to training that hides the cost from the people who will pay it.",
            "signal": "medium",
            "knot_tags": ["refusal"],
            "product_dna": "sovereign_mirror",
        },
        {
            "id": "ex-noise-1",
            "text": "Random low signal chatter about lunch.",
            "signal": "low",
            "knot_tags": ["daily"],
            "product_dna": "political_commentary",
        },
    ]
    path = ann / "mirror_train.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    return republic


def test_mirror_voice_gate_off_empty(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("MAG_INJECT_MIRROR_VOICE", raising=False)
    assert cp._mirror_voice_excerpt("rope vigilance", max_chars=600) == ""


def test_mirror_voice_gate_on_with_fixture(monkeypatch: pytest.MonkeyPatch, mirror_jsonl: Path):
    monkeypatch.setenv("MAG_INJECT_MIRROR_VOICE", "1")
    monkeypatch.setenv("MAG_REPUBLIC_ROOT", str(mirror_jsonl))
    excerpt = cp._mirror_voice_excerpt("rope elias tension", max_chars=600)
    assert excerpt
    assert "ex-rope-1" in excerpt
    assert "rope" in excerpt.lower()


def test_clue_chain_gate_off_empty(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("MAG_INJECT_CLUE_CHAIN", raising=False)
    assert cp._clue_chain_excerpt(max_chars=500) == ""
