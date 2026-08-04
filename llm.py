"""Ollama chat via langchain-ollama (preferred) with raw-HTTP fallback.

Every call traced to usage.jsonl. The HTTP fallback exists so the L0 worker
keeps running on seats where langchain_ollama is not installed (e.g. Hermes
venv) — local-first, no single-oracle dependency on one Python env.
"""
from __future__ import annotations

import json
import re
import time
import urllib.request
from typing import Any

from models.registry import model_for, require_model


def _resolve_base() -> str:
    try:
        from config import ollama_base

        return ollama_base()
    except Exception:
        return "http://127.0.0.1:11434"


def _chat_http(base: str, model: str, system: str, user: str, temperature: float) -> str:
    """Raw POST to Ollama /api/chat — no langchain required."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "temperature": temperature,
    }
    req = urllib.request.Request(
        base.rstrip("/") + "/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    content = body.get("message", {}).get("content")
    return str(content) if content is not None else ""


def chat(
    role: str,
    system: str,
    user: str,
    temperature: float = 0.2,
    *,
    strict: bool = True,
) -> str:
    """Chat with role-mapped model. Logs role/model/ms/ok. Raises if model missing (strict)."""
    t0 = time.perf_counter()
    model = require_model(role, strict=strict) if strict else model_for(role)
    ok = False
    err = None
    text = ""
    base = _resolve_base()
    try:
        try:
            from langchain_ollama import ChatOllama

            llm = ChatOllama(model=model, temperature=temperature, base_url=base)
            messages = [
                ("system", system),
                ("human", user),
            ]
            resp = llm.invoke(messages)
            content = resp.content
            if isinstance(content, list):
                parts = []
                for p in content:
                    if isinstance(p, dict) and "text" in p:
                        parts.append(p["text"])
                    else:
                        parts.append(str(p))
                text = "\n".join(parts)
            else:
                text = str(content)
        except ImportError:
            # langchain_ollama absent in this env (Hermes venv etc.) — raw HTTP fallback.
            text = _chat_http(base, model, system, user, temperature)
        ok = True
        return text
    except Exception as e:
        err = str(e)
        raise
    finally:
        ms = int((time.perf_counter() - t0) * 1000)
        _log_usage(role=role, model=model, ms=ms, ok=ok, error=err, chars=len(text or ""))


def _log_usage(
    *,
    role: str,
    model: str,
    ms: int,
    ok: bool,
    error: str | None,
    chars: int,
) -> None:
    try:
        from mag.lanes import log_usage

        log_usage(
            lane="L0",
            action="chat",
            detail=f"role={role} model={model} ms={ms}",
            ok=ok,
            meta={
                "role": role,
                "model": model,
                "ms": ms,
                "chars": chars,
                "error": (error or "")[:300] or None,
            },
        )
    except Exception:
        # fallback append without mag.lanes
        try:
            from config import ROOT
            from datetime import datetime, timezone

            path = ROOT / "logs" / "usage.jsonl"
            path.parent.mkdir(parents=True, exist_ok=True)
            row = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "lane": "L0",
                "action": "chat",
                "ok": ok,
                "meta": {"role": role, "model": model, "ms": ms, "chars": chars},
            }
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")
        except Exception:
            pass


def extract_json(text: str) -> dict[str, Any] | None:
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None
