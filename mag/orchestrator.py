# Orchestrator - spawn isolated sub-agents per task, terminate on completion.
# THE PROBLEM (operator, 2026-08-03): the agent router does everything in one
# window/process. One crash in a tool call, a runaway loop, or a hung provider
# kills the whole session. Crashes eventually, always.
# THE FIX: one orchestration window supervises short-lived sub-agent processes.
# Each task is a fresh Python process running `main.py agent --query "<goal>"`
# in one-shot mode. The orchestrator:
#   spawn   - write task spec, Popen the child, return task_id (window stays up)
#   monitor - finalize record on child exit (done/failed) or stall/timeout (kill)
#   reap    - clean stale records whose pid is dead
#   kill    - terminate a running task (process tree on Windows)
#   steer / pause / continue - live knot commands via the task's pigeonhole
#              mailbox (memory/mail/<task_id>/inbox.txt). stdin is DEVNULL in
#              sub-agents, so the KNOT is the channel - not a pipe, not a timer.
# Crash containment: a sub-agent crash kills ONLY that process. The orchestrator
# window survives, records the failure, and the operator can retry or escalate.
# Crash RECOGNITION is live: the child writes heartbeat beads + status.json into
# its mailbox; staleness detection nudges (!steer) before ever killing, and the
# hard timeout is only the final backstop. The seat's own crash recognizers
# (collapse detector, empty-response retry, seat-crash-guard) now surface to the
# supervisor immediately via status.json phase (collapse_stop/empty_stop/crashed)
# instead of being invisible until exit.
# Frontier fidelity: mirrors Claude Code Task / Anthropic agent-SDK subagents -
# explicit input contract (goal string), isolated tool process, result capture
# (exit code + log), hard timeout, terminate on completion, parent survival.
# Usage (via main.py):
#   python main.py orchestrator run "<goal>" [--provider deepseek] [--timeout 900] [--tag label] [--wait]
#   python main.py orchestrator list
#   python main.py orchestrator status <id> [--tail 20]
#   python main.py orchestrator steer <id> "<context>"
#   python main.py orchestrator pause <id> | continue <id>
#   python main.py orchestrator watch <id>   (poll heartbeat freshness)
#   python main.py orchestrator kill <id>
#   python main.py orchestrator reap
#   python main.py orchestrator self-test
#   python main.py orchestrator queue add "<goal>" [--provider X] [--timeout N] [--tag L]
#   python main.py orchestrator queue list | status
#   python main.py orchestrator drain [--once]   (auto-advance through the queue)
from __future__ import annotations
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path


def dim(s: str) -> str:
    """Minimal dim fallback (agent_cli has the ANSI variant)."""
    if sys.stdout.isatty():
        return "\033[2m" + s + "\033[0m"
    return s
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TASK_DIR = ROOT / "memory" / "runs" / "orchestrator" / "tasks"
QUEUE_DIR = ROOT / "memory" / "runs" / "orchestrator" / "queue"
LOG_DIR = ROOT / "logs" / "orchestrator"
TRAIL = ROOT / "memory" / "runs" / "orchestrator_trail.jsonl"
DEFAULT_TIMEOUT = 900  # seconds
IMPROVE_TIMEOUT = 420  # shorter backstop for [improve] loops (7 min)
EXTERNAL_STALE_S = 300  # external/desktop seats without pid — reap after stale heartbeat

TERMINAL = {"done", "failed", "timeout", "stalled", "killed", "died"}


def timeout_for_goal(goal: str, *, tag: str = "", timeout: int | None = None) -> int:
    """Pick spawn timeout — improve jobs get a shorter backstop."""
    if timeout is not None and timeout != DEFAULT_TIMEOUT:
        return int(timeout)
    g = (goal or "").lower()
    t = (tag or "").lower()
    if "[improve]" in g or t.startswith("improve"):
        return IMPROVE_TIMEOUT
    return DEFAULT_TIMEOUT


def _is_external_task(task: dict[str, Any]) -> bool:
    src = str(task.get("source") or "")
    if src in ("external", "desktop", "cursor", "cloud", "seat_guard", "launcher"):
        return True
    tid = str(task.get("task_id") or "")
    return tid.startswith("ext-") or tid.startswith("seat-")


def register_external(
    goal: str = "",
    *,
    seat: str = "cursor",
    platform: str = "cursor",
    mode: str = "interactive",
    task_id: str | None = None,
    pid: int | None = None,
    tag: str = "",
    parent: str = "desktop",
) -> dict[str, Any]:
    """Register a desktop/cloud seat — visible in list_tasks_live + switchboard steer."""
    _ensure_dirs()
    task_id = (task_id or "").strip() or ("ext-" + uuid.uuid4().hex[:10])
    task: dict[str, Any] = {
        "task_id": task_id,
        "tag": tag or f"{seat}-external",
        "status": "running",
        "source": "external",
        "seat": seat,
        "platform": platform,
        "mode": mode,
        "parent": parent,
        "goal": (goal or "")[:500],
        "cmd": [],
        "created_at": _now(),
        "started_at": _now(),
        "ended_at": None,
        "exit_code": None,
        "timeout_s": None,
        "log": "",
        "detail": f"registered:{parent}",
        "pid": pid,
    }
    _save(task)
    _trail("register_external", task_id, seat=seat, mode=mode, parent=parent)
    ph = _ph()
    if ph is not None:
        try:
            ph.heartbeat(task_id, seat=seat, phase="registered", source=parent)
            ph.write_status(task_id, phase="registered", seat=seat, goal=task["goal"][:200])
        except Exception:
            pass
    task["ok"] = True
    return task


