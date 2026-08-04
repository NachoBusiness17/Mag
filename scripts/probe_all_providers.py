"""Probe all providers: configured? live PONG? No secrets printed."""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.env_load import load_dotenv
from models.providers import chat_provider, reload_providers, status_table


def main() -> int:
    load_dotenv(override=True)
    reload_providers()
    st = status_table()
    print("=== CONFIGURED ===")
    for p in st["providers"]:
        print(
            f"  {p['id']:12} configured={str(p['configured']):5}  "
            f"default={p.get('default_model')}"
        )

    print()
    print("=== LIVE PROBE (tiny public ping) ===")
    results: list[tuple[str, str, str]] = []
    for p in st["providers"]:
        pid = p["id"]
        if not p["configured"]:
            results.append((pid, "SKIP", "no key"))
            continue
        model = p.get("default_model")
        if pid == "ollama":
            model = "gemma:2b"
        t0 = time.time()
        try:
            r = chat_provider(
                pid,
                "Reply with exactly: PONG",
                "ping",
                model=model,
                max_tokens=16,
                temperature=0,
                tier="T2",
            )
            ms = int((time.time() - t0) * 1000)
            if r.get("ok"):
                text = (r.get("text") or "").replace("\n", " ")[:50]
                results.append(
                    (pid, "OK", f"{ms}ms model={r.get('model')} text={text!r}")
                )
            else:
                err = (r.get("error") or "")[:120]
                results.append((pid, "FAIL", f"{ms}ms {err}"))
        except Exception as e:
            results.append((pid, "FAIL", str(e)[:120]))

    for pid, status, detail in results:
        print(f"  {pid:12} {status:4}  {detail}")

    ok_n = sum(1 for _, s, _ in results if s == "OK")
    fail_n = sum(1 for _, s, _ in results if s == "FAIL")
    skip_n = sum(1 for _, s, _ in results if s == "SKIP")
    print()
    print(
        f"SUMMARY: {ok_n} working · {fail_n} failed · {skip_n} no key "
        f"(of {len(results)} providers)"
    )
    return 0 if ok_n >= 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
