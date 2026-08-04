"""Agent context-window estimate + repack (no remote calls)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mag.agent_cli import (  # noqa: E402
    _estimate_tokens,
    provider_context_tokens,
    repack_messages,
    usable_context_budget,
)


def test_deepseek_context_window():
    assert provider_context_tokens("deepseek") >= 32_000
    assert usable_context_budget("deepseek") < provider_context_tokens("deepseek")


def test_estimate_grows_with_content():
    small = [{"role": "user", "content": "hi"}]
    big = [{"role": "user", "content": "x" * 40_000}]
    assert _estimate_tokens(big) > _estimate_tokens(small)


def test_repack_collapses_to_system_plus_user():
    fat = [
        {"role": "system", "content": "old system"},
        {"role": "user", "content": "do the thing"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "c1",
                    "type": "function",
                    "function": {"name": "list_dir", "arguments": "{}"},
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "c1",
            "content": json_payload(),
        },
    ]
    out = repack_messages(
        fat,
        user_text="do the thing",
        traces=["list_dir: ok=True"],
        provider="deepseek",
    )
    assert len(out) == 2
    assert out[0]["role"] == "system"
    assert "Auto-repack" in out[0]["content"] or "auto-repack" in out[1]["content"].lower()
    assert out[1]["role"] == "user"
    assert "do the thing" in out[1]["content"]
    assert "list_dir" in out[1]["content"]
    # repacked should be much smaller than a fat multi-k tool dump chain
    assert _estimate_tokens(out) < _estimate_tokens(fat) + 5000


def json_payload() -> str:
    return '{"ok": true, "files": ["a.py", "b.py"], "note": "' + ("z" * 2000) + '"}'