def touch_external(task_id: str, **fields: Any) -> dict[str, Any] | None:
    """Update last_seen on an external task record."""
    task = _load(task_id)
    if not task:
        return None
    task["last_seen_at"] = _now()
    for k, v in fields.items():
        if v is not None and k in ("phase", "goal", "seat", "pid", "detail"):
            task[k] = v
    _save(task)
    return task


def finalize_external(task_id: str, *, status: str = "done", detail: str = "") -> dict[str, Any]:
    """Terminal state for external seats (no process kill)."""
    task = _load(task_id)
    if not task:
        return {"ok": False, "error": "no such task", "task_id": task_id}
    if task.get("status") in TERMINAL:
        return {"ok": True, "task": task, "note": "already terminal"}
    task = _finalize(task_id, status, detail=detail or f"external:{status}") or task
    return {"ok": True, "task": task}


def list_external_tasks(*, limit: int = 50) -> list[dict[str, Any]]:
    """Running/ recent external task records enriched with heartbeat."""
    out: list[dict[str, Any]] = []
    ph = _ph()
    for t in list_tasks(limit=limit):
        if not _is_external_task(t):
            continue
        tid = str(t.get("task_id") or "")
        if ph is not None and t.get("status") in ("running", "queued"):
            try:
                t["heartbeat_age_s"] = ph.staleness_s(tid)
                t["alive"] = ph.alive(tid)
                st = ph.read_status(tid)
                if st:
                    t["phase"] = st.get("phase")
            except Exception:
                pass
        t["peer_id"] = f"ext:{tid}"
        t["why"] = [f"external:{t.get('parent', 'desktop')}"]
        out.append(t)
    return out


def _ph() -> Any:
    """Lazy import of the pigeonhole mailbox (knot channel)."""
    try:
        from mag import pigeonhole as ph
        return ph
    except Exception:
        return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dirs() -> None:
    TASK_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def _task_path(task_id: str) -> Path:
    return TASK_DIR / (task_id + ".json")


def _load(task_id: str) -> dict[str, Any] | None:
    p = _task_path(task_id)
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save(task: dict[str, Any]) -> None:
    _ensure_dirs()
    _task_path(task["task_id"]).write_text(
        json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _goal_from_cmd(cmd: list[str] | None) -> str:
    cmd = cmd or []
    if "--query" in cmd:
        i = cmd.index("--query")
        if i + 1 < len(cmd):
            return str(cmd[i + 1])[:240]
    return ""


def _provider_from_cmd(cmd: list[str] | None) -> str:
    cmd = cmd or []
    if "--provider" in cmd:
        i = cmd.index("--provider")
        if i + 1 < len(cmd):
            return str(cmd[i + 1])
    return "deepseek"


def _emit_task_lifecycle(phase: str, task_id: str, **extra: Any) -> None:
    """Training hook — spawn/terminal edges for improve + seat posterior."""
    try:
        from mag.training_events import emit

        task = _load(task_id) or {}
        cmd = task.get("cmd") or []
        emit(
            "task_lifecycle",
            join={"task_id": task_id},
            input_data={
                "goal": (task.get("goal") or _goal_from_cmd(cmd))[:200],
                "provider": task.get("provider") or _provider_from_cmd(cmd),
                "tag": task.get("tag") or "",
            },
            action={"phase": phase, **extra},
            outcome={
                "status": task.get("status"),
                "exit_code": task.get("exit_code"),
                "duration_s": task.get("duration_s"),
            },
            pattern_tags=[f"orc_{phase}"],
        )
    except Exception:
        pass


def _trail(event: str, task_id: str, **meta: Any) -> None:
    _ensure_dirs()
    entry = {"timestamp": _now(), "event": event, "task_id": task_id, **meta}
    with TRAIL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _kill_tree(pid: int) -> None:
    """Terminate the process and its children (Windows process tree)."""
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True, timeout=30,
            )
        except Exception:
            pass
    else:
        try:
            os.kill(pid, 9)
        except (ProcessLookupError, PermissionError):
            pass


def _pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    # Prefer psutil on Windows: os.kill(pid, 0) is unreliable there (returns
    # True for recycled/dead pids), which left zombies stuck in "running".
    try:
        import psutil

        return psutil.pid_exists(pid)
    except Exception:
        pass
    if sys.platform == "win32":
        # psutil-free liveness: tasklist filter is authoritative. os.kill(pid, 0)
        # is NOT a probe on Windows - sig 0 means TerminateProcess, and it can
        # return success on already-dead pids whose handle is still open, so a
        # supervisor would never reap zombies. (Found 2026-08-03: env without
        # psutil -> reap_stale/kill verification silently broken.)
        try:
            r = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True, text=True, timeout=15,
            )
            return str(pid) in (r.stdout or "")
        except Exception:
            pass
        return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False
    except OSError:
        return False


