"""Full local Ollama / Gemma usage graph from Mag logs."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    usage = ROOT / "logs" / "usage.jsonl"
    prov = ROOT / "logs" / "provider_usage.jsonl"

    by_model: dict = defaultdict(
        lambda: {"n": 0, "ms": 0, "chars": 0, "roles": defaultdict(int), "ok": 0, "fail": 0}
    )
    by_role: dict = defaultdict(lambda: {"n": 0, "ms": 0, "chars": 0, "models": set()})
    by_day: dict = defaultdict(lambda: defaultdict(int))
    by_action: dict = defaultdict(int)

    if usage.is_file():
        for line in usage.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            by_action[str(r.get("action") or "?")] += 1
            m = r.get("meta") or {}
            model = str(m.get("model") or "")
            role = str(m.get("role") or "")
            if r.get("action") == "chat" or (model and "gemma" in model.lower()):
                model = model or "unknown-local"
                by_model[model]["n"] += 1
                by_model[model]["ms"] += int(m.get("ms") or 0)
                by_model[model]["chars"] += int(m.get("chars") or 0)
                if r.get("ok", True):
                    by_model[model]["ok"] += 1
                else:
                    by_model[model]["fail"] += 1
                if role:
                    by_model[model]["roles"][role] += 1
                by_role[role or "?"]["n"] += 1
                by_role[role or "?"]["ms"] += int(m.get("ms") or 0)
                by_role[role or "?"]["chars"] += int(m.get("chars") or 0)
                if model:
                    by_role[role or "?"]["models"].add(model)
                ts = str(r.get("ts") or "")[:10]
                if ts:
                    by_day[ts][model] += 1

    ollama_prov = {"calls": 0, "tokens": 0, "prompt": 0, "completion": 0}
    if prov.is_file():
        for line in prov.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("provider") == "ollama":
                ollama_prov["calls"] += int(r.get("calls") or 1)
                ollama_prov["tokens"] += int(r.get("tokens") or 0)
                ollama_prov["prompt"] += int(r.get("prompt_tokens") or 0)
                ollama_prov["completion"] += int(r.get("completion_tokens") or 0)

    print("=== LOCAL OLLAMA / GEMMA (usage.jsonl chat path) ===")
    total_n = total_ms = total_chars = 0
    for model, s in sorted(by_model.items(), key=lambda x: -x[1]["n"]):
        est = s["chars"] // 4
        total_n += s["n"]
        total_ms += s["ms"]
        total_chars += s["chars"]
        roles = ", ".join(f"{k}:{v}" for k, v in sorted(s["roles"].items()))
        print(model)
        print(
            f"  calls={s['n']}  wall={s['ms']/1000:.1f}s  out_chars={s['chars']}  "
            f"est_out_tokens~{est}  ok={s['ok']} fail={s['fail']}"
        )
        print(f"  roles: {roles or '—'}")
    print(
        f"TOTAL chat calls={total_n}  wall={total_ms/1000:.1f}s  "
        f"est_out_tokens~{total_chars//4}"
    )

    print()
    print("=== BY ROLE ===")
    for role, s in sorted(by_role.items(), key=lambda x: -x[1]["n"]):
        models = ",".join(sorted(s["models"])) or "?"
        print(
            f"  {role or '?':14} n={s['n']:3} wall={s['ms']/1000:7.1f}s  "
            f"est_out~{s['chars']//4:5}  models={models}"
        )

    print()
    print("=== BY DAY ===")
    for day in sorted(by_day.keys()):
        parts = "  ".join(
            f"{m.split(':')[0]}={c}" for m, c in sorted(by_day[day].items())
        )
        print(f"  {day}  {parts}")

    print()
    print("=== OLLAMA OpenAI-compat path (provider_usage — real in+out when reported) ===")
    print(
        f"  calls={ollama_prov['calls']}  tokens={ollama_prov['tokens']}  "
        f"(prompt={ollama_prov['prompt']} completion={ollama_prov['completion']})"
    )

    print()
    print("=== ALL LOGGED ACTIONS (includes non-LLM brief/visual) ===")
    for a, c in sorted(by_action.items(), key=lambda x: -x[1]):
        print(f"  {a:16} {c}")

    print()
    print("=== CALL VOLUME ===")
    mx = max((s["n"] for s in by_model.values()), default=1) or 1
    for model, s in sorted(by_model.items(), key=lambda x: -x[1]["n"]):
        bar = "#" * max(1, int(40 * s["n"] / mx))
        print(f"  {model[:26]:26} {bar} {s['n']}")

    print()
    print("=== WALL TIME ===")
    mxm = max((s["ms"] for s in by_model.values()), default=1) or 1
    for model, s in sorted(by_model.items(), key=lambda x: -x[1]["ms"]):
        bar = "#" * max(1, int(40 * s["ms"] / mxm))
        print(f"  {model[:26]:26} {bar} {s['ms']/1000:.1f}s")

    print()
    print("=== EST OUTPUT TOKENS (chars/4) ===")
    mxt = max((s["chars"] // 4 for s in by_model.values()), default=1) or 1
    for model, s in sorted(by_model.items(), key=lambda x: -x[1]["chars"]):
        est = s["chars"] // 4
        bar = "#" * max(1, int(40 * est / mxt))
        print(f"  {model[:26]:26} {bar} ~{est}")

    print()
    print("NOTE: Input tokens for LangChain chat path usually uncounted.")
    print("      Real in+out only on provider_usage ollama rows above.")
    print("      No Meta Llama local model loaded — only gemma:2b + gemma4.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
