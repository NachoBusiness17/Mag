"""Call Nous Research Hermes Agent (headless one-shot).

Hermes is an external seat for Mag — self-improving agent with skills/memory.
Install (Windows PowerShell, operator-run):
  iex (irm https://hermes-agent.nousresearch.com/install.ps1)

Headless entry points used here:
  hermes -z "…"                    # final answer only (scripted)
  hermes chat -q "…" -Q            # quiet one-shot with tools

Not a replacement for Grok TUI (sovereign) or local Ollama (clerk).
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


def find_hermes() -> str | None:
    env = os.environ.get("HERMES_BIN")
    if env and Path(env).is_file():
        return env
    which = shutil.which("hermes")
    if which:
        return which
    # Windows native install (installer docs)
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "hermes"
    for cand in (
        local / "bin" / "hermes.exe",
        local / "hermes.exe",
        local / "hermes-agent" / "hermes",
        Path.home() / ".hermes" / "bin" / "hermes",
        Path.home() / ".local" / "bin" / "hermes",
    ):
        if cand.is_file():
            return str(cand)
    # Windows: hermes.cmd / hermes.ps1 on PATH dirs already covered by which
    return None


def harness_available() -> bool:
    return find_hermes() is not None


def hermes_status() -> dict[str, Any]:
    path = find_hermes()
    if not path:
        return {
            "ok": False,
            "available": False,
            "bin": None,
            "hint": (
                "Hermes not installed. Windows: "
                "iex (irm https://hermes-agent.nousresearch.com/install.ps1) "
                "then hermes setup (or hermes setup --portal). "
                "Or set HERMES_BIN to the hermes executable."
            ),
        }
    version = None
    try:
        proc = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        version = ((proc.stdout or proc.stderr) or "").strip()[:200] or None
    except Exception as e:
        version = f"probe_error: {e}"
    return {
        "ok": True,
        "available": True,
        "bin": path,
        "version": version,
    }


# Preferred local agent model (64k ctx Modelfile; see scripts/setup_hermes_ollama.ps1)
DEFAULT_HERMES_MODEL = os.environ.get("HERMES_MODEL", "gemma4-hermes")
DEFAULT_TOOLSETS = os.environ.get("HERMES_TOOLSETS", "terminal,file,todo")


def escalate_via_hermes(
    *,
    goal: str,
    context: str = "",
    cwd: Path | None = None,
    max_turns: int = 40,
    yolo: bool = True,
    mode: str = "chat",
    provider: str | None = "custom",
    model: str | None = None,
    handoff_id: str | None = None,
    timeout: int = 900,
    ignore_user_rules: bool = False,
    toolsets: str | None = None,
    expect_path: str | Path | None = None,
) -> dict[str, Any]:
    """
    Run one headless Hermes turn with Mag context-pack only.

    mode:
      chat — hermes chat -q -Q (tools + agent loop; default)
      z    — hermes -z (final text only; no tool previews)

    expect_path: if set, job fails when that file is missing after the run
      (catches models that roleplay write_file without calling tools).
    """
    hermes = find_hermes()
    if not hermes:
        return {
            "ok": False,
            "error": "hermes binary not found (install Hermes Agent or set HERMES_BIN)",
            "exit_code": 127,
            "available": False,
        }

    cwd = Path(cwd) if cwd else ROOT
    model = model or DEFAULT_HERMES_MODEL
    toolsets = toolsets or DEFAULT_TOOLSETS
    handoff_id = handoff_id or datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-hermes")
    expect = Path(expect_path) if expect_path else None
    if expect and not expect.is_absolute():
        expect = cwd / expect

    expect_line = ""
    if expect:
        expect_line = (
            f"\n- REQUIRED: create or update this file with real tools "
            f"(not pretend): `{expect}`\n"
            "- Do not narrate tool use. Call terminal/file tools only.\n"
            "- Do not ask clarifying questions. If path unknown, use cwd.\n"
        )

    prompt = f"""You are a specialist seat called by Sovereign Mag (local companion).
Working directory is fixed: {cwd}
Do not ask for paths.

## Goal
{goal}

