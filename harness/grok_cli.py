"""Call Grok's open agentic harness (CLI headless mode).

Uses the same `grok` binary as Grok Build TUI:
  grok -p "..." --cwd ... --output-format plain|json [--max-turns N]

This is the specialist lane for Mag escalations — not a replacement for local Ollama.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import RESULTS_DIR, ROOT


def find_grok() -> str | None:
    env = os.environ.get("GROK_BIN")
    if env and Path(env).is_file():
        return env
    which = shutil.which("grok")
    if which:
        return which
    # Windows default install
    cand = Path.home() / ".grok" / "bin" / "grok.exe"
    if cand.is_file():
        return str(cand)
    return None


def harness_available() -> bool:
    return find_grok() is not None


def escalate_via_harness(
    *,
    goal: str,
    context: str = "",
    cwd: Path | None = None,
    max_turns: int = 12,
    yolo: bool = False,
    output_format: str = "plain",
    handoff_id: str | None = None,
    timeout: int = 600,
) -> dict[str, Any]:
    """Run one headless Grok harness turn. Returns structured result dict."""
    grok = find_grok()
    if not grok:
        return {
            "ok": False,
            "error": "grok binary not found (install Grok CLI / open harness)",
            "exit_code": 127,
        }

    cwd = cwd or ROOT
    handoff_id = handoff_id or datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-harness")
    prompt = f"""You are the specialist lane for Sovereign Mag (local companion).

## Goal
{goal}

## Context (from Mag / local clerk)
{context[:12000]}

## Rules
- One job. Substance. No flattery theater.
- Prefer writing concrete files under the cwd when useful.
- Respect private data: do not exfiltrate secrets.
- End with a short SUMMARY of what you did or what is blocked.

When done, structure your final answer with:
SUMMARY: ...
DELIVERABLE: ...
"""

    # Prefer --prompt-file for long prompts / Windows quoting
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        delete=False,
        encoding="utf-8",
        dir=str(RESULTS_DIR),
    ) as tf:
        tf.write(prompt)
        prompt_path = tf.name

    cmd = [
        grok,
        "--prompt-file",
        prompt_path,
        "--cwd",
        str(cwd),
        "--output-format",
        output_format if output_format in {"plain", "json", "streaming-json"} else "plain",
        "--max-turns",
        str(max_turns),
        "--no-auto-update",
    ]
    if yolo:
        cmd.append("--always-approve")
    # Safer default: deny destructive shell patterns when not yolo
    if not yolo:
        cmd.extend(["--deny", "Bash(rm*)", "--deny", "Bash(*Remove-Item*)"])

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd),
        )
        stdout = (proc.stdout or "")[-50000:]
        stderr = (proc.stderr or "")[-8000:]
        result: dict[str, Any] = {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "handoff_id": handoff_id,
            "summary": _extract_summary(stdout),
            "deliverable": stdout,
            "stderr": stderr,
            "cmd": " ".join(cmd[:6]) + " …",
            "harness": "grok-cli-headless",
        }
        out_path = RESULTS_DIR / f"{handoff_id}.json"
        out_path.write_text(json.dumps(result, indent=2)[:200000], encoding="utf-8")
        result["result_path"] = str(out_path)
        return result
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "harness timeout", "exit_code": 124, "handoff_id": handoff_id}
    except Exception as e:
        return {"ok": False, "error": str(e), "exit_code": 1, "handoff_id": handoff_id}
    finally:
        try:
            Path(prompt_path).unlink(missing_ok=True)
        except OSError:
            pass


def _extract_summary(text: str) -> str:
    for line in text.splitlines():
        if line.strip().upper().startswith("SUMMARY:"):
            return line.split(":", 1)[-1].strip()
    # last non-empty paragraph snippet
    parts = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
    return (parts[-1] if parts else text[:500])[:1500]
