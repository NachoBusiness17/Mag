"""L1 remote chat — multi-provider (OpenRouter, OpenAI, Groq, DeepSeek, Gemini, xAI…).

Constitution: never send T0/T1 (live chat, private archive) to free remote train-on-input APIs.
Prefer models.providers for full surface.
"""
from __future__ import annotations

from typing import Any

from models.providers import chat_openrouter, chat_provider, chat_routed, openrouter_configured

__all__ = [
    "openrouter_configured",
    "chat_openrouter",
    "chat_provider",
    "chat_routed",
]


def chat_public(
    system: str,
    user: str,
    *,
    job: str = "public_summarize",
    tier: str = "T2",
    **kwargs: Any,
) -> dict[str, Any]:
    """Route a public (T2+) job across providers with remaining quota."""
    if tier in ("T0", "T1"):
        return {"ok": False, "error": "refused: T0/T1 may not leave the machine via remote"}
    return chat_routed(system, user, job=job, tier=tier, **kwargs)
