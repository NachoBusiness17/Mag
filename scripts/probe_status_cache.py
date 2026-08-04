"""Write last probe snapshot for Board (no secrets)."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.env_load import load_dotenv
from models.providers import chat_provider, reload_providers, status_table

OUT = ROOT / "logs" / "probe_status_latest.json"


def main(*, live: bool = True) -> int:
    load_dotenv(override=True)
    reload_providers()
    st = status_table()
    rows = []
    for p in st["providers"]:
        pid = p["id"]
        row = {
            "id": pid,
            "configured": p["configured"],
            "probe": "skip",
            "ok": False,
            "detail": "no key" if not p["configured"] else "",
            "ms": None,
        }
        if live and p["configured"]:
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
                    max_tokens=8,
                    temperature=0,
                    tier="T2",
                )
                ms = int((time.time() - t0) * 1000)
                row["ms"] = ms
                if r.get("ok"):
                    row["probe"] = "ok"
                    row["ok"] = True
                    row["detail"] = f"PONG {ms}ms"
                else:
                    row["probe"] = "fail"
                    row["detail"] = (r.get("error") or "")[:120]
            except Exception as e:
                row["probe"] = "fail"
                row["detail"] = str(e)[:120]
        rows.append(row)

    payload = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "providers": rows,
        "working": [r["id"] for r in rows if r["ok"]],
        "failed": [r["id"] for r in rows if r["probe"] == "fail"],
        "no_key": [r["id"] for r in rows if r["probe"] == "skip"],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    live = "--no-live" not in sys.argv
    raise SystemExit(main(live=live))
