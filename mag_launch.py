#!/usr/bin/env python3
"""mag_launch.py - Tripartite supervisor (self-healing ecosystem launcher).

Spawns the background services and keeps them alive:

  1. Backend   - the FastAPI tool service on :8000 used by the agent seat.
  2. Engineer  - the Mag agent seat (interactive, operator-driven). Managed
                 ONLY if MAG_ENGINE_CMD is set (env); otherwise reported
                 idle, because the operator's own CLI session IS the engine
                 and we must not spawn a second seat on top of it.
  3. Scribe    - synthesis_agent.py (writes memory/running_commentary.md).
  4. Dashboard - python main.py dashboard (serves 127.0.0.1:8765).
  5. Drainer   - python main.py orchestrator drain (auto-advances the task
                 queue). OPT-IN: only started if MAG_DRAINER=1. It spawns
                 one-shot sub-agents that compete with the interactive seat,
                 so it is OFF by default.

Children are spawned DETACHED (no console window) so they survive the
supervisor's console being closed. Run this via pythonw.exe (no console) so
the supervisor itself survives too.

Usage:
  pythonw mag_launch.py            run the supervisor (blocking, no console)
  python  mag_launch.py --once     spawn, verify once, report, exit
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "logs"
STATE = ROOT / "state" / "mag_launch.json"

from config import bind_host  # noqa: E402

BIND = bind_host()

CHECK_S = 5
MUTEX_NAME = "Local\\MAGResourceHarnessSupervisor"


def _python_exe() -> str:
    """Spawn services with python.exe even when supervisor runs as pythonw."""
    venv_py = ROOT / ".venv" / "Scripts" / "python.exe"
    if venv_py.is_file():
        return str(venv_py)
    exe = sys.executable
    if exe.lower().endswith("pythonw.exe"):
        return exe[:-5] + ".exe"
    return exe


PY = _python_exe()
MIRROR_SCRIPT = ROOT / "scripts" / "run_mirror_dashboard.py"
PREFERENCES_NOTE = "off - enable in Status tab or MAG_DRAINER=1"


def _mirror_wanted() -> bool:
    if os.environ.get("MAG_NO_MIRROR", "").strip().lower() in ("1", "true", "yes"):
        return False
    if not MIRROR_SCRIPT.is_file():
        return False
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("_mag_mirror_probe", MIRROR_SCRIPT)
        if not spec or not spec.loader:
            return False
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return bool(getattr(mod, "_mirror_home", lambda: None)())
    except Exception:
        return False


def _drainer_wanted() -> bool:
    try:
        from mag.preferences import drainer_enabled

        return drainer_enabled()
    except Exception:
        return os.environ.get("MAG_DRAINER", "0").strip().lower() in ("1", "true", "yes")

# Windows: spawn detached so children survive console closes.
DETACHED = 0
if os.name == "nt":
    DETACHED = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) | \
               getattr(subprocess, "DETACHED_PROCESS", 0x00000008)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _log(msg: str) -> None:
    line = f"[{_now()}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_DIR / "mag_launch.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def _spawn(name: str, cmd: list[str]):
    out = open(LOG_DIR / f"{name}_sv.log", "ab")
    err = open(LOG_DIR / f"{name}_sv.err.log", "ab")
    p = subprocess.Popen(cmd, cwd=str(ROOT), stdout=out, stderr=err,
                         creationflags=DETACHED,
                         stdin=subprocess.DEVNULL)
    _log(f"spawned {name} pid={p.pid} cmd={' '.join(cmd)}")
    return p


class _SingleInstance:
    """Windows mutex preventing competing supervisors from owning one stack."""

    def __init__(self) -> None:
        self.handle = None
        self.already_running = False

    def acquire(self) -> bool:
        if os.name != "nt":
            return True
        import ctypes

        kernel32 = ctypes.windll.kernel32
        self.handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
        self.already_running = kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS
        return not self.already_running

    def release(self) -> None:
        if self.handle:
            import ctypes

            ctypes.windll.kernel32.CloseHandle(self.handle)
            self.handle = None


def build_slots() -> list[dict]:
    slots = [
        {
            "name": "backend",
            "cmd": [PY, "-m", "backend.server", "--host", BIND],
            "wanted": True,
            "proc": None,
            "health_url": "http://127.0.0.1:8000/health",
        },
        {
            "name": "scribe",
            "cmd": [PY, str(ROOT / "synthesis_agent.py")],
            "wanted": True,
            "proc": None,
        },
        {
            "name": "dashboard",
            "cmd": [PY, str(ROOT / "main.py"), "dashboard", "--host", BIND],
            "wanted": True,
            "proc": None,
            "health_url": "http://127.0.0.1:8765/",
        },
    ]
    if _mirror_wanted():
        slots.append({
            "name": "mirror",
            "cmd": [PY, str(MIRROR_SCRIPT)],
            "wanted": True,
            "proc": None,
            "health_url": "http://127.0.0.1:8743/",
        })
    else:
        slots.append({
            "name": "mirror",
            "cmd": [],
            "wanted": False,
            "proc": None,
            "note": "off - set MAG_MIRROR_HOME or unset MAG_NO_MIRROR=1",
        })
    # Drainer is deliberately opt-in. It can perform autonomous work while an
    # operator uses an interactive seat, so it must never start by surprise.
    if _drainer_wanted():
        slots.append({
            "name": "drainer",
            "cmd": [PY, str(ROOT / "main.py"), "orchestrator", "drain"],
            "wanted": True,
            "proc": None,
        })
    else:
        slots.append({
            "name": "drainer",
            "cmd": [],
            "wanted": False,
            "proc": None,
            "note": PREFERENCES_NOTE,
        })
    engine_cmd = os.environ.get("MAG_ENGINE_CMD", "").strip()
    if engine_cmd:
        slots.insert(0, {
            "name": "engine", "cmd": engine_cmd.split(),
            "wanted": True, "proc": None,
        })
    else:
        slots.insert(0, {
            "name": "engine", "cmd": [], "wanted": False, "proc": None,
            "note": "idle - interactive seat is operator-driven; "
                    "set MAG_ENGINE_CMD to auto-spawn",
        })
    return slots


def _pid_alive(pid: int) -> bool:
    """Cross-platform pid liveness check (no psutil dependency)."""
    if not pid:
        return False
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        h = ctypes.windll.kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
        if not h:
            return False
        try:
            ec = wintypes.DWORD()
            ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(ec))
            return ec.value == 259  # STILL_ACTIVE
        finally:
            ctypes.windll.kernel32.CloseHandle(h)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _health_ok(url: str, timeout: float = 1.5) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 300
    except Exception:
        return False


class _AdoptedProc:
    """Lightweight handle to a previously-spawned (still-alive) process.

    Lets the supervisor monitor an adopted pid for death without owning it.
    """
    def __init__(self, pid: int):
        self.pid = pid

    def poll(self) -> int | None:
        return None if _pid_alive(self.pid) else 0


def _load_previous_pids() -> dict[str, int]:
    """Read last-known pids from state file (for adopt-not-duplicate)."""
    try:
        data = json.loads(STATE.read_text(encoding="utf-8"))
        return {k: int(v) for k, v in data.get("pids", {}).items() if v}
    except Exception:
        return {}


def _pids_on_port(port: int) -> list[int]:
    if os.name != "nt":
        return []
    try:
        out = subprocess.check_output(
            ["netstat", "-ano"],
            text=True,
            errors="replace",
        )
    except (OSError, subprocess.CalledProcessError):
        return []
    pids: set[int] = set()
    token = f":{port} "
    for line in out.splitlines():
        if "LISTENING" not in line or token not in line:
            continue
        parts = line.split()
        if parts and parts[-1].isdigit():
            pids.add(int(parts[-1]))
    return sorted(pids)


def _collect_mag_pids() -> set[int]:
    """All PIDs belonging to this project's supervised stack."""
    targets: set[int] = set()
    try:
        data = json.loads(STATE.read_text(encoding="utf-8"))
        sup = int(data.get("supervisor_pid") or 0)
        if sup:
            targets.add(sup)
        for pid in (data.get("pids") or {}).values():
            if pid:
                targets.add(int(pid))
    except Exception:
        pass
    mag_pid = ROOT / "watch" / "mag.pid"
    try:
        pid = int(mag_pid.read_text(encoding="utf-8").strip())
        if pid:
            targets.add(pid)
    except Exception:
        pass
    for port in (8000, 8765, 8743):
        targets.update(_pids_on_port(port))
    if os.name == "nt":
        root = str(ROOT)
        ps_cmd = (
            "Get-CimInstance Win32_Process -Filter "
            "\"Name='python.exe' OR Name='pythonw.exe'\" | "
            f"Where-Object {{ $_.CommandLine -like '*{root}*' }} | "
            "Select-Object -ExpandProperty ProcessId"
        )
        try:
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                text=True,
                errors="replace",
            )
            for line in out.splitlines():
                if line.strip().isdigit():
                    targets.add(int(line.strip()))
        except (OSError, subprocess.CalledProcessError):
            pass
    return targets


