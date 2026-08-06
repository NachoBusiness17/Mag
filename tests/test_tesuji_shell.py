"""Tesuji shell tests — emergent wins path (symmetric to behavioral errors)."""
from __future__ import annotations

from pathlib import Path

import pytest

import mag.improve as imp
import mag.tesuji_shell as ts


@pytest.fixture
def shell_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    daily = tmp_path / "memory" / "improve" / "daily"
    daily.mkdir(parents=True)
    logs = tmp_path / "logs"
    logs.mkdir(parents=True)
    training = tmp_path / "memory" / "training"
    training.mkdir(parents=True)
    decisions = tmp_path / "memory" / "decisions_log.jsonl"
    decisions.write_text("", encoding="utf-8")

    monkeypatch.setattr(ts, "ROOT", tmp_path)
    monkeypatch.setattr(ts, "SHELLS_PATH", logs / "tesuji_shells.jsonl")
    monkeypatch.setattr(ts, "DAILY_DIR", daily)
    monkeypatch.setattr(imp, "ROOT", tmp_path)
    return tmp_path


def test_log_and_synthesize_leaf(shell_fixture):
    res = ts.log_tesuji_shell(
        "Peer handoff brief surfaced mesh pattern we didn't design",
        surprise="emerged from coordination excerpt, not from plan",
        maps_to="skill:mesh-comm",
        source="test",
    )
    assert res.get("ok") is True
    assert (shell_fixture / "logs" / "tesuji_shells.jsonl").is_file()

    leaf = ts.synthesize_tesuji_shell_leaf("2026-08-05")
    assert leaf.get("ok") is True
    assert leaf.get("wins_n") == 1
    path = shell_fixture / "memory" / "improve" / "daily" / "2026-08-05-tesuji-shells.md"
    assert path.is_file()
    body = path.read_text(encoding="utf-8")
    assert "W1" in body
    assert "mesh pattern" in body
    assert "skill:mesh-comm" in body


def test_tesuji_shell_candidates_mined_by_scout(shell_fixture):
    daily = shell_fixture / "memory" / "improve" / "daily"
    (daily / "2026-08-05-tesuji-shells.md").write_text(
        "## W1 — Tripartite boot caught stale session\n"
        "- surprise: none of us planned the three-seat handshake\n"
        "- maps_to: tesuji:tripartite-boot\n",
        encoding="utf-8",
    )
    rows = imp._tesuji_shell_candidates("2026-08-05")
    shell_rows = [r for r in rows if "Tesuji shells leaf" in r.get("claim", "")]
    assert shell_rows
    assert shell_rows[0]["kind"] == "tesuji"
    assert "W1" in shell_rows[0]["detail"]