def _finalize(task_id: str, status: str, exit_code: int | None = None,
              detail: str = "", killed: bool = False) -> dict[str, Any] | None:
    task = _load(task_id)
    if not task:
        return None
    if task.get("status") in TERMINAL:
        return task
    task["status"] = status
    task["exit_code"] = exit_code
    task["detail"] = detail
    task["ended_at"] = _now()
    if task.get("started_at"):
        try:
            s = datetime.fromisoformat(task["started_at"])
            e = datetime.fromisoformat(task["ended_at"])
            task["duration_s"] = round((e - s).total_seconds(), 1)
        except Exception:
            pass
    _save(task)
    _trail(status, task_id, exit_code=exit_code, detail=detail, killed=killed)
    _emit_task_lifecycle(status, task_id, killed=killed, detail=(detail or "")[:120])
    try:
        from mag.tripartite_boot import weave_terminal

        weave_terminal(task_id=task_id, status=status, detail=detail)
    except Exception:
        pass
    return task


def _creation_flags() -> int:
    if sys.platform != "win32":
        return 0
    # own process group so taskkill /T can reap children; not detached (we log)
    return getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)


def _spawn_cmd(cmd: list[str], *, task_id: str, timeout: int,
               tag: str = "") -> dict[str, Any]:
    """Popen a child command and supervise it in a daemon thread."""
    _ensure_dirs()
    log_path = LOG_DIR / (task_id + ".out.log")
    log_fh = log_path.open("a", encoding="utf-8", errors="replace")
    log_fh.write("--- %s spawn: %s\n" % (_now(), " ".join(cmd)))
    log_fh.flush()

    env = dict(os.environ)
    env["MAG_AGENT_SESSION"] = "orc-" + task_id
    env["MAG_TASK_ID"] = task_id  # pigeonhole mailbox: knot channel for the seat
    env["NO_COLOR"] = "1"
    env.setdefault("PYTHONIOENCODING", "utf-8")

    task: dict[str, Any] = {
        "task_id": task_id,
        "tag": tag,
        "status": "running",
        "cmd": cmd,
        "created_at": _now(),
        "started_at": None,
        "ended_at": None,
        "exit_code": None,
        "timeout_s": timeout,
        "log": str(log_path),
        "detail": "",
    }
    _save(task)

    try:
        proc = subprocess.Popen(
            cmd, stdout=log_fh, stderr=subprocess.STDOUT, env=env,
            cwd=str(ROOT), creationflags=_creation_flags(),
            stdin=subprocess.DEVNULL,  # sub-agents never read stdin; else they hang on input()
        )
    except Exception as e:
        log_fh.close()
        _finalize(task_id, "failed", detail="spawn error: " + str(e))
        return _load(task_id) or task

    task = _load(task_id) or task
    task["pid"] = proc.pid
    task["started_at"] = _now()
    _save(task)
    _trail("spawn", task_id, pid=proc.pid, timeout_s=timeout)
    _emit_task_lifecycle("spawn", task_id, pid=proc.pid, timeout_s=timeout)
    try:
        from mag.tripartite_boot import weave_spawn

        weave_spawn(
            task_id=task_id,
            goal=_goal_from_cmd(cmd),
            provider=_provider_from_cmd(cmd),
            pid=proc.pid,
            tag=tag,
        )
    except Exception:
        pass

    def _monitor() -> None:
        """Supervise: exit -> finalize; stall -> nudge (!steer) then kill;
        hard timeout remains the last-resort backstop only."""
        started = time.time()
        stall_polls = 0
        nudged = False
        ph = _ph()
        while True:
            rc = proc.poll()
            if rc is not None:
                log_fh.close()
                _finalize(task_id, "done" if rc == 0 else "failed",
                          exit_code=rc, detail="exit" if rc == 0 else "non-zero exit %s" % rc)
                return
            elapsed = time.time() - started
            if elapsed > timeout:
                _kill_tree(proc.pid)
                log_fh.close()
                _finalize(task_id, "timeout", exit_code=None,
                          detail="exceeded %ss" % timeout, killed=True)
                return
            # Live crash/stall recognition via the knot: heartbeat staleness.
            # A healthy agent writes a bead every 15s. No bead -> nudge once
            # through the mailbox (!steer re-anchor); if it stays silent, kill
            # as "stalled" instead of burning the whole timeout.
            age = None
            stall_after = None
            if ph is not None:
                try:
                    age = ph.staleness_s(task_id)
                    stall_after = ph.STALL_AFTER_S
                except Exception:
                    age = None
            if age is None or stall_after is None or age < stall_after:
                stall_polls = 0  # healthy (or still starting): reset the counter
            else:
                stall_polls += 1
                if stall_polls == 2 and not nudged:
                    nudged = True
                    try:
                        from mag import supervisor as _sup
                        ph.post_steer(task_id, _sup.stall_nudge_text(task_id, age))
                        _trail("stall-nudge", task_id, age_s=age, receipts=True)
                        print(dim("  [orchestrator] stall-nudge %s (no heartbeat %ss)" % (task_id, age)), flush=True)
                    except Exception:
                        pass
                elif stall_polls >= 6:  # ~30s after the nudge threshold
                    defer_kill = False
                    try:
                        from mag.run_worth import evaluate_task_hung

                        hung_eval = evaluate_task_hung(task_id)
                        defer_kill = bool(hung_eval.get("defer_kill"))
                        if hung_eval.get("hung"):
                            defer_kill = False
                    except Exception:
                        hung_eval = {}
                    if defer_kill and stall_polls < 10:
                        stall_polls = 4  # one grace cycle when worth uncertain
                        _trail(
                            "stall-defer-worth",
                            task_id,
                            age_s=age,
                            verdict=(hung_eval or {}).get("verdict"),
                        )
                    else:
                        _kill_tree(proc.pid)
                        log_fh.close()
                        detail = "no heartbeat for %ss" % age
                        if hung_eval.get("hung"):
                            detail = "hung: %s" % (hung_eval.get("reason") or detail)
                        _finalize(task_id, "stalled", exit_code=None,
                                  detail=detail, killed=True)
                        return
            time.sleep(5.0)

    threading.Thread(target=_monitor, daemon=True).start()
    return _load(task_id) or task
