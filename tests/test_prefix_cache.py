"""Prefix cache + tool eco + DeepSeek usage normalization."""
from __future__ import annotations

from mag.prefix_cache import (
    byte_stable_prefix_enabled,
    stable_system_prompt,
    volatile_reminder,
    wrap_user_with_reminder,
)
from mag.tool_eco import compress_tool_result
from models.cache_usage import normalize_cache_usage


def test_stable_system_is_byte_identical():
    a = stable_system_prompt()
    b = stable_system_prompt()
    assert a == b
    assert "mag-stable-system-v1" in a
    assert "Context pack" not in a


def test_volatile_not_in_stable_system():
    stable = stable_system_prompt()
    vol = volatile_reminder("bonds: test-bond\nbrief: hello", repacked=True)
    assert "<system-reminder>" in vol
    assert "bonds: test-bond" in vol
    assert "Auto-repack" in vol
    assert "bonds: test-bond" not in stable


def test_byte_stable_default_for_deepseek():
    assert byte_stable_prefix_enabled("deepseek") is True
    assert byte_stable_prefix_enabled("ollama") is False


def test_wrap_user_with_reminder():
    wrapped = wrap_user_with_reminder("do the thing", "pack-line")
    assert "do the thing" in wrapped
    assert "pack-line" in wrapped
    assert wrapped.index("<system-reminder>") < wrapped.index("do the thing")


def test_normalize_deepseek_cache_usage():
    norm = normalize_cache_usage(
        {
            "prompt_tokens": 5000,
            "completion_tokens": 200,
            "prompt_cache_hit_tokens": 4800,
            "prompt_cache_miss_tokens": 200,
        }
    )
    assert norm["cache_read_tokens"] == 4800
    assert norm["cache_miss_tokens"] == 200


def test_tool_eco_never_worse_on_short():
    raw = '{"ok": true, "x": 1}'
    assert compress_tool_result("run_python", raw) == raw


def test_tool_eco_compresses_pytest_tail():
    blob = "line\n" * 5 + "FAILED tests/test_x.py::test_y - AssertionError\n" + ("z" * 3000)
    out = compress_tool_result("run_shell", blob)
    assert len(out) < len(blob)
    assert "FAILED" in out or "eco" in out
