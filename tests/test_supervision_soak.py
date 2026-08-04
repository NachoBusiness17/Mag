"""Run 5 refine + Run 6 beta: orchestrator + gpipes supervision soak (hermetic).

Real sub-processes via orc._spawn_cmd (no LLM, no network):
  1. short child completes -> status done, exit_code 0, log written
  2. long child killed -> status killed, pid dead (bounded grace poll),
     PARENT (orc module) survives
  3. reap_stale marks dead-pid "running" tasks as died
  4. gpipes: pipe_status refresh, collect, kill_pipe, list_pipes on a real pipe
     record pointing at real task_ids (crash containment: kill child, parent ok)

Pipe semantics: after kill_pipe, pipe.status is "partial" (tasks terminal,
not all done) - that is CORRECT, not an error.
"""
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mag import orchestrator as orc
from mag import gpipes


def _wait_terminal(task_id, timeout_s=20):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout_s:
        t = orc.task_status(task_id) or {}
        if t.get("status") in orc.TERMINAL:
            return t
        time.sleep(0.5)
    return orc.task_status(task_id) or {}


def _wait_dead(pid, timeout_s=5):
    """A supervisor verifies death: poll _pid_alive until gone (bounded)."""
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout_s:
        if not orc._pid_alive(pid):
            return True
        time.sleep(0.25)
    return False


def test_spawn_short_child_done():
    task_id = "t" + uuid.uuid4().hex[:10]
    cmd = [sys.executable, "-c", "print('soak-ok-marker')"]
    rec = orc._spawn_cmd(cmd, task_id=task_id, timeout=60, tag="soak-test")
    assert rec.get("status") == "running"
    t = _wait_terminal(task_id)
    assert t.get("status") == "done", f"expected done: {t}"
    assert t.get("exit_code") == 0, f"expected exit 0: {t}"
    log = orc.tail_log(task_id, 5)
    assert "soak-ok-marker" in log, f"log missing marker: {log}"
    print("PASS test_spawn_short_child_done", t.get("status"), t.get("exit_code"))


def test_kill_child_parent_survives():
    """Kill a running child -> status killed, pid dead, orchestrator still works."""
    task_id = "t" + uuid.uuid4().hex[:10]
    cmd = [sys.executable, "-c", "import time; time.sleep(120)"]
    rec = orc._spawn_cmd(cmd, task_id=task_id, timeout=120, tag="soak-kill")
    pid = rec.get("pid")
    assert pid, f"no pid: {rec}"
    r = orc.kill_task(task_id)
    assert r.get("ok"), f"kill failed: {r}"
    t = orc.task_status(task_id) or {}
    assert t.get("status") == "killed", f"expected killed: {t}"
    assert _wait_dead(pid), f"pid {pid} still alive {5}s after kill"
    lst = orc.list_tasks(limit=3)
    assert isinstance(lst, list), "orchestrator broken after kill"
    print("PASS test_kill_child_parent_survives", t.get("status"), "pid", pid, "dead")


def test_reap_stale_marks_dead():
    """A fabricated running task with a dead pid -> reap_stale marks died."""
    task_id = "t" + uuid.uuid4().hex[:10]
    rec = {
        "task_id": task_id,
        "status": "running",
        "pid": 999999999,  # cannot exist
        "cmd": [sys.executable, "-c", "print('x')"],
        "created_at": orc._now(),
        "timeout_s": 60,
        "tag": "soak-reap",
    }
    orc._save(rec)
    r = orc.reap_stale()
    assert r.get("ok"), f"reap failed: {r}"
    t = orc.task_status(task_id) or {}
    assert t.get("status") == "died", f"expected died: {t}"
    print("PASS test_reap_stale_marks_dead", t.get("status"))


def test_gpipes_pipe_status_kill_list():
    """Real pipe record over real task_ids: status refresh, kill, list."""
    kid = "t" + uuid.uuid4().hex[:10]
    cmd = [sys.executable, "-c", "import time; time.sleep(120)"]
    rec = orc._spawn_cmd(cmd, task_id=kid, timeout=120, tag="gpipes-soak")
    pipe_id = "p" + uuid.uuid4().hex[:10]
    pipe = {
        "pipe_id": pipe_id,
        "created_at": gpipes._now(),
        "goals": ["soak"],
        "task_ids": [kid],
        "tags": ["gpipes-soak"],
        "provider": "local",
        "timeout_s": 120,
        "status": "running",
        "tasks": [rec],
    }
    gpipes._save(pipe)
    st = gpipes.pipe_status(pipe_id)
    assert st and st.get("live") and st["live"][0]["status"] == "running"
    r = gpipes.kill_pipe(pipe_id)
    assert r.get("ok"), f"kill_pipe failed: {r}"
    # killed pipe -> tasks terminal but not all done -> "partial" (correct)
    assert r.get("status") in ("done", "partial"), f"unexpected pipe status: {r}"
    assert _wait_dead(rec.get("pid")), "child survived pipe kill"
    lp = gpipes.list_pipes(limit=50)
    assert any(p.get("pipe_id") == pipe_id for p in lp), "pipe missing from list"
    col = gpipes.collect(pipe_id, wait=0, tail=5)
    assert col.get("ok") and col["merged"]["killed"] >= 1, f"collect mismatch: {col['merged']}"
    print("PASS test_gpipes_pipe_status_kill_list", "status", r.get("status"), "merged", col["merged"])
