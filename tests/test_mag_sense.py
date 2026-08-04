"""Mag sense/judge without full Ollama cycle."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.grok_cli import find_grok, harness_available
from mag.sense import sense


def test_sense_has_policy():
    s = sense()
    assert "policy" in s
    assert "assigned" in s


def test_grok_harness_binary():
    if find_grok():
        assert harness_available() is True
    else:
        assert harness_available() is False