def _running_tasks() -> list[dict[str, Any]]:
    """All non-terminal task records (running/stalled/starting)."""
    _ensure_dirs()
    out = []
    for p in TASK_DIR.glob("*.json"):
        try:
            t = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if t.get("status") not in TERMINAL:
            out.append(t)
    return out


def spawn_task(goal: str, *, provider: str = "ollama", model: str | None = None,
               timeout: int = DEFAULT_TIMEOUT, tag: str = "",
               require_build: str | None = None) -> dict[str, Any]:
    """Spawn a one-shot sub-agent for a goal. Returns the task record (async).

    Same-goal dedupe (2026-08-03): if a non-terminal task with the SAME goal
    already exists, refuse to spawn a duplicate and return the existing task
    instead. Prevents the 8-identical-smoke-spawns pattern from session mining.
    """
    goal = goal.strip()
    if not goal:
        return {"ok": False, "error": "empty goal"}
    from mag.factory_gate import check_frozen_build

    build_gate = check_frozen_build(goal, require_build=require_build)
    if not build_gate.get("ok"):
        return {"ok": False, "error": build_gate.get("reason"), "factory_gate": build_gate}

    if goal.lower().startswith("[steward]"):
        try:
            from mag.steward import execute_steward_goal

            res = execute_steward_goal(goal, dry=False)
            tid = "t-steward-" + uuid.uuid4().hex[:8]
            status = "done" if res.get("ok") else "failed"
            rec: dict[str, Any] = {
                "ok": res.get("ok", False),
                "task_id": tid,
                "goal": goal,
                "status": status,
                "provider": "ollama",
                "tag": tag or "steward",
                "detail": str(res.get("path") or res.get("reason") or res.get("error") or "")[:300],
                "steward_result": res,
                "created_at": _now(),
                "ended_at": _now(),
            }
            _ensure_dirs()
            _save(rec)
            _trail("steward-inline", tid, goal=goal[:120], ok=res.get("ok"))
            return rec
        except Exception as exc:
            return {"ok": False, "error": f"steward: {exc}"}

    timeout = timeout_for_goal(goal, tag=tag, timeout=timeout)
    for t in _running_tasks():
        if t.get("goal") == goal:
            return {
                "ok": False,
                "error": f"duplicate goal already running: {t['task_id']}",
                "existing": t["task_id"],
                "status": t.get("status"),
            }
    task_id = "t" + uuid.uuid4().hex[:10]
    try:
        from mag.autorun_common import refresh_context_for_goal

        refresh_context_for_goal(goal)
    except Exception:
        pass
    cmd = [sys.executable, str(ROOT / "main.py"), "agent", "--query", goal,
           "--provider", provider]
    if build_gate.get("required"):
        cmd += ["--tier", str(build_gate.get("tier") or "T1")]
    if model:
        cmd += ["--model", model]
    rec = _spawn_cmd(cmd, task_id=task_id, timeout=timeout, tag=tag)
    rec["ok"] = True
    rec["goal"] = goal
    return rec


# ---------------------------------------------------------------------------
# Task queue: enqueue goals, drain them sequentially (auto-advance).
# The operator's recurring ask: "the orchestrator didn't move onto the next
# task automatically." spawn_task() is one-shot (spawn + return). This queue
# gives a list of goals that a drain loop processes one at a time, spawning
# the next queued goal the moment the current one reaches a terminal state.
# ---------------------------------------------------------------------------
QUEUE_TERMINAL = {"done", "failed", "timeout", "stalled", "killed", "died"}


def _queue_path(queue_id: str) -> Path:
    return QUEUE_DIR / (queue_id + ".json")


