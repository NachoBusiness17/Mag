"""Mag power switch — one kill, one start, honest stack status.

Stops the whack-a-mole: supervisor respawn, guard restart, orphan orchestrator
children, seat-guard REPLs, and port listeners all go down together.

CLI:  python main.py power status|stop|start
REST: GET /api/v1/power · POST /api/v1/power/stop · POST /api/v1/power/start
Files: state/mag_power.off (set while stack should stay down)
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
from typing import Any

from config import ROOT

POWER_OFF = ROOT / "state" / "mag_power.off"
LAUNCH_STATE = ROOT / "state" / "mag_launch.json"
GUARD_DIR = ROOT / "memory" / "runs" / "seat_guard"
MAG_PORTS = (8000, 8765, 8743)
SCHEMA = "mag_power.v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_off() -> bool:
    return POWER_OFF.is_file()


def set_off() -> None:
    POWER_OFF.parent.mkdir(parents=True, exist_ok=True)
    POWER_OFF.write_text(_now() + "\n", encoding="utf-8")


def clear_off() -> None:
    try:
        POWER_OFF.unlink(missing_ok=True)
    except OSError:
        pass


def _python_exe() -> str:
    venv_py = ROOT / ".venv" / "Scripts" / "python.exe"
    if venv_py.is_file():
        return str(venv_py)
    if sys.platform == "win32" and sys.executable.lower().endswith("pythonw.exe"):
        return sys.executable[:-5] + ".exe"
    return sys.executable


def _health(url: str, timeout: float = 1.5) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return 200 <= r.status < 300
    except Exception:
        return False


def _pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            h = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))
            if not h:
                return False
            try:
                ec = wintypes.DWORD()
                ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(ec))
                return ec.value == 259
            finally:
                ctypes.windll.kernel32.CloseHandle(h)
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _kill_tree(pid: int) -> None:
    if not pid:
        return
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            os.kill(pid, 15)
    except OSError:
        pass


def _pids_on_port(port: int) -> list[int]:
    if os.name != "nt":
        try:
            out = subprocess.check_output(
                ["ss", "-ltnp"], text=True, errors="replace", timeout=5,
            )
            pids: set[int] = set()
            for line in out.splitlines():
                if f":{port}" in line and "pid=" in line:
                    for part in line.split("pid=")[1:]:
                        num = part.split(",")[0].strip()
                        if num.isdigit():
                            pids.add(int(num))
            return sorted(pids)
        except Exception:
            return []
    try:
        out = subprocess.check_output(["netstat", "-ano"], text=True, errors="replace")
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


def _mag_python_pids() -> set[int]:
    targets: set[int] = set()
    root = str(ROOT)
    if os.name == "nt":
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
                timeout=30,
            )
            for line in out.splitlines():
                if line.strip().isdigit():
                    targets.add(int(line.strip()))
        except Exception:
            pass
    else:
        try:
            out = subprocess.check_output(["ps", "aux"], text=True, errors="replace", timeout=10)
            for line in out.splitlines():
                if root in line and "python" in line.lower():
                    parts = line.split()
                    if len(parts) > 1 and parts[1].isdigit():
                        targets.add(int(parts[1]))
        except Exception:
            pass
    return targets


def _collect_all_pids() -> set[int]:
    """Every pid belonging to this Mag stack."""
    targets: set[int] = set()
    try:
        from mag_launch import _collect_mag_pids

        targets.update(_collect_mag_pids())
    except Exception:
        pass
    for port in MAG_PORTS:
        targets.update(_pids_on_port(port))
    targets.update(_mag_python_pids())
    try:
        data = json.loads(LAUNCH_STATE.read_text(encoding="utf-8"))
        sup = int(data.get("supervisor_pid") or 0)
        if sup:
            targets.add(sup)
        for pid in (data.get("pids") or {}).values():
            if pid:
                targets.add(int(pid))
    except Exception:
        pass
    try:
        from mag.orchestrator import list_tasks_live

        for t in list_tasks_live(limit=100) or []:
            if t.get("status") == "running" and t.get("pid"):
                targets.add(int(t["pid"]))
    except Exception:
        pass
    if GUARD_DIR.is_dir():
        for p in GUARD_DIR.glob("seat-*.json"):
            try:
                rec = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            pid = rec.get("pid")
            if rec.get("status") == "running" and pid:
                targets.add(int(pid))
    mag_pid = ROOT / "watch" / "mag.pid"
    try:
        targets.add(int(mag_pid.read_text(encoding="utf-8").strip()))
    except Exception:
        pass
    # Never kill our own pid during status/stop orchestration from CLI
    targets.discard(os.getpid())
    return targets


def _stop_seat_guards() -> int:
    n = 0
    if not GUARD_DIR.is_dir():
        return 0
    for p in GUARD_DIR.glob("seat-*.json"):
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if rec.get("status") != "running":
            continue
        tid = str(rec.get("task_id") or "")
        if tid:
            (GUARD_DIR / f"{tid}.stop").write_text("power_stop\n", encoding="utf-8")
            n += 1
    return n


def _kill_orchestrator_running() -> int:
    n = 0
    try:
        from mag.orchestrator import kill_task, list_tasks_live

        for t in list_tasks_live(limit=100) or []:
            if t.get("status") != "running":
                continue
            tid = str(t.get("task_id") or "")
            if tid:
                kill_task(tid)
                n += 1
    except Exception:
        pass
    return n


def stop_all(*, include_self: bool = False) -> dict[str, Any]:
    """Kill switch — bring down the entire Mag stack (no respawn until start)."""
    set_off()
    guards = _stop_seat_guards()
    orch_killed = _kill_orchestrator_running()

    pids = _collect_all_pids()
    if include_self:
        pids.add(os.getpid())

    # Supervisor first — stops the respawn loop
    sup_pid = 0
    try:
        sup_pid = int(json.loads(LAUNCH_STATE.read_text(encoding="utf-8")).get("supervisor_pid") or 0)
    except Exception:
        pass
    if sup_pid and sup_pid in pids:
        _kill_tree(sup_pid)
        pids.discard(sup_pid)
        time.sleep(0.5)

    killed: list[int] = []
    for pid in sorted(pids, reverse=True):
        _kill_tree(pid)
        killed.append(pid)

    try:
        from mag_launch import stop_stack

        stop_stack()
    except Exception:
        pass

    try:
        LAUNCH_STATE.write_text("{}", encoding="utf-8")
    except OSError:
        pass
    mag_pid = ROOT / "watch" / "mag.pid"
    try:
        mag_pid.unlink(missing_ok=True)
    except OSError:
        pass

    time.sleep(1)
    remaining = _collect_all_pids()
    ports = {str(p): _pids_on_port(p) for p in MAG_PORTS}

    return {
        "ok": True,
        "schema": SCHEMA,
        "ts": _now(),
        "action": "stop",
        "power_off": True,
        "orchestrator_killed": orch_killed,
        "seat_guards_stopped": guards,
        "pids_targeted": len(killed),
        "pids_remaining": len(remaining),
        "remaining_pids": sorted(remaining)[:20],
        "ports": ports,
        "hint": "Stack off. Run: mag.cmd power start  or  start_everything.cmd",
    }


def start_all(*, open_browser: bool = False) -> dict[str, Any]:
    """Turn-on switch — clear off flag and boot supervisor + core services."""
    clear_off()
    py = _python_exe()
    pyw = py.replace("python.exe", "pythonw.exe") if py.endswith("python.exe") else py
    launch = ROOT / "mag_launch.py"
    if not launch.is_file():
        return {"ok": False, "error": "mag_launch.py missing"}

    # Spawn detached supervisor (same as start_everything.cmd)
    try:
        subprocess.run([py, str(launch), "--once"], cwd=str(ROOT), timeout=120, check=False)
    except Exception as exc:
        return {"ok": False, "error": f"launch --once failed: {exc}"}

    detached = 0
    if os.name == "nt":
        detached = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) | getattr(
            subprocess, "DETACHED_PROCESS", 0x00000008
        )
    try:
        subprocess.Popen(
            [pyw if os.path.isfile(pyw) else py, str(launch)],
            cwd=str(ROOT),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=detached,
            start_new_session=(os.name != "nt"),
        )
    except Exception as exc:
        return {"ok": False, "error": f"supervisor spawn failed: {exc}"}

    deadline = time.time() + 60
    health = {"backend": False, "dashboard": False}
    while time.time() < deadline:
        health["backend"] = _health("http://127.0.0.1:8000/health")
        health["dashboard"] = _health("http://127.0.0.1:8765/")
        if all(health.values()):
            break
        time.sleep(1)

    if open_browser and health["dashboard"]:
        try:
            import webbrowser

            webbrowser.open("http://127.0.0.1:8765")
        except Exception:
            pass

    return {
        "ok": all(health.values()),
        "schema": SCHEMA,
        "ts": _now(),
        "action": "start",
        "power_off": False,
        "health": health,
        "hint": "http://127.0.0.1:8765 — Body tab for live stack status",
    }


def stack_status() -> dict[str, Any]:
    """Honest glance — services, ports, supervisor, fleet, switchboard."""
    off = is_off()
    services = {
        "backend": _health("http://127.0.0.1:8000/health"),
        "dashboard": _health("http://127.0.0.1:8765/"),
        "mirror": _health("http://127.0.0.1:8743/"),
    }
    stack_up = services["backend"] and services["dashboard"]

    supervisor: dict[str, Any] = {"running": False, "pids": {}, "wanted": {}}
    try:
        ml = json.loads(LAUNCH_STATE.read_text(encoding="utf-8"))
        pids = ml.get("pids") or {}
        wanted = ml.get("wanted") or {}
        alive = {r: p for r, p in pids.items() if p and _pid_alive(int(p))}
        supervisor = {
            "running": any(alive.get(r) for r in wanted if wanted.get(r)),
            "pids": alive,
            "wanted": wanted,
            "started": ml.get("started"),
            "health": ml.get("health") or {},
        }
    except Exception:
        pass

    fleet = {"running": 0, "total": 0}
    try:
        from mag.orchestrator import TERMINAL, list_tasks

        tasks = list_tasks(limit=50)
        fleet = {
            "total": len(tasks),
            "running": sum(1 for t in tasks if t.get("status") not in TERMINAL),
        }
    except Exception:
        pass

    switchboard: dict[str, Any] = {}
    try:
        from mag.switchboard import status as sb_status

        switchboard = sb_status()
    except Exception as exc:
        switchboard = {"error": str(exc)[:120]}

    seat_guards = 0
    if GUARD_DIR.is_dir():
        for p in GUARD_DIR.glob("seat-*.json"):
            try:
                if json.loads(p.read_text(encoding="utf-8")).get("status") == "running":
                    seat_guards += 1
            except Exception:
                pass

    registered = 0
    try:
        from mag.seat_registry import list_registered

        registered = len(list_registered(live_only=True))
    except Exception:
        pass

    mag_pids = len(_collect_all_pids())
    headline = "STOPPED" if off else ("UP" if stack_up else "PARTIAL")
    if not off and mag_pids > 0 and not stack_up:
        headline = "ZOMBIES"  # processes without healthy ports

    return {
        "ok": True,
        "schema": SCHEMA,
        "ts": _now(),
        "headline": headline,
        "power_off": off,
        "stack_up": stack_up,
        "services": services,
        "ports": {str(p): _pids_on_port(p) for p in MAG_PORTS},
        "supervisor": supervisor,
        "fleet": fleet,
        "seat_guards_running": seat_guards,
        "registered_seats": registered,
        "mag_processes": mag_pids,
        "switchboard_summary": switchboard.get("summary"),
        "top_peers": (switchboard.get("top_peers") or [])[:5],
        "actions": {
            "stop": "mag.cmd power stop  or  mag_kill.cmd",
            "start": "mag.cmd power start  or  start_everything.cmd",
            "status": "mag.cmd power status  or  dashboard Body tab",
        },
    }


def format_status_text(s: dict[str, Any]) -> str:
    lines = [
        f"Mag power ({s.get('headline')}) — off_flag={s.get('power_off')}",
        f"  backend={s.get('services', {}).get('backend')} "
        f"dashboard={s.get('services', {}).get('dashboard')} "
        f"mirror={s.get('services', {}).get('mirror')}",
        f"  supervisor={s.get('supervisor', {}).get('running')} "
        f"fleet_running={s.get('fleet', {}).get('running')} "
        f"seat_guards={s.get('seat_guards_running')} "
        f"mag_pids={s.get('mag_processes')}",
    ]
    for p in s.get("top_peers") or []:
        lines.append(
            f"  · {p.get('peer_id')} seat={p.get('seat')} status={p.get('status')}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="mag power", description="Kill switch + turn-on + stack status")
    ap.add_argument("action", nargs="?", default="status", choices=["status", "stop", "start"])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--browser", action="store_true", help="open dashboard after start")
    args = ap.parse_args(argv)

    if args.action == "stop":
        res = stop_all()
    elif args.action == "start":
        res = start_all(open_browser=bool(args.browser))
    else:
        res = stack_status()

    if args.json:
        print(json.dumps(res, indent=2, default=str))
    else:
        print(format_status_text(res) if args.action == "status" else json.dumps(res, indent=2, default=str))
    if args.action == "stop":
        return 0 if res.get("pids_remaining", 1) == 0 else 0  # always 0 for operator
    return 0 if res.get("ok", True) else 1


if __name__ == "__main__":
    sys.exit(main())
