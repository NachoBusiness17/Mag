"""Probe lanes for real — not hallucination.

L0: Ollama chat roundtrip
L1: OpenRouter (if key) public model ping — never send T0/T1
L2: grok harness availability (no spend unless --live)
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


def probe_l0(prompt: str = "Reply with exactly: PONG") -> dict[str, Any]:
    try:
        from llm import chat

        out = chat("router", "You are a probe. Reply with only the requested token.", prompt, temperature=0)
        text = (out or "").strip()
        ok = "PONG" in text.upper()
        return {
            "lane": "L0",
            "ok": ok,
            "backend": "ollama",
            "raw": text[:200],
            "evidence": "local chat roundtrip",
            "hallucination_risk": "low" if ok else "model drifted or ollama down",
        }
    except Exception as e:
        return {"lane": "L0", "ok": False, "error": str(e), "evidence": "exception"}


def probe_l1(prompt: str = "Reply with exactly: PONG") -> dict[str, Any]:
    key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OR_API_KEY")
    if not key:
        return {
            "lane": "L1",
            "ok": False,
            "configured": False,
            "evidence": "no OPENROUTER_API_KEY",
            "how_to": "setx OPENROUTER_API_KEY <key> then new shell; use public T2 prompts only",
        }
    model = os.environ.get("OPENROUTER_MODEL") or "openrouter/auto"
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": "Probe only. Reply with exactly: PONG"},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 16,
            "temperature": 0,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://127.0.0.1:8765",
            "X-Title": "Mag Resource Harness probe",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
        text = (
            ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        ).strip()
        ok = "PONG" in text.upper()
        return {
            "lane": "L1",
            "ok": ok,
            "configured": True,
            "backend": "openrouter",
            "model": model,
            "raw": text[:200],
            "evidence": "HTTP chat completion",
            "tier_rule": "T2+ public only — never paste live_from_grok or private archive",
        }
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")[:300]
        return {"lane": "L1", "ok": False, "configured": True, "error": f"HTTP {e.code}: {err}"}
    except Exception as e:
        return {"lane": "L1", "ok": False, "configured": True, "error": str(e)}


def probe_l2() -> dict[str, Any]:
    try:
        from harness.grok_cli import harness_available

        avail = harness_available()
        return {
            "lane": "L2",
            "ok": avail,
            "backend": "grok_cli",
            "evidence": "which/path probe via harness_available()",
            "note": "Full escalate still needs [priority] + budget; this only checks binary presence",
        }
    except Exception as e:
        return {"lane": "L2", "ok": False, "error": str(e)}


def probe_all(*, include_l1_chat: bool = True) -> dict[str, Any]:
    l0 = probe_l0()
    l1 = probe_l1() if include_l1_chat else {"lane": "L1", "skipped": True}
    l2 = probe_l2()
    return {
        "ok": bool(l0.get("ok")),  # local is required; L1/L2 optional
        "L0": l0,
        "L1": l1,
        "L2": l2,
        "verdict": (
            "L0 working — local harness is real"
            if l0.get("ok")
            else "L0 FAILED — fix Ollama before trusting any Mag LLM claim"
        ),
    }
