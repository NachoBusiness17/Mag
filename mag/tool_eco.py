"""Deterministic tool-result compression (/eco) before model context.

Never-worse: if compression would grow the payload, return the original.
"""
from __future__ import annotations

import json
import re
from typing import Any


def _dedup_lines(text: str, *, max_lines: int = 120) -> str:
    counts: dict[str, int] = {}
    order: list[str] = []
    for line in text.splitlines():
        key = line.rstrip()
        if key not in counts:
            order.append(key)
            counts[key] = 0
        counts[key] += 1
    out: list[str] = []
    for line in order[:max_lines]:
        n = counts[line]
        out.append(f"{line} [×{n}]" if n > 1 else line)
    if len(order) > max_lines:
        out.append(f"…[{len(order) - max_lines} more unique lines truncated]…")
    return "\n".join(out)


def _compress_pytest(text: str) -> str:
    lines = text.splitlines()
    fails = [ln for ln in lines if "FAILED" in ln or "ERROR" in ln or "AssertionError" in ln]
    summary = [ln for ln in lines if re.search(r"\d+ passed|\d+ failed|===", ln)]
    head = lines[:8]
    body = fails[-12:] if fails else lines[-20:]
    chunks = ["[eco:pytest]"]
    chunks.extend(head)
    if summary:
        chunks.append("--- summary ---")
        chunks.extend(summary[-5:])
    if fails:
        chunks.append("--- failures ---")
        chunks.extend(body)
    elif body:
        chunks.append("--- tail ---")
        chunks.extend(body)
    return "\n".join(chunks)


def _compress_git(text: str) -> str:
    drop = re.compile(
        r"^(remote:|From |To |\* \[|Enumerating|Counting|Compressing|"
        r"Receiving objects|Resolving deltas|Already up to date)",
        re.I,
    )
    kept = [ln for ln in text.splitlines() if ln.strip() and not drop.match(ln.strip())]
    if not kept:
        return text
    return "[eco:git]\n" + _dedup_lines("\n".join(kept), max_lines=60)


def _compress_pip_npm(text: str) -> str:
    drop = re.compile(
        r"^(Collecting |Downloading |Installing |Requirement already|"
        r"npm WARN|added \d+ packages|^\s*\d+%|Progress:)",
        re.I,
    )
    kept = [ln for ln in text.splitlines() if ln.strip() and not drop.match(ln.strip())]
    err = [ln for ln in kept if re.search(r"error|failed|ERROR", ln, re.I)]
    if err:
        return "[eco:pip/npm errors]\n" + "\n".join(err[-30:])
    tail = kept[-25:] if kept else text.splitlines()[-25:]
    return "[eco:pip/npm]\n" + "\n".join(tail)


def _compress_shell(name: str, text: str) -> str:
    low = text.lower()
    if "pytest" in low or "=== " in text:
        return _compress_pytest(text)
    if name == "run_shell":
        if "git " in low or "github" in low:
            return _compress_git(text)
        if "pip " in low or "npm " in low:
            return _compress_pip_npm(text)
    return _dedup_lines(text, max_lines=80)


def compress_tool_result(tool_name: str, payload: str, *, max_chars: int = 6000) -> str:
    """Compress tool JSON/text before appending to the model context."""
    raw = (payload or "").strip()
    if not raw:
        return raw
    # Try to unpack JSON tool envelopes
    text = raw
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            for key in ("output", "error", "stdout", "stderr", "text"):
                if isinstance(obj.get(key), str) and len(obj[key]) > 200:
                    inner = compress_tool_result(tool_name, obj[key], max_chars=max_chars)
                    if len(inner) < len(obj[key]):
                        obj[key] = inner
                        obj["_eco"] = True
                    text = json.dumps(obj, default=str)
                    break
            else:
                text = raw
    except json.JSONDecodeError:
        text = _compress_shell(tool_name, raw)

    if len(text) > max_chars:
        text = text[: max_chars - 40] + "\n…[eco head-cap]…\n" + text[-120:]

    # Never-worse guard
    if len(text) >= len(raw):
        return raw[:max_chars]
    return text


def compress_tool_output(tool_name: str, out: dict[str, Any], *, max_chars: int = 6000) -> str:
    return compress_tool_result(tool_name, json.dumps(out, default=str), max_chars=max_chars)