## Context (from Mag — authoritative, min tokens)
{context[:12000]}

## Rules
- One job. Substance. No flattery.
- Use tools for file/shell work. Never roleplay a tool call in plain text.
- Prefer concrete deliverables under the working directory when useful.
- Do not exfiltrate secrets, .env, or intimate/private residual data.
{expect_line}- End with:
SUMMARY: ...
DELIVERABLE: ...
"""

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

    env = os.environ.copy()
    env.setdefault("OPENAI_API_KEY", "ollama")
    env.setdefault("OLLAMA_CONTEXT_LENGTH", "65536")
    env.setdefault("HERMES_API_TIMEOUT", "1800")

    try:
        query = Path(prompt_path).read_text(encoding="utf-8")
        cmd: list[str]
        if mode == "z":
            cmd = [hermes, "-z", query, "-m", model]
            if provider:
                cmd.extend(["--provider", provider])
        else:
            cmd = [
                hermes,
                "chat",
                "-q",
                query,
                "-Q",
                "--source",
                "tool",
                "--max-turns",
                str(max_turns),
                "-m",
                model,
                "-t",
                toolsets,
                "--accept-hooks",
            ]
            if provider:
                cmd.extend(["--provider", provider])
            if yolo:
                cmd.append("--yolo")
            if ignore_user_rules:
                cmd.extend(["--ignore-user-config", "--ignore-rules"])

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd),
            env=env,
        )
        stdout = (proc.stdout or "")[-50000:]
        stderr = (proc.stderr or "")[-8000:]
        theater = _looks_like_tool_theater(stdout)
        missing = bool(expect and not expect.is_file())
        ok = proc.returncode == 0 and not theater and not missing
        result: dict[str, Any] = {
            "ok": ok,
            "exit_code": proc.returncode,
            "handoff_id": handoff_id,
            "summary": _extract_summary(stdout),
            "deliverable": stdout,
            "stderr": stderr,
            "cmd": " ".join(cmd[:8]) + " …",
            "harness": "hermes-agent",
            "mode": mode,
            "model": model,
            "toolsets": toolsets if mode != "z" else None,
            "available": True,
            "tool_theater": theater,
            "expect_path": str(expect) if expect else None,
            "expect_missing": missing,
        }
        if theater:
            result["error"] = (
                "Hermes roleplayed tools without executing them "
                "(tool theater). Use a stronger tool model or tighten goal."
            )
        if missing:
            result["error"] = (
                f"Expected deliverable missing: {expect}. "
                "Model did not write the file."
            )
        out_path = RESULTS_DIR / f"{handoff_id}.json"
        out_path.write_text(json.dumps(result, indent=2)[:200000], encoding="utf-8")
        result["result_path"] = str(out_path)
        return result
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "error": "hermes timeout",
            "exit_code": 124,
            "handoff_id": handoff_id,
            "harness": "hermes-agent",
        }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "exit_code": 1,
            "handoff_id": handoff_id,
            "harness": "hermes-agent",
        }
    finally:
        try:
            Path(prompt_path).unlink(missing_ok=True)
        except OSError:
            pass


def _looks_like_tool_theater(text: str) -> bool:
    """True when the model narrates tool use instead of producing real results."""
    t = (text or "").lower()
    if not t.strip():
        return False
    pretend = (
        "assuming the content",
        "i will now use the",
        "i will read all",
        "via write_file tool",
        "final output generation via",
        "once i have successfully",
        "let me know what the next step",
        "could you please provide",
        "please provide me with the absolute path",
    )
    hits = sum(1 for p in pretend if p in t)
    # Pure narration with no SUMMARY and no path-like deliverable
    has_summary = "summary:" in t
    if hits >= 2 and not has_summary:
        return True
    if hits >= 1 and "write_file" in t and "summary:" not in t:
        return True
    return False


def _extract_summary(text: str) -> str:
    for line in text.splitlines():
        if line.strip().upper().startswith("SUMMARY:"):
            return line.split(":", 1)[-1].strip()
    parts = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
    return (parts[-1] if parts else text[:500])[:1500]
