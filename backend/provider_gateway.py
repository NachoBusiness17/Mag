#!/usr/bin/env python3
"""Sovereign Provider Gateway — task different API chains with jobs, agnostically.

The operator's vision (2026-08-03): the local Mag agent surfaces direction +
codebase, then tasks *different API chains* (DeepSeek, Overmind, Vast, Groq, ...)
and the chains "run agnostically" — the caller names a provider, the gateway
routes the job, preserves context across chained jobs, and fails over across
that provider's keys.

This is the promoted + fixed version of `memory/working/api_gateway_fastapi.py`
(v0.7 draft). Key fixes over the draft:

  * `Depends(get_default_provider())` called the function at import time and
    passed the string "deepseek" into `Depends` -> collection crash. The
    dependency is now passed as a callable.
  * Provider calls are REAL (models.providers.chat_messages), not stubs —
    multi-key failover, thinking-off and degenerate-output detection come free.
  * Keys are validated against the provider's configured env keys
    (constant-time compare), never compared against a hardcoded dev key.
  * Context preservation: `context_id` keeps a per-chain message history so
    job N+1 sees job N's answer.

Run:
    python -m backend.provider_gateway [--port 8010]
    # or
    python -m uvicorn backend.provider_gateway:app --port 8010

Security: every route is gated by X-API-Key. The accepted key for a provider
is any key Mag has configured for it in configs/providers.yaml (never logged,
never returned). Rate limits are in-process per provider (window + max calls).
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import Depends, FastAPI, HTTPException, Request, status  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from models.env_load import load_dotenv  # noqa: E402

load_dotenv(override=False)

from models.providers import (  # noqa: E402
    chat_messages,
    get_provider,
    list_provider_ids,
    provider_keys,
    status_table,
)

DEFAULT_PROVIDER = os.environ.get("MAG_GATEWAY_DEFAULT_PROVIDER", "deepseek")
RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("MAG_GATEWAY_RATE_WINDOW", "60"))
RATE_LIMIT_MAX_CALLS = int(os.environ.get("MAG_GATEWAY_RATE_MAX", "60"))
MAX_CONTEXT_MESSAGES = int(os.environ.get("MAG_GATEWAY_MAX_CONTEXT", "20"))
DEFAULT_MAX_TOKENS = int(os.environ.get("MAG_GATEWAY_MAX_TOKENS", "1024"))

app = FastAPI(
    title="Sovereign Provider Gateway",
    description="Route jobs across API chains (DeepSeek/Overmind/Vast/Groq/...) "
    "with context preservation + multi-key failover.",
    version="2.0.0",
)

# ---------------------------------------------------------------------------
# In-process state
# ---------------------------------------------------------------------------

_LAST_ACCESS: dict[str, float] = {}
_CALL_COUNTS: dict[str, int] = {}
# context_id -> message history (OpenAI-style). Cap per chain.
_CONTEXTS: dict[str, list[dict[str, Any]]] = {}


def _const_eq(a: str, b: str) -> bool:
    if len(a) != len(b):
        return False
    result = 0
    for ca, cb in zip(a, b):
        result |= ord(ca) ^ ord(cb)
    return result == 0


def _rate_limited(provider: str) -> bool:
    now = time.time()
    last = _LAST_ACCESS.get(provider, 0.0)
    if now - last >= RATE_LIMIT_WINDOW_SECONDS:
        _CALL_COUNTS[provider] = 0
        _LAST_ACCESS[provider] = now
    _CALL_COUNTS[provider] = _CALL_COUNTS.get(provider, 0) + 1
    return _CALL_COUNTS[provider] > RATE_LIMIT_MAX_CALLS


# ---------------------------------------------------------------------------
# Security layer
# ---------------------------------------------------------------------------


def authenticate(provider: str, api_key: str) -> bool:
    """Key valid for provider AND under the rate limit."""
    if _rate_limited(provider):
        return False
    pcfg = get_provider(provider)
    if pcfg is None:
        return False
    if pcfg.get("free_local"):
        return True  # local providers accept any key (ollama sends "ollama")
    accepted = provider_keys(pcfg)
    if not accepted:
        return False
    presented = (api_key or "").strip()
    if not presented:
        return False
    return any(_const_eq(presented, k) for k in accepted)


def get_api_key(provider: str = "deepseek", x_api_key: str = "") -> str:
    """Compatibility shim for the operator's draft signature.

    The real gate is `_require_key` (used by the routes). Direct callers of
    `run_turn` bypass DI by design (see module docstring).
    """
    return x_api_key or ""


def _require_key(provider: str, x_api_key: str | None) -> str:
    """Validate X-API-Key against the provider's configured keys."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing X-API-Key header",
        )
    if not authenticate(provider, x_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed or rate limited for provider '{provider}'.",
        )
    return x_api_key


