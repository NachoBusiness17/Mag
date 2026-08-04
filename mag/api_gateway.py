"""Mag API Gateway — foundation for the sovereign HTTP surface.

Epoch 1 · Pillar I (Infrastructure & Deployment).

This module is the *foundation* only: it owns the security gate and the
route registry. Concrete endpoints are registered by later epochs (and by
callers) via :func:`route`. It is deliberately dependency-light and lazy —
importing ``mag.api_gateway`` must NOT pull the LangGraph daemon chain or
any model stack.

Security model
--------------
Every registered endpoint is gated by an ``X-API-Key`` header. The gate is
enforced by :func:`dispatch` before any route resolution runs, so a valid
key is always required. The comparison is constant-time (XOR-accumulate)
with no early exit on byte mismatch.

Contract
--------
- ``HandlerFn = Callable[[dict, dict | None], tuple[int, dict]]``
  ``(params, body) -> (status, body_dict)``.
- :func:`dispatch` returns ``(status, envelope)`` and never raises for
  well-formed string inputs; 401/404/405/500 are returned as ``_err``
  envelopes.
- Envelope shape mirrors ``dashboard/rest.py``: ``{"ok": bool, "schema":
  str, "data": ...}`` for success, ``{"ok": False, "error": str, ...}``
  for failure.
"""

from __future__ import annotations

import os
import time
from typing import Any, Callable, Optional

# ---------------------------------------------------------------------------
# Envelope helpers
# ---------------------------------------------------------------------------

HandlerFn = Callable[[dict, Optional[dict]], tuple[int, dict]]


def _ok(data: dict, schema: str = "ok") -> tuple[int, dict]:
    """Return a 200-style success envelope merged with ``data``."""
    body: dict[str, Any] = {"ok": True, "schema": schema}
    body.update(data)
    return 200, body


def _err(status: int, message: str, **extra: Any) -> tuple[int, dict]:
    """Return an error envelope with a truncated message."""
    body: dict[str, Any] = {"ok": False, "error": message[:500]}
    body.update(extra)
    return status, body


# ---------------------------------------------------------------------------
# API key gate
# ---------------------------------------------------------------------------

API_KEY_HEADER = "X-API-Key"
_ENV_KEY = "MAG_API_KEY"


def api_key() -> str:
    """Return the configured API key (env override wins)."""
    return os.environ.get(_ENV_KEY, "mag-local-dev-key")


def _const_eq(a: str, b: str) -> bool:
    """Constant-time string equality (XOR-accumulate, no early exit)."""
    if len(a) != len(b):
        return False
    result = 0
    for ca, cb in zip(a, b):
        result |= ord(ca) ^ ord(cb)
    return result == 0


def check_api_key(headers: dict) -> bool:
    """Return True if ``headers`` carries a valid API key.

    Header lookup is case-insensitive for the two common casings; callers
    should normalize header keys to lowercase before calling :func:`dispatch`
    for full case-insensitivity.
    """
    expected = api_key()
    presented = headers.get(API_KEY_HEADER) or headers.get(API_KEY_HEADER.lower())
    if presented is None:
        return False
    return _const_eq(presented.strip(), expected)


# ---------------------------------------------------------------------------
# Route registry
# ---------------------------------------------------------------------------

_ROUTES: dict[str, dict[str, HandlerFn]] = {}


def route(method: str, path: str) -> Callable[[HandlerFn], HandlerFn]:
    """Decorator factory registering ``fn`` for ``method`` + ``path``.

    ``path`` may contain ``{name}`` segments captured as path params, e.g.
    ``/items/{sid}``. Registering the same ``(method, path)`` twice silently
    overwrites the previous handler.
    """

    def decorator(fn: HandlerFn) -> HandlerFn:
        m = method.upper()
        _ROUTES.setdefault(m, {})[path] = fn
        return fn

    return decorator


def _capture(pattern: str, path: str) -> Optional[dict[str, str]]:
    """Return captured params if ``path`` matches ``pattern``, else None."""
    p_parts = pattern.split("/")
    path_parts = path.split("/")
    if len(p_parts) != len(path_parts):
        return None
    params: dict[str, str] = {}
    for p, v in zip(p_parts, path_parts):
        if p.startswith("{") and p.endswith("}"):
            params[p[1:-1]] = v
        elif p != v:
            return None
    return params


def _match(method: str, path: str) -> tuple[Optional[HandlerFn], dict]:
    """Resolve ``(handler, params)`` for ``method`` + ``path``."""
    handlers = _ROUTES.get(method, {})
    if path in handlers:
        return handlers[path], {}
    # Pattern match over registered paths containing {name}.
    for registered, fn in handlers.items():
        if "{" not in registered:
            continue
        params = _capture(registered, path)
        if params is not None:
            return fn, params
    return None, {}


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def dispatch(method: str, path: str, headers: dict, body: Optional[dict] = None) -> tuple[int, dict]:
    """Route a request through the security gate and registry.

    Returns ``(status, envelope)`` and never raises for well-formed string
    inputs. 401 (gate), 405 (no method), 404 (no route), 500 (handler error).
    """
    if not check_api_key(headers):
        return _err(401, "missing or invalid API key")

    m = method.upper()
    if m not in _ROUTES:
        return _err(405, f"method not allowed: {m}")

    fn, params = _match(m, path)
    if fn is None:
        return _err(404, f"no route for {m} {path}")

    try:
        return fn(params, body)
    except Exception as e:  # noqa: BLE001 — envelope, never raise
        return _err(500, f"handler error: {e}")


# ---------------------------------------------------------------------------
# Built-in endpoints
# ---------------------------------------------------------------------------

@route("GET", "/health")
def _health(params: dict, body: Optional[dict]) -> tuple[int, dict]:
    """Liveness probe."""
    return _ok({"status": "up", "ts": time.time()})


@route("GET", "/routes")
def _routes(params: dict, body: Optional[dict]) -> tuple[int, dict]:
    """List registered routes (method -> paths)."""
    listing = {m: sorted(paths) for m, paths in _ROUTES.items()}
    return _ok({"routes": listing})


# ---------------------------------------------------------------------------
# Example handler (Epoch 1 placeholder)
# ---------------------------------------------------------------------------

@route("POST", "/v1/chat")
def _chat(params: dict, body: Optional[dict]) -> tuple[int, dict]:
    """Placeholder chat endpoint.

    The API-key gate is enforced by :func:`dispatch` before this handler runs,
    so a valid ``X-API-Key`` header is always required.

    Contract
    --------
    Request body: ``{"text": "<prompt>"}``.

    * ``text`` must be a non-empty string — otherwise ``400``.
    * The DeepSeekOrchestrator is intentionally NOT integrated yet. This handler
      simulates processing by waiting 3 seconds (simulated thinking time) and
      returning a fixed dummy result so callers can exercise the full request
      lifecycle end-to-end.
    """
    if not body or not isinstance(body.get("text"), str) or not body["text"].strip():
        return _err(400, "body.text must be a non-empty string")
    time.sleep(3)  # simulated thinking time
    return _ok({"reply": "dummy reply (orchestrator not yet integrated)"}, schema="chat")