def _queue_load(queue_id: str) -> dict[str, Any] | None:
    p = _queue_path(queue_id)
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _queue_save(q: dict[str, Any]) -> None:
    _ensure_dirs()
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    _queue_path(q["queue_id"]).write_text(
        json.dumps(q, ensure_ascii=False, indent=2), encoding="utf-8")


def enqueue(goal: str, *, provider: str = "ollama", model: str | None = None,
            timeout: int = DEFAULT_TIMEOUT, tag: str = "",
            require_build: str | None = None) -> dict[str, Any]:
    """Add a goal to the queue. Returns the queue entry (not yet spawned)."""
    goal = goal.strip()
    if not goal:
        return {"ok": False, "error": "empty goal"}
    from mag.factory_gate import check_frozen_build

    build_gate = check_frozen_build(goal, require_build=require_build)
    if not build_gate.get("ok"):
        return {"ok": False, "error": build_gate.get("reason"), "factory_gate": build_gate}
    try:
        from mag.loop_audit import _goal_key

        norm = _goal_key(goal)
        for q in list_queue(limit=80):
            if q.get("status") not in ("queued", "running"):
                continue
            if _goal_key(str(q.get("goal") or "")) == norm:
                return {
                    "ok": False,
                    "error": "duplicate goal already queued",
                    "existing_queue_id": q.get("queue_id"),
                    "goal": goal[:120],
                }
    except Exception:
        pass
    timeout = timeout_for_goal(goal, tag=tag, timeout=timeout)
    q = {
        "queue_id": "q" + uuid.uuid4().hex[:10],
        "goal": goal,
        "provider": provider,
        "model": model,
        "timeout": timeout,
        "tag": tag,
        "build_spec": build_gate.get("spec_path"),
        "created_at": _now(),
        "status": "queued",   # queued -> running -> done/failed
        "task_id": None,
        "detail": "",
    }
    try:
        from mag.cost_ledger import task_estimate

        q["task_estimate"] = task_estimate(goal, provider=provider, model=model)
    except Exception:
        pass
    _queue_save(q)
    _trail("queue-add", q["queue_id"], goal=goal[:120], tag=tag)
    q["ok"] = True
    return q


def list_queue(limit: int = 100) -> list[dict[str, Any]]:
    """All queue entries, newest first, with live task linkage."""
    _ensure_dirs()
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for p in sorted(QUEUE_DIR.glob("*.json"), reverse=True)[:limit]:
        try:
            q = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        # Link live task status so the queue view shows real progress.
        if q.get("task_id"):
            t = _load(q["task_id"])
            if t:
                q["task_status"] = t.get("status")
                q["task_detail"] = t.get("detail")
        out.append(q)
    return out


def _next_queued() -> dict[str, Any] | None:
    """Oldest queued (not yet running) entry, or None."""
    _ensure_dirs()
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    best = None
    for p in QUEUE_DIR.glob("*.json"):
        try:
            q = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if q.get("status") != "queued":
            continue
        if best is None or q.get("created_at", "") < best.get("created_at", ""):
            best = q
    return best


def _any_running_task() -> bool:
    """True if any task is live: a non-terminal task record OR a queue entry
    still in 'running' state (spawned from the queue, not yet finished)."""
    if _running_tasks():
        return True
    # A queue entry in "running" means we spawned it and it hasn't finished.
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    for p in QUEUE_DIR.glob("*.json"):
        try:
            q = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if q.get("status") == "running":
            return True
    return False


def _reconcile_queue() -> int:
    """Mark queue entries done/failed when their linked task is terminal.

    The queue entry stays "running" while its sub-agent is live. When the
    task record reaches a terminal state, this flips the queue entry to match
    so the drain loop can advance to the next goal. Returns entries reconciled.
    """
    _ensure_dirs()
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    fixed = 0
    for p in QUEUE_DIR.glob("*.json"):
        try:
            q = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if q.get("status") != "running":
            continue
        tid = q.get("task_id")
        if not tid:
            continue
        t = _load(tid)
        if t and t.get("status") in TERMINAL:
            q["status"] = "done" if t.get("status") == "done" else "failed"
            q["detail"] = t.get("detail") or t.get("status")
            _queue_save(q)
            _trail("queue-end", q["queue_id"], task_status=t.get("status"))
            try:
                from mag.cost_ledger import emit_terminal

                emit_terminal(q, t)
            except Exception:
                pass
            fixed += 1
    return fixed


