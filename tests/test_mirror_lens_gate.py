"""Tests for mirror decision lens promote gate."""

from __future__ import annotations

import pytest

import mag.improve as imp


@pytest.fixture(autouse=True)
def lens_on(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MAG_MIRROR_LENS_GATE", "1")


def test_lens_pass_local_conflict_scan():
    verdict, reason = imp._mirror_lens_verdict(
        {
            "claim": "SubtleMemory conflict-scan pass on residual write path",
            "detail": "local-first vigilance hook under 30 min",
            "tags": ["verkle"],
        }
    )
    assert verdict == "pass"
    assert "starved" in reason or "no block" in reason


def test_lens_reject_single_oracle():
    verdict, reason = imp._mirror_lens_verdict(
        {
            "claim": "Route all inference through single oracle API",
            "detail": "remote-only cloud dependency; no local path",
        }
    )
    assert verdict == "reject"
    assert "oracle" in reason or "remote" in reason


def test_lens_hold_cloud_without_local():
    verdict, reason = imp._mirror_lens_verdict(
        {
            "claim": "Hosted SaaS dashboard for improve metrics",
            "detail": "cloud-only analytics without fork steps",
        }
    )
    assert verdict == "hold"
    assert "cloud" in reason


def test_lens_gate_disabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MAG_MIRROR_LENS_GATE", "0")
    assert imp._mirror_lens_gate_enabled() is False


def test_append_practices_skips_reject(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(imp, "ROOT", tmp_path)
    paths = {
        "playbook": tmp_path / "memory" / "improve" / "playbook.md",
    }
    paths["playbook"].parent.mkdir(parents=True)
    practices = [
        {"id": "c-bad", "claim": "single oracle remote-only pipeline", "source_urls": []},
        {"id": "c-good", "claim": "local-first ollama fallback with usage.jsonl trace", "source_urls": []},
    ]
    imp._append_practices_to_playbook(paths, practices)
    text = paths["playbook"].read_text(encoding="utf-8")
    assert "c-bad" not in text
    assert "c-good" in text
