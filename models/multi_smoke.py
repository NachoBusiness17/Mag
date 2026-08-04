"""M0 dual-local multi-model smoke — public fixture only.

Pass only if clerk + worker (+ critic) all respond and two model ids appear.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import ROOT


FIXTURE = ROOT / "configs" / "selftest" / "multi_smoke_fixture.txt"
LOG_DIR = ROOT / "logs"
LATEST = LOG_DIR / "multi_smoke_latest.json"


def _fixture_text() -> str:
    if FIXTURE.is_file():
        return FIXTURE.read_text(encoding="utf-8")
    return (
        "Local Mag harness: small model routes, large model writes briefs. "
        "Grok is scarce. Private data stays local."
    )


def run_multi_smoke() -> dict[str, Any]:
    from llm import chat, extract_json
    from models.registry import inventory, model_for

    inv = inventory()
    text = _fixture_text()
    steps: list[dict[str, Any]] = []
    models_seen: set[str] = set()

    # --- 1 clerk / router ---
    clerk_model = model_for("router")
    models_seen.add(clerk_model)
    try:
        raw = chat(
            "router",
            'Classify the task. Reply JSON only: {"lane":"local|escalate|wait","reason":"..."}',
            f"Public fixture (not private chat):\n{text}\n\n"
            "Should Mag handle this locally, escalate to Grok, or wait for human?",
            temperature=0.1,
        )
        data = extract_json(raw) or {}
        lane = str(data.get("lane") or "").lower()
        ok = lane in {"local", "escalate", "wait"} or "local" in raw.lower()
        if not lane and "local" in raw.lower():
            lane = "local"
        steps.append(
            {
                "id": "clerk_route",
                "role": "router",
                "model": clerk_model,
                "ok": ok,
                "lane": lane or None,
                "raw": (raw or "")[:400],
            }
        )
    except Exception as e:
        steps.append(
            {"id": "clerk_route", "role": "router", "model": clerk_model, "ok": False, "error": str(e)}
        )

    # --- 2 worker brief ---
    worker_model = model_for("worker")
    models_seen.add(worker_model)
    try:
        raw = chat(
            "worker",
            "Summarize in exactly 3 short bullet lines. No preamble. Truth only.",
            f"Fixture:\n{text}",
            temperature=0.15,
        )
        bullets = [ln for ln in raw.splitlines() if ln.strip().startswith(("-", "*", "•")) or re.match(r"^\d+\.", ln.strip())]
        if len(bullets) < 3:
            # accept 3+ non-empty lines
            bullets = [ln for ln in raw.splitlines() if ln.strip()][:3]
        ok = len(bullets) >= 3 and len(raw.strip()) > 40
        steps.append(
            {
                "id": "worker_brief",
                "role": "worker",
                "model": worker_model,
                "ok": ok,
                "n_lines": len(bullets),
                "raw": (raw or "")[:500],
            }
        )
    except Exception as e:
        steps.append(
            {"id": "worker_brief", "role": "worker", "model": worker_model, "ok": False, "error": str(e)}
        )

    # --- 3 critic risk ---
    critic_model = model_for("critic")
    models_seen.add(critic_model)
    try:
        raw = chat(
            "critic",
            "Name exactly one real risk in one sentence. Plain English.",
            f"Fixture:\n{text}\n\nWhat is the main risk if we treat this as finished?",
            temperature=0.15,
        )
        risk_words = ("risk", "theater", "polish", "empty", "claim", "private", "tier", "soil", "finish", "mirror")
        ok = len(raw.strip()) > 20 and any(w in raw.lower() for w in risk_words)
        steps.append(
            {
                "id": "critic_risk",
                "role": "critic",
                "model": critic_model,
                "ok": ok,
                "raw": (raw or "")[:400],
            }
        )
    except Exception as e:
        steps.append(
            {"id": "critic_risk", "role": "critic", "model": critic_model, "ok": False, "error": str(e)}
        )

    dual = len([m for m in models_seen if m]) >= 2 or (
        clerk_model != worker_model and all(s.get("ok") for s in steps[:2] if "error" not in s or steps[0].get("ok"))
    )
    # stronger dual check: clerk model id != worker model id
    dual_ids = clerk_model != worker_model
    all_ok = all(s.get("ok") for s in steps) and dual_ids

    result = {
        "schema": "multi_smoke.v1",
        "ok": all_ok,
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "fixture": str(FIXTURE.relative_to(ROOT)) if FIXTURE.is_file() else "inline",
        "models_seen": sorted(models_seen),
        "dual_local": dual_ids,
        "clerk_model": clerk_model,
        "worker_model": worker_model,
        "steps": steps,
        "inventory": inv,
        "verdict": (
            "PASS — dual-local multi-model is real"
            if all_ok
            else "FAIL — fix Ollama models or role map; see steps"
        ),
        "anti_hallucination": "Trust this JSON + usage.jsonl model fields, not chat claims.",
    }

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = LOG_DIR / f"multi_smoke_{stamp}.json"
    raw_out = json.dumps(result, indent=2, default=str)
    path.write_text(raw_out, encoding="utf-8")
    LATEST.write_text(raw_out, encoding="utf-8")
    result["path"] = str(path)
    result["latest"] = str(LATEST)

    try:
        from mag.lanes import log_usage

        log_usage(
            lane="L0",
            action="multi_smoke",
            detail=result["verdict"],
            ok=all_ok,
            meta={"models": sorted(models_seen), "path": str(path)},
        )
    except Exception:
        pass

    return result


def last_smoke() -> dict[str, Any] | None:
    if not LATEST.is_file():
        return None
    try:
        return json.loads(LATEST.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
