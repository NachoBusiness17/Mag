from __future__ import annotations


def test_remote_token_requires_strength_and_constant_match(monkeypatch):
    from mag import remote_control as rc

    monkeypatch.setenv(rc.TOKEN_ENV, "short")
    assert not rc.configured()
    assert not rc.authorized("short")
    token = "test-token-that-is-at-least-24-characters"
    monkeypatch.setenv(rc.TOKEN_ENV, token)
    assert rc.configured()
    assert rc.authorized(token)
    assert not rc.authorized(token + "x")


def test_submit_intent_files_queues_and_teaches(monkeypatch, tmp_path):
    from mag import remote_control as rc

    monkeypatch.setattr(rc, "RECEIPTS_PATH", tmp_path / "receipts.jsonl")
    monkeypatch.setattr(
        "mag.operating_protocol.build_envelope",
        lambda goal, **kw: {
            "ok": True,
            "intent_id": "intent-test",
            "execution": {"provider": "deepseek", "seat": "deepseek"},
            "routing_economics": {"objective": "cheap verified outcome"},
        },
    )
    monkeypatch.setattr("mag.peer_handoff.file_peer_handoff", lambda **kw: {"ok": True, "handoff_id": "h1"})
    monkeypatch.setattr("mag.governor_autorun.enqueue_routed", lambda *a, **kw: {"ok": True, "id": "q1"})
    monkeypatch.setattr("mag.training_events.emit", lambda *a, **kw: {"ok": True})
    out = rc.submit_intent({"goal": "Implement the bounded task and run tests", "depth": "job"})
    assert out["ok"] is True
    assert out["status"] == "queued"
    assert out["receipt"]["queue_id"] == "q1"
    assert len(out["receipt"]["sha256"]) == 64
    assert "test-token" not in rc.RECEIPTS_PATH.read_text(encoding="utf-8")


def test_submit_intent_rejects_empty_goal():
    from mag.remote_control import submit_intent

    assert submit_intent({}) == {"ok": False, "error": "goal required"}


def test_status_has_repo_and_queue(monkeypatch):
    from mag import remote_control as rc

    monkeypatch.setattr("mag.repo_readiness.repo_readiness", lambda root: {"ok": True, "branch": "test"})
    monkeypatch.setattr("mag.orchestrator.list_queue", lambda limit=20: [{"status": "queued", "queue_id": "q1"}])
    out = rc.status()
    assert out["repo"]["branch"] == "test"
    assert out["queue"]["active"] == 1
