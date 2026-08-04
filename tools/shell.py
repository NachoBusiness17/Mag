"""Allowlisted shell commands only."""
from __future__ import annotations

import shlex
import subprocess
import sys

from config import MAX_TOOL_OUTPUT, ROOT, SHELL_ALLOW


def run_shell(command: str, timeout: int = 60) -> dict:
    command = (command or "").strip()
    if not command:
        return {"ok": False, "exit_code": 1, "error": "empty command"}

    # Parse first token (PowerShell-friendly: split on space)
    first = command.split()[0]
    # strip path-like prefixes
    base = first.replace("\\", "/").split("/")[-1]
    if base not in SHELL_ALLOW and first not in SHELL_ALLOW:
        return {
            "ok": False,
            "exit_code": 126,
            "error": f"command not allowlisted: {base}",
            "allow": sorted(SHELL_ALLOW),
        }

    # Block obvious danger even if allowlisted binary
    lowered = command.lower()
    for bad in ("rm -rf", "format ", "del /f", "remove-item -recurse", "invoke-webrequest", "curl http"):
        if bad in lowered:
            return {"ok": False, "exit_code": 126, "error": f"blocked pattern: {bad}"}

    try:
        # Prefer PowerShell on Windows for dir/Get-ChildItem
        if sys.platform == "win32":
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        else:
            proc = subprocess.run(
                shlex.split(command),
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        out = (proc.stdout or "") + (proc.stderr or "")
        out = out[:MAX_TOOL_OUTPUT]
        return {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "output": out,
            "command": command,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "exit_code": 124, "error": "timeout", "command": command}
    except Exception as e:
        return {"ok": False, "exit_code": 1, "error": str(e), "command": command}
