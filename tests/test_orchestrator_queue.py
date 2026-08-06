"""Orchestrator task queue: enqueue goals, drain sequentially (auto-advance).

The operator's recurring ask: "the orchestrator didn't move onto the next task
automatically." spawn_task() is one-shot (spawn + return). This test proves the
queue drains one goal at a time, spawning the next the moment the current one
reaches a terminal state.

Hermetic: monkeypatches spawn_task to return fake task records (no LLM, no
network, no real sub-process). Uses a temp QUEUE_DIR so it never touches the
real queue.
"""
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mag import orchestrator as orc


def _fake_spawn(goal, *, provider="deepseek", model=None, timeout=900, tag=""):
    """Return a fake running task record (no real sub-process)."""
    tid = "t" + uuid.uuid4().hex[:10]
    return {
        "ok": True, "task_id": tid, "goal": goal, "status": "running",
        "provider": provider, "model": model, "timeout": timeout, "tag": tag,
        "pid": 0, "cmd": ["fake"], "created_at": orc._now(),
    }


def _make_terminal(task_id, status="done"):
    """Write a terminal task record so _any_running_task() sees it finished."""
    rec = {
        "task_id": task_id, "status": status, "exit_code": 0,
        "cmd": ["fake"], "created_at": orc._now(), "ended_at": orc._now(),
        "timeout_s": 900, "tag": "fake", "detail": "exit",
    }
    orc._save(rec)


def _isolate():
    """Point QUEUE_DIR + TASK_DIR at temp dirs so tests never touch real state."""
    import tempfile
    tmp = tempfile.mkdtemp()
    old_qdir, old_tdir = orc.QUEUE_DIR, orc.TASK_DIR
    old_spawn = orc.spawn_task
    orc.QUEUE_DIR = orc.Path(tmp) / "queue"
    orc.TASK_DIR = orc.Path(tmp) / "tasks"
    orc.QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    orc.TASK_DIR.mkdir(parents=True, exist_ok=True)
    orc.spawn_task = _fake_spawn
    return old_qdir, old_tdir, old_spawn


def _restore(old_qdir, old_tdir, old_spawn):
    orc.QUEUE_DIR, orc.TASK_DIR, orc.spawn_task = old_qdir, old_tdir, old_spawn


def test_enqueue_and_drain_sequential():
    """Two queued goals drain one at a time, auto-advancing on completion."""
    old_qdir, old_tdir, old_spawn = _isolate()
    try:
        q1 = orc.enqueue("goal one", tag="q-test")
        q2 = orc.enqueue("goal two", tag="q-test")
        assert q1.get("ok") and q2.get("ok")
        assert q1.get("status") == "queued"
        assert q2.get("status") == "queued"

        # First drain: no task running -> spawns goal one.
        r1 = orc.drain_once(force=True)
        assert r1.get("action") == "started", f"expected started: {r1}"
        assert r1.get("goal") == "goal one"
        tid1 = r1["task_id"]
        q1b = orc._queue_load(q1["queue_id"])
        assert q1b["status"] == "running" and q1b["task_id"] == tid1

        # Second drain while task one is still running -> busy, no spawn.
        r2 = orc.drain_once(force=True)
        assert r2.get("action") == "busy", f"expected busy: {r2}"

        # Task one finishes -> next drain spawns goal two.
        _make_terminal(tid1, "done")
        r3 = orc.drain_once(force=True)
        assert r3.get("action") == "started", f"expected started: {r3}"
        assert r3.get("goal") == "goal two"
        tid2 = r3["task_id"]
        q2b = orc._queue_load(q2["queue_id"])
        assert q2b["status"] == "running" and q2b["task_id"] == tid2

        # Task two finishes -> queue empty.
        _make_terminal(tid2, "done")
        r4 = orc.drain_once(force=True)
        assert r4.get("action") == "empty", f"expected empty: {r4}"

        # queue_status reflects the drained state.
        st = orc.queue_status()
        assert st["total"] == 2
        assert st["counts"].get("done", 0) == 2, f"counts: {st['counts']}"
        print("PASS test_enqueue_and_drain_sequential", st["counts"])
    finally:
        _restore(old_qdir, old_tdir, old_spawn)


def test_enqueue_dedupes_same_goal():
    """Second enqueue with same normalized goal is refused."""
    old_qdir, old_tdir, old_spawn = _isolate()
    try:
        q1 = orc.enqueue("[test] dedupe smoke", tag="q-test")
        assert q1.get("ok")
        q2 = orc.enqueue("[test] dedupe smoke", tag="q-test")
        assert q2.get("ok") is False
        assert "duplicate" in str(q2.get("error", "")).lower()
        assert q2.get("existing_queue_id") == q1.get("queue_id")
        print("PASS test_enqueue_dedupes_same_goal")
    finally:
        _restore(old_qdir, old_tdir, old_spawn)


def test_drain_skips_when_running():
    """drain_once does NOT spawn a second task while one is live."""
    old_qdir, old_tdir, old_spawn = _isolate()
    try:
        orc.enqueue("only goal", tag="q-test")
        r1 = orc.drain_once(force=True)
        assert r1.get("action") == "started"
        # A second drain while running must not spawn a duplicate.
        r2 = orc.drain_once(force=True)
        assert r2.get("action") == "busy", f"expected busy: {r2}"
        entries = orc.list_queue()
        running = [e for e in entries if e.get("status") == "running"]
        assert len(running) == 1, f"expected exactly 1 running: {entries}"
        print("PASS test_drain_skips_when_running")
    finally:
        _restore(old_qdir, old_tdir, old_spawn)


def test_queue_status_counts():
    """queue_status reports queued/running/done counts correctly."""
    old_qdir, old_tdir, old_spawn = _isolate()
    try:
        orc.enqueue("a", tag="q-test")
        orc.enqueue("b", tag="q-test")
        st = orc.queue_status()
        assert st["total"] == 2
        assert st["counts"].get("queued", 0) == 2, f"counts: {st['counts']}"
        assert st["running_task_id"] is None
        print("PASS test_queue_status_counts", st["counts"])
    finally:
        _restore(old_qdir, old_tdir, old_spawn)