def drain_once(*, force: bool = False) -> dict[str, Any]:
    """Spawn the next queued goal IF no task is currently running.

    This is the auto-advance: call it in a loop (or from a timer) and the
    queue drains one goal at a time, moving to the next the moment the
    current one finishes. Returns what happened.
    """
    try:
        from mag.autorun_common import autorun_pause_reason

        pause = None if force else autorun_pause_reason()
        if pause:
            return {"ok": True, "action": "paused", "detail": pause}
    except Exception:
        pass
    _ensure_dirs()
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    _reconcile_queue()
    if _any_running_task():
        return {"ok": True, "action": "busy", "detail": "a task is already running"}
    nxt = _next_queued()
    if nxt is None:
        return {"ok": True, "action": "empty", "detail": "no queued goals"}
    qid = nxt["queue_id"]
    rec = spawn_task(nxt["goal"], provider=nxt.get("provider") or "ollama",
                     model=nxt.get("model"), timeout=int(nxt.get("timeout") or DEFAULT_TIMEOUT),
                     tag=nxt.get("tag") or "")
    if not rec.get("ok"):
        q = _queue_load(qid) or nxt
        q["status"] = "failed"
        q["detail"] = rec.get("error", "spawn failed")
        _queue_save(q)
        _trail("queue-fail", qid, error=rec.get("error", ""))
        return {"ok": False, "action": "spawn_failed", "queue_id": qid,
                "detail": rec.get("error", "")}
    q = _queue_load(qid) or nxt
    q["status"] = "running"
    q["task_id"] = rec["task_id"]
    q["detail"] = "spawned"
    q["usage_started_at"] = _now()
    _queue_save(q)
    _trail("queue-start", qid, spawned_task_id=rec["task_id"])
    try:
        from mag.tripartite_boot import weave_drain

        weave_drain(
            action="started",
            goal=nxt.get("goal", ""),
            task_id=rec.get("task_id", ""),
            queue_id=qid,
        )
    except Exception:
        pass
    return {"ok": True, "action": "started", "queue_id": qid,
            "task_id": rec["task_id"], "goal": nxt["goal"][:120]}


def drain_loop(interval_s: float = 5.0, *, once: bool = False) -> None:
    """Run drain_once repeatedly so the queue auto-advances.

    `once=True` runs a single drain pass and returns (for smoke tests / CLI).
    Otherwise loops forever (Ctrl-C to stop), spawning the next queued goal
    whenever the current one finishes.

    Set MAG_AUTOPILOT_EVERY=N to run autopilot_once every N drain cycles
    (e.g. 60 ≈ 5 min at 5s interval) when drainer is on.
    """
    autopilot_every = int(os.environ.get("MAG_AUTOPILOT_EVERY", "0") or "0")
    tick = 0
    while True:
        try:
            res = drain_once()
            if res.get("action") in ("started", "spawn_failed"):
                print(dim("  [queue] %s %s" % (res.get("action"), res.get("detail", ""))), flush=True)
        except Exception as e:
            print(dim("  [queue] drain error: %s" % e), flush=True)
        tick += 1
        if autopilot_every > 0 and tick % autopilot_every == 0:
            try:
                from mag.autopilot import autopilot_once

                ap = autopilot_once(queue_improve=True, governor=True, drain=False, max_queue=1)
                print(dim("  [autopilot] seed=%s steps=%s" % (
                    ap.get("seed_mirror", {}).get("hint", "?")[:60],
                    len(ap.get("steps") or []),
                )), flush=True)
            except Exception as e:
                print(dim("  [autopilot] error: %s" % e), flush=True)
        if once:
            return
        time.sleep(interval_s)


def queue_status() -> dict[str, Any]:
    """Summary of the queue: counts by status + the running task id."""
    entries = list_queue()
    counts: dict[str, int] = {}
    running = None
    for q in entries:
        st = q.get("status") or "?"
        counts[st] = counts.get(st, 0) + 1
        if st == "running":
            running = q.get("task_id")
    return {"ok": True, "total": len(entries), "counts": counts,
            "running_task_id": running}


def list_tasks(limit: int = 20) -> list[dict[str, Any]]:
    _ensure_dirs()
    out: list[dict[str, Any]] = []
    # IDs are random and therefore not chronological. Fleet/handoff views need
    # the records most recently written, especially when many old tasks exist.
    for p in sorted(TASK_DIR.glob("*.json"), key=lambda item: item.stat().st_mtime_ns, reverse=True)[:limit]:
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            pass
    return out


def list_tasks_live(limit: int = 50) -> list[dict[str, Any]]:
    """Fleet view WITH live knot state (phase, heartbeat age, alive) — the
    dashboard feeds from this so the tab shows agents as they really are:
    fresh, stale, departed. Raw list_tasks() stays for CLI/orchestrator use."""
    tasks = list_tasks(limit=limit)
    ph = _ph()
    for t in tasks:
        if not t.get("goal"):
            cmd = t.get("cmd") or []
            try:
                i = cmd.index("--query")
                if i + 1 < len(cmd):
                    t["goal"] = cmd[i + 1]
            except ValueError:
                pass

        if t.get("status") not in ("running", "queued"):
            continue
        if ph is None:
            continue
        try:
            t["heartbeat_age_s"] = ph.staleness_s(t["task_id"])
            t["alive"] = ph.alive(t["task_id"])
            st = ph.read_status(t["task_id"])
            if st:
                t["phase"] = st.get("phase")
                t["agent_ts"] = st.get("ts")
        except Exception:
            pass
    return tasks


