#!/usr/bin/env python3
"""Routing smoke — proves one classifier, honest failures, local execution path.

Run on home machine with keys in .env:
  .venv/Scripts/python.exe scripts/routing_smoke.py
  mag.cmd route "doctor health"

Exit 0 = routing contract holds. Exit 1 = fix before trusting autorun.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _check(name: str, cond: bool, detail: str = "") -> bool:
    mark = "PASS" if cond else "FAIL"
    print(f"  [{mark}] {name}" + (f" — {detail}" if detail else ""))
    return cond


def main() -> int:
    from mag.coordination import classify_depth, coordinate
    from mag.dispatch import _classify_job
    from mag.router import route

    print("Mag routing smoke\n")
    ok = True

    # 1 — scut → local executable
    r = route("doctor health status")
    ok &= _check("scut → local ollama", r["depth"] == "scut" and r["seat"] == "local" and r["executable"])

    # 2 — simple typo → local (not remote summarize)
    r = route("fix typo in README one file")
    ok &= _check("simple → local", r["depth"] == "simple_code" and r["seat"] == "local")

    # 3 — overview → grok pack only (never ollama provider)
    r = route("big picture interlink ecosystem map")
    ok &= _check(
        "overview → grok_tui pack",
        r["depth"] == "overview" and r["seat"] == "grok_tui" and not r["executable"],
    )
    ok &= _check("overview never ollama", r.get("provider") != "ollama")

    # 4 — heavy without keys fails loud OR executes if key set
    r = route("implement multi-file orchestrator heal loop with tests")
    has_ds = bool(os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("DEEPSEEK_OVERMIND_API_KEY"))
    if has_ds:
        ok &= _check("heavy + key → executable", r["depth"] == "heavy_code" and r["executable"])
    else:
        ok &= _check(
            "heavy no key → fail loud",
            r["depth"] == "heavy_code" and not r["executable"] and r.get("error") == "no_execution_provider",
        )

    # 5 — classifiers agree on depth
    goals = [
        "doctor health",
        "fix typo in README",
        "implement multi-file refactor",
        "big picture ecosystem",
        "via cursor wire dashboard",
    ]
    agree = all(route(g)["depth"] == classify_depth(g)["depth"] for g in goals)
    ok &= _check("coordination.classify_depth agrees", agree)

    # 6 — dispatch uses same router
    d_agree = all(route(g)["seat"] == _classify_job(g)[2] for g in goals)
    ok &= _check("dispatch._classify_job seat agrees", d_agree)

    # 7 — scut coordinate executes (local)
    res = coordinate("doctor health status", launch=True)
    ok &= _check("coordinate scut launches", res.get("ok") and res.get("action") == "dispatch")

    # 8 — plan coordinate does not execute
    res = coordinate("Plan the architecture for republic launch", launch=True)
    ok &= _check("coordinate plan → file_for_grok", res.get("action") == "file_for_grok")

    print()
    if ok:
        print("routing smoke: OK")
        return 0
    print("routing smoke: FAILED — routing is still theater until these pass")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