def stop_stack() -> int:
    """Stop supervisor + all Mag service processes for this project."""
    pids = _collect_mag_pids()
    if not pids:
        _log("stop: no mag processes found")
        return 0
    for pid in sorted(pids, reverse=True):
        _log(f"stop: kill pid={pid}")
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            _kill_pid(pid)
    try:
        STATE.write_text("{}", encoding="utf-8")
    except OSError:
        pass
    mag_pid = ROOT / "watch" / "mag.pid"
    try:
        mag_pid.unlink(missing_ok=True)
    except OSError:
        pass
    time.sleep(1)
    _log(f"stop: done ({len(pids)} pids targeted)")
    return 0


def ensure(slots: list[dict]) -> None:
    prev = _load_previous_pids()
    for s in slots:
        if not s["wanted"]:
            continue
        health_url = s.get("health_url")
        if health_url and _health_ok(health_url):
            p = s["proc"]
            if p is None or p.poll() is not None:
                _log(f"skip spawn {s['name']}: already listening ({health_url})")
            continue
        p = s["proc"]
        stale = prev.get(s["name"])
        if p is None and stale and _pid_alive(stale):
            if health_url and not _health_ok(health_url):
                _log(f"drop stale {s['name']} pid={stale} (health failed)")
                _kill_pid(stale)
            else:
                _log(f"adopt {s['name']} (pid={stale} still alive)")
                s["proc"] = _AdoptedProc(stale)
                continue
        if p is None or p.poll() is not None:
            if p is not None:
                _log(f"respawn {s['name']} (was pid={p.pid}, rc={p.poll()})")
            s["proc"] = _spawn(s["name"], s["cmd"])


