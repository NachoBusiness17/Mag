from __future__ import annotations

import mag.attention_ranker as ranker


def _sources(monkeypatch, *, repo=None, tasks=None, road=None, inbox=None):
    monkeypatch.setattr(ranker, "_repo_snapshot", lambda: repo or {
        "ok": True, "branch": "mag/test", "upstream": "origin/mag/test",
        "head": "abc", "handoff_ready": True, "blockers": [],
    })
    monkeypatch.setattr(ranker, "_task_rows", lambda: tasks or [])
    monkeypatch.setattr(ranker, "_roadmap_snapshot", lambda: road or {
        "next": {"ok": True, "version": "v5", "meaning": "Test era", "gate": {"id": "next_gate"}, "passed_gates": []}
    })
    monkeypatch.setattr(ranker, "_inbox_snapshot", lambda: inbox or {"pending_n": 0})
    monkeypatch.setattr(ranker, "_feedback", lambda: {})


def test_repository_blocker_is_an_unhideable_interrupt(monkeypatch):
    _sources(monkeypatch, repo={
        "ok": True, "branch": "mag/test", "handoff_ready": False,
        "blockers": ["branch is behind upstream"],
    })
    result = ranker.build_ranked_attention()
    first = result["items"][0]
    assert first["id"] == "repo:handoff"
    assert first["band"] == "P0"
    assert first["hard_rule"] is True


def test_passed_gate_suppresses_old_worker_failure(monkeypatch):
    _sources(monkeypatch, tasks=[{
        "task_id": "t-old", "status": "failed", "tag": "roadmap-v5-gate_one",
        "detail": "non-zero exit", "goal": "Build gate one",
    }], road={"next": {
        "ok": True, "version": "v5", "meaning": "Next", "gate": {"id": "gate_two"},
        "passed_gates": ["gate_one"],
    }})
    result = ranker.build_ranked_attention()
    assert not any(x["id"] == "task:t-old" for x in result["items"])
    assert any(x["id"] == "roadmap:v5:gate_two" for x in result["items"])


def test_feedback_cannot_mute_hard_rule(monkeypatch):
    _sources(monkeypatch, repo={
        "ok": True, "branch": "mag/test", "handoff_ready": False,
        "blockers": ["dirty"],
    })
    monkeypatch.setattr(ranker, "_feedback", lambda: {"repo:handoff": ["mute"]})
    item = ranker.build_ranked_attention()["items"][0]
    assert item["band"] == "P0"


def test_pin_promotes_ordinary_evidence(monkeypatch):
    _sources(monkeypatch, road={"next": {"ok": False}})
    monkeypatch.setattr(ranker, "_feedback", lambda: {"repo:ready": ["pin"]})
    item = ranker.build_ranked_attention()["items"][0]
    assert item["id"] == "repo:ready"
    assert item["band"] == "P1"
