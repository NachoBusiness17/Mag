from __future__ import annotations

import mag.feature_lab as lab


def test_candidate_requires_isolation_sync_and_bound_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(lab, "ROOT", tmp_path / "main")
    (tmp_path / "main").mkdir()
    monkeypatch.setattr(lab, "_git", lambda root, *args: (0, "") if args[0] == "status" else (0, "origin/feature") if args[0] == "rev-parse" else (0, "0 0"))
    monkeypatch.setattr(lab, "_evidence_for", lambda root, branch, head: {"verified": True, "bound_to_head": True, "path": "proof.json"})
    monkeypatch.setattr(lab, "_task_for", lambda branch: None)
    monkeypatch.setattr(lab, "_handoff_for", lambda branch: None)
    item = lab._candidate({"worktree": str(tmp_path / "feature"), "branch": "refs/heads/feature", "HEAD": "abcdef"}, "main")
    assert item["graduation_ready"] is True
    assert item["stage"] == "ready for review"


def test_dirty_candidate_cannot_graduate(tmp_path, monkeypatch):
    monkeypatch.setattr(lab, "ROOT", tmp_path / "main")
    (tmp_path / "main").mkdir()
    monkeypatch.setattr(lab, "_git", lambda root, *args: (0, " M file.py") if args[0] == "status" else (0, "origin/feature") if args[0] == "rev-parse" else (0, "0 0"))
    monkeypatch.setattr(lab, "_evidence_for", lambda root, branch, head: {"verified": True, "bound_to_head": True})
    monkeypatch.setattr(lab, "_task_for", lambda branch: None)
    monkeypatch.setattr(lab, "_handoff_for", lambda branch: None)
    item = lab._candidate({"worktree": str(tmp_path / "feature"), "branch": "refs/heads/feature"}, "main")
    assert item["graduation_ready"] is False
    assert item["stage"] == "building"


def test_graduation_refuses_missing_gates(monkeypatch):
    monkeypatch.setattr(lab, "status", lambda: {"operational_branch": "main", "candidates": [{"branch": "feature", "graduation_ready": False, "gates": {"verified": False}}]})
    out = lab.request("feature", "graduate")
    assert out["ok"] is False
    assert out["missing"] == ["verified"]
