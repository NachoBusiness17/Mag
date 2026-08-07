"""Dual-seat Mag research: DeepSeek structure + OpenAI fable on DM tools pack.

Usage:
  .venv\\Scripts\\python.exe scripts/dm_tools_dual_research.py
Writes: memory/working/research/dm_tools_dual_<ts>/
"""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from config import ROOT
from models.providers import chat_provider

PACK = """# Mag dual-seat research pack (T2 public only)
## Mag snapshot
- Home multi-agent harness: local / DeepSeek / OpenAI / Grok TUI
- Dogfood: /table + voice D&D adventure; engine owns HP/rooms/legal moves
- Shipped: classic module, multi-NPC tavern brawl, Tavern Brawler, passage card
  (Interior/Area/Environment/Narrator/Leads), speak_text=narrator only, corpus_query,
  Fast engine / Slow color, play_benchmark B0-B2
- Missing: multiplayer VTT scene, map tokens/fog, audio, session recap pipeline,
  deep generators, plugin/extension contract, polished combat HUD

## Reddit OP stack (r/rpg favourite after 15 apps)
1. Notion — world builder / linked databases (NPC-shop-quest)
2. Saga20 — session transcription + recaps
3. Syrinscape — layered music/SFX
4. Lost Atlas — map search for prep
5. Shieldmaiden — combat tracker + autobalance
Comments: Owlbear simplicity vs Foundry depth; Tokenstamp2; donjon; NotebookLM PDF RAG;
Improved Initiative; pushback that tools can kill soul/note-taking value

## donjon.bin.sh
Free RPG generators: fantasy names, random NPC/loot/quest, random inn/tavern,
dungeon / 5-room dungeon, 5e encounter/treasure/magic shop, initiative trackers, weather.
Mag law: generators feed engine tables/modules — not freestyle LLM invent of rooms.

## Owlbear Rodeo core (owlbear.rodeo)
Thin browser VTT: maps, tokens, scenes, multiplayer. Shell not Foundry.
Mag map: /table=shell, campaign engine=truth.

## Owlbear extensions (owlbear.rogue.pub/extensions ~234)
Categories: Combat, Dice, Fog, Automation, Tool, Audio, Drawing.
Exemplar patterns: Battle Board / Clash! (combat HUD), Dynamic Fog, dddice/Dice+,
Crawl! (procedural dungeon), Hoot (music), GM Grimoire (HP/init/loot), Condition Markers.
Steal: extension manifest — small core + optional plugins; not code clone.

## Law for answers
Steal contracts/patterns only. No secrets. No invent Mag APIs. Engine owns truth.
Prefer Mag FILE paths that exist or are one PR away.
"""

SYS_DS = (
    "You are a structure specialist for Mag multi-agent project. "
    "Output markdown tables as requested. Mag engine owns game truth. "
    "No flattery. No secrets. Be concrete about Mag paths "
    "(e.g. mag/game_brawl.py, dashboard/static/table.html, memory/game_modules/)."
)

JOB_DS = """From the pack, produce:

## Matrix
| family | example tools | Mag path (file/module) | take/leave/hold | why | acceptance smoke |
Cover: world notes, session recap, combat HUD, map search, audio, generators (donjon),
VTT shell (Owlbear), extensions marketplace.

## Gaps (rank 7)
| rank | gap | risk if ignored | smoke signal | FILE path |

## Extension contract sketch
5-10 fields for Mag table extension manifest (name, slot, engine_hooks, never_writes, ...)

## Do not
Bullets: Full Foundry clone; audio-first product; invent APIs that do not exist.
"""

SYS_OAI = (
    "You are a product researcher helping Mag (home multi-agent D&D table dogfood). "
    "Scannable markdown. Concrete tools. Mag is not Foundry. Engine owns rules; models color. "
    "No roleplay as Mag system. No secrets."
)

JOB_OAI = """From the pack, produce:

## Player-facing gaps
What feels missing on Mag /table vs a real web adventure.

## Learn-from list (8-12)
| tool | free/paid | web/PC | pattern to steal | leave behind |
Must include Notion, Saga20, Shieldmaiden, donjon, Owlbear core, and at least 2 Owlbear extensions by name.

## Three do-not-builds

## One next slice (2 weeks)
Name · UX · engine touchpoints · success demo on /table

## Soft leads for the operator
3 concrete next human decisions
"""


def run_seat(name: str, provider: str, system: str, job: str) -> dict:
    t0 = time.time()
    user = "## Pack\n" + PACK + "\n\n## Job\n" + job
    try:
        res = chat_provider(
            provider,
            system,
            user,
            tier="T2",
            max_tokens=1600,
            temperature=0.35,
        )
        ms = int((time.time() - t0) * 1000)
        text = ""
        if res.get("ok"):
            text = str(res.get("text") or res.get("content") or res.get("answer") or "")
        return {
            "seat": name,
            "provider": provider,
            "ok": bool(res.get("ok")),
            "model": res.get("model"),
            "latency_ms": ms,
            "error": None if res.get("ok") else str(res.get("error") or res)[:400],
            "text": text,
        }
    except Exception as e:
        return {
            "seat": name,
            "provider": provider,
            "ok": False,
            "model": None,
            "latency_ms": int((time.time() - t0) * 1000),
            "error": str(e)[:400],
            "text": "",
        }


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = ROOT / "memory" / "working" / "research" / f"dm_tools_dual_{ts}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "pack.md").write_text(PACK, encoding="utf-8")

    meta: dict = {
        "schema": "mag_dual_research.v1",
        "ts": datetime.now(timezone.utc).isoformat(),
        "dir": str(out.relative_to(ROOT)).replace("\\", "/"),
        "seats": {},
    }

    with ThreadPoolExecutor(max_workers=2) as ex:
        futs = [
            ex.submit(run_seat, "structure", "deepseek", SYS_DS, JOB_DS),
            ex.submit(run_seat, "fable", "openai", SYS_OAI, JOB_OAI),
        ]
        for fut in as_completed(futs):
            r = fut.result()
            fname = "deepseek.md" if r["provider"] == "deepseek" else "openai.md"
            body = r["text"] if r["ok"] else f"# FAIL\n\n{r.get('error')}\n"
            (out / fname).write_text(body, encoding="utf-8")
            meta["seats"][r["provider"]] = {
                "ok": r["ok"],
                "model": r.get("model"),
                "latency_ms": r.get("latency_ms"),
                "error": r.get("error"),
                "chars": len(r.get("text") or ""),
            }
            print(
                r["provider"],
                "ok=",
                r["ok"],
                "ms=",
                r.get("latency_ms"),
                "chars=",
                len(r.get("text") or ""),
                "err=",
                (r.get("error") or "")[:100],
            )

    (out / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("OUT", out)
    print(json.dumps(meta, indent=2))
    both = all(s.get("ok") for s in meta["seats"].values())
    return 0 if both else 1


if __name__ == "__main__":
    raise SystemExit(main())
