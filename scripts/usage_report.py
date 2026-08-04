"""Report local vs remote token usage from Mag logs."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    usage = ROOT / "logs" / "usage.jsonl"
    prov = ROOT / "logs" / "provider_usage.jsonl"

    by_prov: dict[str, dict] = defaultdict(
        lambda: {
            "calls": 0,
            "tokens": 0,
            "prompt": 0,
            "completion": 0,
            "ok": 0,
            "fail": 0,
        }
    )
    if prov.is_file():
        for line in prov.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            p = r.get("provider") or "?"
            by_prov[p]["calls"] += int(r.get("calls") or 1)
            by_prov[p]["tokens"] += int(r.get("tokens") or 0)
            by_prov[p]["prompt"] += int(r.get("prompt_tokens") or 0)
            by_prov[p]["completion"] += int(r.get("completion_tokens") or 0)
            if r.get("ok"):
                by_prov[p]["ok"] += 1
            else:
                by_prov[p]["fail"] += 1

    print("=== provider_usage.jsonl (API token counts when reported) ===")
    local_tok = remote_tok = 0
    local_calls = remote_calls = 0
    for p, s in sorted(by_prov.items()):
        print(
            f"  {p:12} calls={s['calls']:4} tokens={s['tokens']:7} "
            f"(prompt={s['prompt']} completion={s['completion']}) "
            f"ok={s['ok']} fail={s['fail']}"
        )
        if p == "ollama":
            local_tok += s["tokens"]
            local_calls += s["calls"]
        else:
            remote_tok += s["tokens"]
            remote_calls += s["calls"]

    print()
    print(f"LOCAL  (ollama API path):  calls={local_calls}  tokens={local_tok}")
    print(f"REMOTE (all cloud APIs):   calls={remote_calls} tokens={remote_tok}")
    xai = by_prov.get("xai") or {}
    print(
        f"  xAI API only:            calls={xai.get('calls', 0)} tokens={xai.get('tokens', 0)} "
        f"(fails may be 0 tokens)"
    )

    # L0 chat() via langchain — often no token usage object
    chat_roles: dict[str, dict] = defaultdict(lambda: {"n": 0, "ms": 0, "chars": 0, "models": set()})
    lanes: dict[str, int] = defaultdict(int)
    actions: dict[str, int] = defaultdict(int)
    if usage.is_file():
        for line in usage.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            lanes[str(r.get("lane") or "?")] += 1
            actions[str(r.get("action") or "?")] += 1
            m = r.get("meta") or {}
            if r.get("action") == "chat" or m.get("model"):
                role = str(m.get("role") or r.get("action") or "?")
                chat_roles[role]["n"] += 1
                chat_roles[role]["ms"] += int(m.get("ms") or 0)
                chat_roles[role]["chars"] += int(m.get("chars") or 0)
                if m.get("model"):
                    chat_roles[role]["models"].add(str(m["model"]))

    print()
    print("=== usage.jsonl L0 chat() (Ollama via LangChain — output chars; tokens often missing) ===")
    est_total = 0
    n_total = 0
    for role, s in sorted(chat_roles.items()):
        est = s["chars"] // 4
        est_total += est
        n_total += s["n"]
        models = ",".join(sorted(s["models"])) or "?"
        print(
            f"  {role:16} n={s['n']:4} ms={s['ms']:8} out_chars={s['chars']:7} "
            f"est_out_tokens~{est} models={models}"
        )
    print(f"  TOTAL chat events: {n_total}  est output tokens only ~{est_total}")
    print(f"  (input tokens for these chats usually NOT counted unless Ollama reports them)")

    print()
    print("lane events:", dict(lanes))
    print("actions:", dict(actions))
    print()
    print("=== Grok TUI (this conversation) ===")
    print("  NOT metered in Mag logs.")
    print("  Check xAI / Grok account UI for subscription usage.")
    print("  Mag only tracks: Ollama, remote APIs, and optional grok -p escalates.")
    print()
    # Combined rough picture
    print("=== ROUGH PICTURE ===")
    print(f"  Local tokens known (provider path):  {local_tok}")
    print(f"  Local chat est OUT only (L0 path):   ~{est_total}")
    print(f"  Remote API tokens known:             {remote_tok}")
    print(f"  Grok TUI tokens:                     unknown here")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
