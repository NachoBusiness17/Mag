"""Sandboxed Python execution in a temp dir (no network intent)."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from config import MAX_TOOL_OUTPUT, ROOT


# Preamble injected into every snippet so agents don't re-implement file I/O
# boilerplate (the dominant PATCH-VERIFY loop from session mining 2026-08-03).
_PREAMBLE = r'''
import os, sys, json
from pathlib import Path
ROOT = Path(r"{root}")
def P(*parts):
    """Join path parts under ROOT."""
    return str(ROOT.joinpath(*parts))
def dump_lines(path, line_from=None, line_to=None):
    """Print a numbered region of a file (1-indexed, clamps to EOF)."""
    p = Path(path) if os.path.isabs(path) else ROOT.joinpath(path)
    if not p.is_file():
        print(f"[dump_lines] missing: {{p}}")
        return
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    total = len(lines)
    lo = (line_from or 1) - 1
    hi = (line_to or total) if line_to else total
    lo = max(0, lo); hi = min(total, hi)
    for i in range(lo, hi):
        print(f"{{i+1}}: {{lines[i]}}")
    print(f"[dump_lines] {{p}} total={{total}} shown={{hi-lo}}")
'''.format(root=str(ROOT).replace("\\", "\\\\"))


def run_python(code: str, timeout: int = 30) -> dict:
    if not code or not code.strip():
        return {"ok": False, "exit_code": 1, "error": "empty code"}

    # Soft refuse obvious network imports used maliciously — still not a full sandbox
    banned = ("socket.socket", "subprocess", "os.system", "shutil.rmtree", "__import__('os')")
    for b in banned:
        if b in code:
            return {"ok": False, "exit_code": 126, "error": f"banned pattern: {b}"}

    try:
        with tempfile.TemporaryDirectory(prefix="lsa_exec_") as td:
            script = Path(td) / "snippet.py"
            script.write_text(_PREAMBLE + "\n" + code, encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(script)],
                cwd=td,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={
                    **dict(**{k: v for k, v in __import__("os").environ.items() if k in ("SYSTEMROOT", "PATH", "PYTHONPATH") or k.startswith("PYTHON")}),
                },
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            return {
                "ok": proc.returncode == 0,
                "exit_code": proc.returncode,
                "output": out[:MAX_TOOL_OUTPUT],
            }
    except subprocess.TimeoutExpired:
        return {"ok": False, "exit_code": 124, "error": "timeout"}
    except Exception as e:
        return {"ok": False, "exit_code": 1, "error": str(e)}