def task_status(task_id: str) -> dict[str, Any] | None:
    t = _load(task_id)
    if not t:
        return None
    # Live knot view: heartbeat freshness + agent-reported phase. This is the
    # crash recognizer the supervisor sees — not a timeout countdown.
    ph = _ph()
    if ph is not None:
        try:
            t["heartbeat_age_s"] = ph.staleness_s(task_id)
            t["alive"] = ph.alive(task_id)
            st = ph.read_status(task_id)
            if st:
                t["phase"] = st.get("phase")
                t["agent_ts"] = st.get("ts")
        except Exception:
            pass
    return t


def kill_task(task_id: str) -> dict[str, Any]:
    task = _load(task_id)
    if not task:
        return {"ok": False, "error": "no such task"}
    if task.get("status") in TERMINAL:
        return {"ok": True, "task": task, "note": "already terminal"}
    pid = task.get("pid")
    if pid:
        _kill_tree(pid)
    return {"ok": True, "task": _finalize(task_id, "killed",
                                          detail="operator kill", killed=True)}


def reap_stale() -> dict[str, Any]:
    """Mark running tasks whose pid is dead as died (parent survived a crash)."""
    _ensure_dirs()
    fixed = 0
    for p in TASK_DIR.glob("*.json"):
        try:
            t = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if t.get("status") != "running":
            continue
        pid = t.get("pid")
        if pid and not _pid_alive(pid):
            _finalize(t["task_id"], "died", detail="pid gone (parent survived)")
            fixed += 1
            continue
        # External/desktop seats: no pid — reap on stale pigeonhole heartbeat
        if not pid and _is_external_task(t):
            ph = _ph()
            if ph is None:
                continue
            try:
                age = ph.staleness_s(t["task_id"])
            except Exception:
                age = None
            if age is not None and age > EXTERNAL_STALE_S:
                _finalize(
                    t["task_id"],
                    "died",
                    detail=f"external heartbeat stale {age}s",
                )
                fixed += 1
    return {"ok": True, "reaped": fixed}


def respawn_dead(max_per_task: int = 2) -> dict[str, Any]:
    """Watchdog: mark dead-pid running tasks as died, then re-spawn them
    (bounded retries) with the same command. Auto-heal for the fleet."""
    _ensure_dirs()
    reaped = 0
    respawned: list[dict[str, Any]] = []
    for p in TASK_DIR.glob("*.json"):
        try:
            t = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if t.get("status") != "running":
            continue
        pid = t.get("pid")
        if not (pid and not _pid_alive(pid)):
            continue
        old_id = t["task_id"]
        rc = int(t.get("respawn_count", 0) or 0)
        if rc >= max_per_task:
            _finalize(old_id, "died", detail="pid gone (watchdog), respawns exhausted")
            reaped += 1
            continue
        _finalize(old_id, "died", detail="pid gone (watchdog), respawning")
        reaped += 1
        cmd = t.get("cmd") or []
        if not cmd or cmd[0] != sys.executable:
            continue  # not a respawnable agent cmd
        new_id = "t" + uuid.uuid4().hex[:10]
        nrec = _spawn_cmd(cmd, task_id=new_id,
                          timeout=int(t.get("timeout_s") or DEFAULT_TIMEOUT),
                          tag=str(t.get("tag") or ""))
        nrec["respawn_of"] = old_id
        nrec["respawn_count"] = rc + 1
        nrec["goal"] = t.get("goal", "")
        _save(nrec)
        _trail("respawn", new_id, from_task=old_id, count=rc + 1)
        respawned.append(nrec)
    return {"ok": True, "reaped": reaped, "respawned": respawned}


def tail_log(task_id: str, n: int = 20) -> str:
    p = LOG_DIR / (task_id + ".out.log")
    if not p.is_file():
        return "no log yet"
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-n:])


def self_test() -> dict[str, Any]:
    """Spawn a trivial python child; assert it completes with status done."""
    task_id = "t" + uuid.uuid4().hex[:10]
    cmd = [sys.executable, "-c", "print('orc-self-test-ok')"]
    rec = _spawn_cmd(cmd, task_id=task_id, timeout=60, tag="self-test")
    t = rec
    import time
    for _ in range(60):
        t = _load(task_id) or {}
        if t.get("status") in TERMINAL:
            break
        time.sleep(0.5)
    ok = t.get("status") == "done" and t.get("exit_code") == 0
    return {"ok": ok, "task": t}