def _required_health() -> dict[str, bool]:
    """Health of services desktop launchers wait on."""
    return {
        "backend": _health_ok("http://127.0.0.1:8000/health"),
        "dashboard": _health_ok("http://127.0.0.1:8765/"),
    }


def _kill_pid(pid: int) -> None:
    if not pid:
        return
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            os.kill(pid, 15)
    except OSError:
        pass


def _is_supervisor_pid(pid: int) -> bool:
    if not pid or os.name != "nt":
        return bool(pid)
    try:
        out = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}' "
                f"-ErrorAction SilentlyContinue).CommandLine",
            ],
            text=True,
            errors="replace",
        ).strip()
        return "mag_launch.py" in out
    except (OSError, subprocess.CalledProcessError):
        return False


def _takeover_stale_supervisor() -> bool:
    """If mutex owner exists but stack is unhealthy, kill it so we can restart."""
    health = _required_health()
    if all(health.values()):
        return False
    sup = 0
    try:
        data = json.loads(STATE.read_text(encoding="utf-8"))
        sup = int(data.get("supervisor_pid") or 0)
    except Exception:
        pass
    if sup and _pid_alive(sup) and _is_supervisor_pid(sup):
        _log(
            "stale supervisor pid=%s with unhealthy stack %s; taking over"
            % (sup, health)
        )
        _kill_pid(sup)
        time.sleep(1)
        return True
    # No live supervisor but mutex held — wait briefly and retry acquire.
    _log(f"unhealthy stack {health} with no live supervisor pid; retrying mutex")
    time.sleep(1)
    return True


def _sync_dynamic_slots(slots: list[dict]) -> None:
    """Refresh drainer/mirror wanted flags; stop drainer when toggled off."""
    want_drain = _drainer_wanted()
    for s in slots:
        if s["name"] == "drainer":
            s["wanted"] = want_drain
            if want_drain:
                s["cmd"] = [PY, str(ROOT / "main.py"), "orchestrator", "drain"]
                s.pop("note", None)
            else:
                s["cmd"] = []
                s["note"] = PREFERENCES_NOTE
                p = s.get("proc")
                if p is not None and p.poll() is None:
                    _log(f"stop drainer pid={p.pid} (toggle off)")
                    _kill_pid(p.pid)
                    s["proc"] = None


def write_state(slots: list[dict]) -> None:
    payload = {
        "started": _now(),
        "check_s": CHECK_S,
        "supervisor_pid": os.getpid(),
        "pids": {s["name"]: (s["proc"].pid if s["proc"] else None)
                 for s in slots},
        "wanted": {s["name"]: s["wanted"] for s in slots},
        "notes": {s["name"]: s.get("note", "") for s in slots},
        "health": {
            s["name"]: _health_ok(s["health_url"])
            for s in slots
            if s.get("health_url")
        },
    }
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError:
        pass


def main() -> int:
    if "--stop" in sys.argv:
        return stop_stack()
    once = "--once" in sys.argv
    instance = _SingleInstance()
    if not instance.acquire():
        if _takeover_stale_supervisor():
            instance.release()
            instance = _SingleInstance()
            if not instance.acquire():
                health = _required_health()
                _log(f"supervisor mutex held but stack unhealthy: {health}")
                return 1
        else:
            _log("supervisor already running; stack healthy")
            return 0
    slots = build_slots()
    try:
        _sync_dynamic_slots(slots)
        for s in slots:
            if not s["wanted"]:
                _log(f"{s['name']}: {s.get('note')}")
        ensure(slots)
        write_state(slots)
        if once:
            time.sleep(2)
            ensure(slots)
            write_state(slots)
            alive = {s["name"]: (s["proc"] is not None and s["proc"].poll()
                                 is None) for s in slots}
            print(json.dumps({"alive": alive}, indent=2))
            wanted = [s["name"] for s in slots if s["wanted"]]
            return 0 if all(alive.get(k) for k in wanted) else 1
        try:
            while True:
                time.sleep(CHECK_S)
                _sync_dynamic_slots(slots)
                ensure(slots)
                write_state(slots)
        except KeyboardInterrupt:
            _log("supervisor stopping; terminating children")
            for s in slots:
                if s["proc"] is not None and s["proc"].poll() is None:
                    try:
                        s["proc"].terminate()
                    except OSError:
                        pass
            return 0
    finally:
        instance.release()


if __name__ == "__main__":
    sys.exit(main())
