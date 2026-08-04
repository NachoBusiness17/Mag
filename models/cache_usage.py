"""Normalize provider usage blobs — DeepSeek prefix cache telemetry."""
from __future__ import annotations

from typing import Any


def normalize_cache_usage(usage: dict[str, Any] | None) -> dict[str, int]:
    """Map DeepSeek / Anthropic cache fields onto a common shape.

    DeepSeek (OpenAI-compat): prompt_cache_hit_tokens, prompt_cache_miss_tokens
    Anthropic-style aliases: cache_read_input_tokens, input_tokens (miss)
    """
    u = usage or {}
    hit = int(
        u.get("prompt_cache_hit_tokens")
        or u.get("cache_read_input_tokens")
        or u.get("cached_tokens")
        or 0
    )
    miss = int(
        u.get("prompt_cache_miss_tokens")
        or u.get("cache_creation_input_tokens")
        or 0
    )
    prompt = int(u.get("prompt_tokens") or u.get("input_tokens") or 0)
    completion = int(u.get("completion_tokens") or u.get("output_tokens") or 0)
    if miss <= 0 and prompt > 0:
        # When only aggregate prompt_tokens returned, treat as miss unless hit covers all
        if hit > 0 and hit >= prompt:
            miss = 0
        else:
            miss = max(0, prompt - hit)
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "cache_read_tokens": hit,
        "cache_miss_tokens": miss,
    }