def main(argv: list[str] | None = None) -> int:
    args = list(argv) if argv else sys.argv[1:]
    if not args:
        print("usage: orchestrator run|list|status|kill|reap|self-test")
        return 2
    cmd = args[0]
    if cmd == "self-test":
        print(json.dumps(self_test(), indent=2, default=str))
        return 0 if self_test()["ok"] else 1
    if cmd == "list":
        for t in list_tasks():
            print("%s %-9s %-20s %s" % (t.get("task_id", "?"), t.get("status", "?"),
                                        t.get("tag", ""), (t.get("cmd") or [""])[-1][:60]))
        return 0
    if cmd == "status":
        if len(args) < 2:
            print("need task_id")
            return 2
        t = task_status(args[1])
        if not t:
            print("no such task")
            return 1
        print(json.dumps(t, indent=2, default=str))
        tail = 0
        if "--tail" in args:
            try:
                tail = int(args[args.index("--tail") + 1])
            except (ValueError, IndexError):
                tail = 20
        if tail:
            print("--- log tail ---")
            print(tail_log(args[1], tail))
        return 0
    if cmd in ("steer", "pause", "continue"):
        if len(args) < 2:
            print("need task_id")
            return 2
        tid = args[1]
        if not _load(tid):
            print("no such task")
            return 1
        ph = _ph()
        if ph is None:
            print("pigeonhole unavailable")
            return 1
        if cmd == "steer":
            ctx = " ".join(args[2:]).strip()
            if not ctx:
                print("need steer context text")
                return 2
            ph.post_steer(tid, ctx)
            print("steer posted to %s" % tid)
        elif cmd == "pause":
            ph.post_cmd(tid, "!pause")
            print("pause posted to %s" % tid)
        else:
            ph.post_cmd(tid, "!continue")
            print("continue posted to %s" % tid)
        return 0
    if cmd == "watch":
        if len(args) < 2:
            print("need task_id")
            return 2
        tid = args[1]
        ph = _ph()
        for _ in range(60):
            t = task_status(tid)
            if not t:
                print("no such task")
                return 1
            age = t.get("heartbeat_age_s")
            phase = t.get("phase", "?")
            alive = t.get("alive")
            print("%-9s phase=%-14s heartbeat_age=%s alive=%s" % (
                t.get("status", "?"), phase,
                "?" if age is None else ("%ss" % age),
                "?" if alive is None else alive), flush=True)
            if t.get("status") in TERMINAL:
                return 0 if t.get("status") == "done" else 1
            time.sleep(5)
        return 0
    if cmd == "kill":
        if len(args) < 2:
            print("need task_id")
            return 2
        print(json.dumps(kill_task(args[1]), indent=2, default=str))
        return 0
    if cmd == "reap":
        print(json.dumps(reap_stale(), indent=2))
        return 0
    if cmd == "queue":
        sub = args[1] if len(args) > 1 else "list"
        if sub == "add":
            rest = args[2:]
            goal = ""
            provider = "ollama"
            model = None
            timeout = DEFAULT_TIMEOUT
            tag = ""
            i = 0
            while i < len(rest):
                a = rest[i]
                if a == "--provider" and i + 1 < len(rest):
                    provider = rest[i + 1]; i += 2
                elif a == "--model" and i + 1 < len(rest):
                    model = rest[i + 1]; i += 2
                elif a == "--timeout" and i + 1 < len(rest):
                    try:
                        timeout = int(rest[i + 1])
                    except ValueError:
                        pass
                    i += 2
                elif a == "--tag" and i + 1 < len(rest):
                    tag = rest[i + 1]; i += 2
                else:
                    goal = (goal + " " + a).strip(); i += 1
            if not goal:
                print("need a goal")
                return 2
            q = enqueue(goal, provider=provider, model=model,
                        timeout=timeout, tag=tag)
            print(json.dumps(q, indent=2, default=str))
            return 0 if q.get("ok") else 1
        if sub == "list":
            for q in list_queue():
                print("%s %-9s %-20s %s" % (
                    q.get("queue_id", "?"), q.get("status", "?"),
                    q.get("tag", ""), q.get("goal", "")[:60]))
            return 0
        if sub == "status":
            print(json.dumps(queue_status(), indent=2, default=str))
            return 0
        print("unknown queue subcommand: " + sub)
        return 2
    if cmd == "drain":
        once = "--once" in args
        drain_loop(interval_s=5.0, once=once)
        return 0
    if cmd == "run":
        rest = args[1:]
        goal = ""
        provider = "ollama"
        model = None
        timeout = DEFAULT_TIMEOUT
        tag = ""
        wait = False
        i = 0
        while i < len(rest):
            a = rest[i]
            if a == "--provider" and i + 1 < len(rest):
                provider = rest[i + 1]; i += 2
            elif a == "--model" and i + 1 < len(rest):
                model = rest[i + 1]; i += 2
            elif a == "--timeout" and i + 1 < len(rest):
                try:
                    timeout = int(rest[i + 1])
                except ValueError:
                    pass
                i += 2
            elif a == "--tag" and i + 1 < len(rest):
                tag = rest[i + 1]; i += 2
            elif a == "--wait":
                wait = True; i += 1
            else:
                goal = (goal + " " + a).strip(); i += 1
        if not goal:
            print("need a goal")
            return 2
        rec = spawn_task(goal, provider=provider, model=model,
                         timeout=timeout, tag=tag)
        print(json.dumps(rec, indent=2, default=str))
        if wait and rec.get("task_id"):
            import time
            tid = rec["task_id"]
            for _ in range(timeout + 1):
                t = _load(tid) or {}
                if t.get("status") in TERMINAL:
                    print("--- final ---")
                    print(json.dumps(t, indent=2, default=str))
                    print("--- log tail ---")
                    print(tail_log(tid, 40))
                    return 0 if t.get("status") == "done" else 1
                time.sleep(1)
        return 0
    print("unknown orchestrator command: " + cmd)
    return 2


if __name__ == "__main__":
    sys.exit(main())
