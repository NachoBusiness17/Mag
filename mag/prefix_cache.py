"""Byte-stable prefix + DeepSeek disk cache helpers (ClawCodex-inspired).

Stable system prompt stays byte-identical across turns; volatile context pack,
anchor, and repack notes move to a trailing <system-reminder> block on the user
turn so the request prefix (system + tools + history) can hit DeepSeek cache.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from config import ROOT
from mag.compass import FRAMEWORK_BLOCK, constitution_text

# Bump only when binding law / framework text changes (invalidates cache by design).
_STABLE_VERSION = "mag-stable-system-v1"

_REMINDER_OPEN = "<system-reminder>"
_REMINDER_CLOSE = "</system-reminder>"


def byte_stable_prefix_enabled(provider: str) -> bool:
    env = os.environ.get("MAG_BYTE_STABLE_PREFIX", "").strip().lower()
    if env in ("0", "false", "no"):
        return False
    if env in ("1", "true", "yes"):
        return True
    pid = (provider or "").strip().lower()
    return pid in ("deepseek", "deepseek_overmind")


def load_anchor_text() -> str:
    anchor_path = os.environ.get("MAG_ANCHORED_PLAN") or str(
        ROOT / "memory" / "plans" / "ANCHOR.md"
    )
    try:
        p = Path(anchor_path)
        if p.is_file():
            return p.read_text(encoding="utf-8")[:2500]
    except OSError:
        pass
    return ""


@lru_cache(maxsize=1)
def stable_system_prompt() -> str:
    """Immutable across turns within a process — safe for DeepSeek prefix cache."""
    law_block = "\n".join(
        [
            "## Binding law (constitution - immutable)",
            constitution_text(700),
            "\nObligations always hold: data tiers T0-T3 (T0/T1 never to free remote "
            "train-on-input APIs); no .env/verkle_tip/knots writes; irreversible acts "
            "need a Human Nod; artifact > transcript.",
        ]
    )
    return f"""You are Mag agent CLI — a tool-using seat on the operator's local Mag disk.
You keep work moving with local tools + this model.

## Law
- One job at a time. Truth-only. No flattery.
- Artifact > transcript. Prefer tools over guessing file contents.
- Paths are relative to Mag project root unless absolute and jailed.
- Never read or echo .env secrets. Never destroy residual DNA / verkle_tip / knots.
- Prefer write targets: memory/working.md, memory/runs/*/progress.md, queue/, dig leaves under memory/improve/.
- When done, give a short final answer (what you did + paths). Do not narrate fake tool calls — call tools for real.
- Context is scarce on remote seats (esp. DeepSeek). Prefer short tool results and finish; the harness will auto-repack if the window fills.
- Volatile operator context arrives in trailing {_REMINDER_OPEN} blocks — treat as authoritative for this turn.

{law_block}
{FRAMEWORK_BLOCK}
## Prefix cache ({_STABLE_VERSION})
This system block is byte-stable. Do not expect refreshed bonds/brief here — read the reminder tail.
"""


def volatile_reminder(
    pack_text: str,
    *,
    repacked: bool = False,
    anchor_text: str | None = None,
) -> str:
    """Volatile context — appended to user turns, not baked into system prefix."""
    anchor = anchor_text if anchor_text is not None else load_anchor_text()
    parts: list[str] = [_REMINDER_OPEN]
    if repacked:
        parts.append(
            "## Auto-repack\n"
            "History was compacted to fit this provider's context window "
            "(pack-first). Residual below holds the goal and tools already run. "
            "Continue the job; do not re-discover from zero."
        )
    if anchor:
        parts.append(f"## Anchored plan (survives repack)\n{anchor}")
    parts.append("## Context pack (authoritative, min tokens)")
    parts.append((pack_text or "(empty)")[:3500])
    parts.append(_REMINDER_CLOSE)
    return "\n".join(parts)


def wrap_user_with_reminder(user_text: str, pack_text: str, *, repacked: bool = False) -> str:
    reminder = volatile_reminder(pack_text, repacked=repacked)
    body = (user_text or "").strip()
    return f"{reminder}\n\n{body}" if body else reminder


def is_reminder_message(content: str) -> bool:
    return _REMINDER_OPEN in (content or "")


def ensure_stable_system(messages: list[dict[str, Any]], *, provider: str) -> list[dict[str, Any]]:
    """Force byte-stable system slot when enabled; no-op otherwise."""
    if not byte_stable_prefix_enabled(provider):
        return messages
    stable = {"role": "system", "content": stable_system_prompt()}
    if not messages:
        return [stable]
    if messages[0].get("role") == "system":
        out = list(messages)
        out[0] = stable
        return out
    return [stable] + list(messages)


def fresh_pack_text() -> str:
    from mag.context_pack import build_context_pack, format_context_pack_text

    pack = build_context_pack(max_brief=900, max_live=400)
    text = format_context_pack_text(pack)
    try:
        (ROOT / "memory" / "context_pack_latest.md").write_text(text, encoding="utf-8")
    except OSError:
        pass
    return text