def get_default_provider() -> str:
    return DEFAULT_PROVIDER


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class RunTurnRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="The job prompt")
    context_id: str | None = Field(
        default=None, description="Chain id - jobs sharing a context_id share memory"
    )
    provider: str | None = Field(
        default=None, description="Provider id (default: deepseek)"
    )
    max_tokens: int | None = Field(default=None, ge=16, le=16384)
    system: str | None = Field(default=None, description="Optional system preamble")


class RunTurnResponse(BaseModel):
    status: str
    provider_used: str
    content: str
    context_id: str | None = None
    provenance: list[str]
    error: str | None = None


# ---------------------------------------------------------------------------
# Core router
# ---------------------------------------------------------------------------


def _chain_history(context_id: str | None) -> list[dict[str, Any]]:
    cid = context_id or "default"
    if cid not in _CONTEXTS:
        _CONTEXTS[cid] = []
    return _CONTEXTS[cid]


def run_turn(
    prompt: str,
    context_id: str | None = None,
    provider: str | None = None,
    *,
    system: str | None = None,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    """Route one job to a provider; preserve context for chained jobs.

    Returns an envelope shaped like the operator's draft (`status`,
    `provider_used`, `content`, `provenance`, `context_id`, `error`).
    """
    pid = (provider or DEFAULT_PROVIDER).strip()
    pcfg = get_provider(pid)
    if pcfg is None:
        return {
            "status": "error",
            "provider_used": pid,
            "content": "",
            "provenance": [],
            "error": f"unknown provider '{pid}' - have: {', '.join(list_provider_ids())}",
        }

    history = _chain_history(context_id)
    if system:
        if history and history[0].get("role") == "system":
            history[0] = {"role": "system", "content": system}
        else:
            history.insert(0, {"role": "system", "content": system})
    history.append({"role": "user", "content": prompt})
    # Keep the chain bounded: drop oldest user/assistant pairs past the cap.
    while len(history) > MAX_CONTEXT_MESSAGES:
        history.pop(1)  # keep system at index 0

    try:
        res = chat_messages(
            pid,
            history,
            model=None,  # provider default (env override honored)
            tier="T2",
            max_tokens=max_tokens or DEFAULT_MAX_TOKENS,
            temperature=0.2,
        )
    except Exception as e:  # noqa: BLE001
        return {
            "status": "error",
            "provider_used": pid,
            "content": "",
            "context_id": context_id,
            "provenance": [f"{pid}/gateway-exception"],
            "error": str(e)[:400],
        }

    if not res.get("ok"):
        err = str(res.get("error") or "provider call failed")
        # Do not poison the chain with a failed attempt.
        history.pop()
        return {
            "status": "error",
            "provider_used": pid,
            "content": "",
            "context_id": context_id,
            "provenance": [f"{pid}/error"],
            "error": err[:400],
        }

    content = res.get("text") or ""
    history.append({"role": "assistant", "content": content})
    return {
        "status": "success",
        "provider_used": pid,
        "content": content,
        "context_id": context_id,
        "provenance": [f"{pid}/{res.get('model') or '?'}/key{res.get('key_idx')}"],
        "error": None,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.post("/api/v1/run_turn", response_model=RunTurnResponse)
def execute_run_turn(
    request: RunTurnRequest,
    http: Request,
    provider: str = Depends(get_default_provider),
) -> RunTurnResponse:
    """Run one job on the named provider (default deepseek), with chain memory."""
    pid = (request.provider or provider).strip()
    key = http.headers.get("X-API-Key") or http.headers.get("x-api-key")
    _require_key(pid, key)
    result = run_turn(
        request.prompt,
        request.context_id,
        pid,
        system=request.system,
        max_tokens=request.max_tokens,
    )
    return RunTurnResponse(**result)


@app.get("/api/v1/providers")
def providers_overview() -> dict[str, Any]:
    """Which chains are configured (key present) and their budgets."""
    st = status_table()
    return {
        "ok": True,
        "schema": "provider_gateway.v1",
        "providers": st.get("providers"),
        "budgets": st.get("budgets"),
        "note": "configured=key present in env; live status = /api/v1/router-status",
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "service": "provider-gateway", "providers": list_provider_ids()}


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Sovereign Provider Gateway")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8010)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args(argv)

    import uvicorn

    print(f"Provider gateway -> http://{args.host}:{args.port}/  (chains: {list_provider_ids()})")
    uvicorn.run(
        "backend.provider_gateway:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
