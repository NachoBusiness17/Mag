#!/usr/bin/env python3
"""CLI for local_sovereign_agent."""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

# Ensure project root on path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from audit import log_event, sync_current  # noqa: E402
from config import HANDOFF_DIR, RESULTS_DIR, STATE_DIR, bind_host  # noqa: E402
from handoff.schema import validate_handoff  # noqa: E402
from handoff.verify import load_json, verify_result  # noqa: E402
from models.env_load import load_dotenv  # noqa: E402

# Windows consoles default to cp1252; argparse help contains non-ASCII (\u2192 etc.)
# which crashes --help. Force UTF-8 with replacement so help/errors never die on encode.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass  # non-reconfigurable stream (e.g. some test harnesses)

# Provider keys from project .env (never commit .env)
load_dotenv()


def cmd_run(goal: str, thread_id: str | None = None) -> int:
    from graph import default_graph  # lazy: only run needs LangGraph
    thread_id = thread_id or str(uuid.uuid4())
    app = default_graph()
    init = {
        "goal": goal,
        "messages": [],
        "tier": "T2",
        "plan": [],
        "step_i": 0,
        "tool_trace": [],
        "critique": "",
        "route": "plan",
        "handoff_id": None,
        "status": "running",
        "success_checks": [],
        "last_result": "",
        "retry_count": 0,
        "thread_id": thread_id,
    }
    config = {"configurable": {"thread_id": thread_id}}
    log_event({"event": "run_start", "thread_id": thread_id, "goal": goal[:300]})
    final = app.invoke(init, config=config)
    sync_current(final)
    print("---")
    print(f"status: {final.get('status')}")
    print(f"tier: {final.get('tier')} route: {final.get('route')}")
    print(f"thread_id: {thread_id}")
    if final.get("handoff_id"):
        print(f"handoff_id: {final.get('handoff_id')}")
        print(f"handoff: {HANDOFF_DIR / (final['handoff_id'] + '.json')}")
    print("last_result:")
    print((final.get("last_result") or "")[:3000])
    print("critique:")
    print((final.get("critique") or "")[:1500])
    print(f"\nSee state/CURRENT.md and logs/router.jsonl")
    # persist thread id for resume convenience
    (STATE_DIR / "last_thread.txt").write_text(thread_id, encoding="utf-8")
    return 0 if final.get("status") in {"done", "escalated", "waiting"} else 1


def cmd_status() -> int:
    p = STATE_DIR / "CURRENT.md"
    if p.is_file():
        print(p.read_text(encoding="utf-8"))
        return 0
    print("No CURRENT.md yet. Run a goal first.")
    return 1


def cmd_ingest_result(handoff_id: str) -> int:
    hpath = HANDOFF_DIR / f"{handoff_id}.json"
    rpath = RESULTS_DIR / f"{handoff_id}.json"
    if not hpath.is_file():
        print(f"missing handoff {hpath}")
        return 1
    handoff = json.loads(hpath.read_text(encoding="utf-8"))
    ok, errs = validate_handoff(handoff)
    if not ok:
        print("invalid handoff", errs)
        return 1
    result = load_json(rpath)
    if not result:
        print(f"missing result {rpath} — place Grok output there first")
        return 1
    passed, notes = verify_result(handoff, result)
    log_event({"event": "ingest_result", "handoff_id": handoff_id, "passed": passed, "notes": notes})
    print("verify:", passed, notes)
    if passed:
        summary = result.get("summary") or result.get("deliverable") or ""
        working = ROOT / "memory" / "working.md"
        prev = working.read_text(encoding="utf-8") if working.is_file() else ""
        working.write_text(
            prev + f"\n\n## Result {handoff_id}\n\n{summary}\n",
            encoding="utf-8",
        )
        print(f"merged into {working}")
    return 0 if passed else 1




def cmd_api(host: str, port: int) -> int:
    """Launch the FastAPI API gateway (Epoch 1, Pillar I)."""
    from mag.api_server import run as run_api  # lazy: only api needs FastAPI

    print(f"Mag API gateway -> http://{host}:{port}/  (X-API-Key required)")
    run_api(host=host, port=port)
    return 0

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local sovereign agent (LangGraph + Ollama)")
    sub = parser.add_subparsers(dest="cmd")

    p_run = sub.add_parser("run", help="Run a goal")
    p_run.add_argument("goal", nargs="+", help="Goal text")
    p_run.add_argument("--thread", default=None)

    p_plan = sub.add_parser("plan", help="Planning gate: clarify big/ambiguous goals")
    p_plan.add_argument("action", nargs="?", default="list",
                        choices=["list", "approve", "edit", "reject", "show"],
                        help="list | approve <id> | edit <id> | reject <id> | show <id>")
    p_plan.add_argument("plan_id", nargs="?", default=None, help="Plan id")
    p_plan.add_argument("--goal", default=None, help="Fire the gate on a goal (draft plan)")

    sub.add_parser("status", help="Show CURRENT.md")

    p_ing = sub.add_parser("ingest", help="Ingest Grok result for handoff id")
    p_ing.add_argument("handoff_id")

    p_watch = sub.add_parser(
        "watch", help="Watch live Grok session into memory/live_from_grok.md"
    )
    p_watch.add_argument("--once", action="store_true")
    p_watch.add_argument("--interval", type=float, default=3.0)

    p_dash = sub.add_parser(
        "dashboard",
        help="Browse history: sessions, PDFs, Verkle, ingest (http://127.0.0.1:8765)",
    )
    p_dash.add_argument("--host", default=bind_host())
    p_dash.add_argument("--port", type=int, default=8765)

    p_api = sub.add_parser(
        "api",
        help="FastAPI gateway on :8001 (X-API-Key required; :8000 is tool backend)",
    )
    p_api.add_argument("--host", default="127.0.0.1")
    p_api.add_argument("--port", type=int, default=8001)

    p_evo = sub.add_parser(
        "knot-evolution",
        help="Show living Verkle-knot topic evolution across session records",
    )

    p_sum = sub.add_parser(
        "summarize-session",
        help="FILE a seat chat into residual DNA + Verkle leaf (Grok or Mag agent)",
    )
    p_sum.add_argument(
        "--session",
        default="",
        help="Session id (Grok UUID, mag-agent-<seat>, or agent seat name; default: active Grok)",
    )
    p_sum.add_argument(
        "--source",
        default="auto",
        choices=["auto", "grok", "mag_agent", "agent"],
        help="Chat source (default auto — resolve Grok or Mag agent)",
    )
    p_sum.add_argument("--force", action="store_true", help="Re-summarize even if done")
    p_sum.add_argument("--no-llm", action="store_true", help="Heuristic only, no Ollama")
    p_sum.add_argument(
        "--pdf",
        action="store_true",
        help="Also render PDF (export layer; off by default)",
    )
    p_sum.add_argument(
        "--visual",
        action="store_true",
        help="Also write visual pack (export layer; off by default)",
    )
    p_sum.add_argument(
        "--all-agents",
        action="store_true",
        help="FILE every Mag agent seat under memory/agent_sessions/",
    )
    p_sum.add_argument(
        "--no-pdf",
        action="store_true",
        help="Deprecated: PDF already off by default",
    )

    p_mag = sub.add_parser(
        "mag",
        help="Sovereign Mag background companion (sense→judge→act; Grok harness escalate)",
    )
    p_mag.add_argument("--once", action="store_true", help="Single cycle then exit")
    p_mag.add_argument(
        "--interval",
        type=float,
        default=None,
        help="Seconds between cycles (default from configs/mag.yaml)",
    )
    p_mag.add_argument(
        "--no-harness",
        action="store_true",
        help="Force file handoffs only (skip grok -p)",
    )

    p_brief = sub.add_parser(
        "brief",
        help="Local brief from dossier (L0) — memory/briefs/<session>.md",
    )
    p_brief.add_argument("--session", default="latest")
    p_brief.add_argument("--no-llm", action="store_true")

    p_ask = sub.add_parser(
        "ask",
        help="Ask Mag biographer from local memory (no Grok)",
    )
    p_ask.add_argument("question", nargs="+", help="Question text")
    p_ask.add_argument("--session", default="", help="Optional session id")
    p_ask.add_argument("--no-llm", action="store_true")
    p_ask.add_argument("--no-speak", action="store_true", help="Disable default TTS for this answer")

    p_tts = sub.add_parser("tts", help="Speak text out loud (default TTS)")
    p_tts.add_argument("text", nargs="+", help="Text to speak")

    p_ws = sub.add_parser(
        "workshop",
        help="Socratic prompt workshop: refine a prompt before launching a coding session",
    )
    p_ws.add_argument("prompt", nargs="+", help="Rough prompt to refine")
    p_ws.add_argument("--rounds", type=int, default=3, help="Socratic rounds")
    p_ws.add_argument("--no-speak", action="store_true", help="Don't speak the refined prompt")

    p_vis = sub.add_parser(
        "visual",
        help="Build/amend Mag visual pack (chambers) for a session",
    )
    p_vis.add_argument("--session", default="latest")

    sub.add_parser("doctor", help="Sanity map: integral / live board / lanes (anti-hallucination)")
    p_nerv = sub.add_parser(
        "nervous",
        help="Nervous system: at-a-glance body + Verkle tips + key presence (agent ops)",
    )
    p_nerv.add_argument("--json", action="store_true", help="Full nervous_system.v1 JSON")
    p_nerv.add_argument(
        "--quiet",
        action="store_true",
        help="Write face files only; exit code = body_ok",
    )
    sub.add_parser(
        "lattice",
        help="Verkle lattice history + plan summary (JSON for desk / Grok)",
    )
    p_fs = sub.add_parser(
        "field-steal",
        help="Ingest field sysprompt archive → contract steal ledger (not DNA)",
    )
    p_fs.add_argument(
        "--root",
        type=str,
        default="",
        help="Path to field clone (default: ../field-strike-the-chord)",
    )
    p_fs.add_argument("--max-files", type=int, default=0, help="Cap files scanned (0=all)")
    p_fs.add_argument("--json", action="store_true", help="Print result JSON only")
    p_cu = sub.add_parser("catch-up", help="After reconnect: watch + amend + visual")
    p_probe = sub.add_parser("probe-lanes", help="Real L0/L1/L2 probes (not vibes)")
    p_probe.add_argument("--no-l1", action="store_true", help="Skip OpenRouter chat")
    p_guard = sub.add_parser("guard", help="Failsafe loop: detect down Mag, optional --restart")
    p_guard.add_argument("--once", action="store_true")
    p_guard.add_argument("--interval", type=float, default=30.0)
    p_guard.add_argument("--restart", action="store_true", help="Spawn lab if down")
    p_boot = sub.add_parser(
        "boot",
        help="Sancho boot: self-analysis + optional ensure lab (SessionStart)",
    )
    p_boot.add_argument(
        "--ensure",
        action="store_true",
        help="Spawn lab if integral down / live stale",
    )
    p_boot.add_argument(
        "--light",
        action="store_true",
        help="Skip quota snapshot (faster hook path)",
    )
    p_boot.add_argument("--json", action="store_true", help="Print full JSON report")
    p_pack = sub.add_parser(
        "pack-status",
        help="Records office: pack completeness for one session or all",
    )
    p_pack.add_argument(
        "session",
        nargs="?",
        default="all",
        help="Session id, or 'all' (default)",
    )
    p_pack.add_argument("--json", action="store_true", help="Full JSON")
    p_bf = sub.add_parser(
        "backfill-sessions",
        help="Records office: force-complete incomplete session packs",
    )
    p_bf.add_argument(
        "--llm",
        action="store_true",
        help="Use Ollama polish (default: heuristic only)",
    )
    p_bf.add_argument(
        "--dry-run",
        action="store_true",
        help="List holes only; do not write",
    )
    p_bf.add_argument(
        "--all",
        action="store_true",
        help="Re-file every known session, not only incomplete",
    )
    sub.add_parser(
        "refresh-session-cards",
        help="Rebuild human blurb+bullets on all dossiers (no full re-summarize)",
    )
    sub.add_parser(
        "migrate-lean-registry",
        help="Migrate dossiers → residual/ + rebuild registry.jsonl (lean model)",
    )
    p_org = sub.add_parser(
        "org-review",
        help="Local forest walk: DNA + what was I doing + next ticket (no Grok)",
    )
    p_org.add_argument("--json", action="store_true", help="Full operator-os JSON")
    sub.add_parser(
        "tapestry",
        help="Build 3D tapestry pack from residual (sample VK-class lattice)",
    )
    sub.add_parser("models", help="Role → Ollama model map + present/missing")
    sub.add_parser(
        "multi-smoke",
        help="M0 dual-local proof: clerk+worker+critic on public fixture",
    )
    p_governor = sub.add_parser(
        "governor",
        help="Autorun decision framework (the product): decide/execute/verify/record",
    )
    p_governor.add_argument("--run", type=int, default=1, help="cycles to autorun")
    p_governor.add_argument("--dry", type=int, default=0, help="decide + report only")
    p_auto = sub.add_parser(
        "autopilot",
        help="Brain+loop pass: improve queue + governor + seed-mirror status",
    )
    p_auto.add_argument("--no-queue", action="store_true", help="skip improve->orchestrator enqueue")
    p_auto.add_argument("--no-governor", action="store_true", help="skip governor cycle")
    p_auto.add_argument("--drain", action="store_true", help="drain once after queue")
    p_auto.add_argument("--max-queue", type=int, default=2, help="max improve tickets to queue")
    p_autorun = sub.add_parser(
        "autorun",
        help="Intelligent autorun: fill queue, route, drain DeepSeek jobs (drainer loop)",
    )
    p_autorun.add_argument("--once", action="store_true", help="single tick then exit")
    p_autorun.add_argument("--dry", action="store_true", help="plan only, no execute")
    p_autorun.add_argument("--no-fill", action="store_true", help="skip queue fill")
    p_autorun.add_argument("--fill-only", action="store_true", help="fill + plan only")
    p_autorun.add_argument("--interval", type=float, default=5.0, help="loop interval seconds")
    p_sg = sub.add_parser(
        "seat-guard",
        help="Supervise the seat REPL: relaunch on crash/glitch/stall/hard-stop",
    )
    p_sg.add_argument("sg_args", nargs=argparse.REMAINDER,
                      help="forwarded to mag/seat_guard.py (run/status/stop/trail)")
    p_cp = sub.add_parser(
        "context-pack",
        help="Min-token pack for Grok TUI (bonds+brief+loops — not full chat)",
    )
    p_cp.add_argument(
        "--refresh-bonds",
        action="store_true",
        help="Re-ingest residual bonds before packing",
    )
    p_cp.add_argument(
        "--agent",
        action="store_true",
        help="Blind-men agent preamble (coarse elephant for subagents/workflows)",
    )
    p_cp.add_argument(
        "--goal",
        default="",
        help="Optional goal line embedded in --agent preamble",
    )
    p_bonds = sub.add_parser(
        "bonds",
        help="Ingest residual bonds → memory/bonds_active.md (next-session inputs)",
    )
    p_bonds.add_argument(
        "--session",
        default="",
        help="Session id (default: latest brief)",
    )
    p_bonds.add_argument(
        "--print",
        action="store_true",
        dest="print_bonds",
        help="Print bonds markdown after ingest",
    )

    p_bonds.add_argument(
        "--scan",
        default="",
        help="Conflict-scan a candidate bond text against existing residual bonds (no write)",
    )

    p_diary = sub.add_parser(
        "diary",
        help="Day-by-day story spine from filed beads (how we got here)",
    )
    p_diary.add_argument("--newest", action="store_true", help="Newest first")
    p_diary.add_argument("--write", action="store_true", help="Write memory/diary_latest.md")
    p_diary.add_argument("--json", action="store_true", help="JSON output")

    p_ideas = sub.add_parser(
        "ideas",
        help="Idea graph v0 — topic nodes/edges on disk (list|add|link|pack|seed|show)",
    )
    p_ideas.add_argument(
        "action",
        nargs="?",
        default="list",
        choices=["list", "add", "link", "pack", "seed", "show", "summary"],
        help="list|add|link|pack|seed|show|summary",
    )
    p_ideas.add_argument("ids", nargs="*", help="node id(s); link uses SRC DST")
    p_ideas.add_argument("--type", default="", dest="idea_type", help="node or edge type")
    p_ideas.add_argument("--status", default="", help="filter status (list) or set status (add)")
    p_ideas.add_argument("--title", default="", help="title for add")
    p_ideas.add_argument("--body", default="", help="body for add")
    p_ideas.add_argument("--note", default="", help="note for link")
    p_ideas.add_argument("--ref", default="", help="ref path for link")
    p_ideas.add_argument("--limit", type=int, default=40, help="list limit")
    p_ideas.add_argument("--json", action="store_true", help="JSON output")
    p_as = sub.add_parser(
        "agent-state",
        help="Versioned Grok/Mag agent state (Verkle chain) — LOAD before redesign",
    )
    p_as.add_argument(
        "--load",
        action="store_true",
        help="Print LATEST.md (full recall pack)",
    )
    p_as.add_argument(
        "--list",
        action="store_true",
        dest="list_versions",
        help="List version chain rows",
    )
    p_as.add_argument(
        "--show",
        default="",
        help="Show version by content_commit prefix (8+ hex)",
    )
    p_as.add_argument(
        "--commit",
        default="",
        help="Commit reason/label (writes new version; use with --from-file or default snapshot)",
    )
    p_as.add_argument(
        "--from-file",
        default="",
        help="JSON payload path for --commit (optional)",
    )
    p_as.add_argument(
        "--link-residual",
        action="store_true",
        help="Write edges.agent_state onto latest residual (no core strip)",
    )
    p_as.add_argument("--session", default="", help="Session id for --link-residual")
    p_as.add_argument("--json", action="store_true", help="JSON output where applicable")
    p_compose = sub.add_parser(
        "compose-status",
        help="Module registry + compose/runtime health (modular upgrade face)",
    )
    p_compose.add_argument("--json", action="store_true", help="Raw JSON")
    p_compose.add_argument(
        "--attach-runs",
        action="store_true",
        help="Retrocausal: write related_runs onto residual edges (no core strip)",
    )
    p_compose.add_argument("--session", default="", help="Session id for --attach-runs")
    p_trail = sub.add_parser(
        "trail",
        help="Run object + live trail (seat purity, cores, pack excerpt)",
    )
    p_trail.add_argument(
        "action",
        choices=[
            "start",
            "append",
            "status",
            "close",
            "check-seat",
            "cores",
            "pack",
            "base",
            "drifts",
        ],
        help="start|append|status|close|check-seat|cores|pack|base|drifts",
    )
    p_trail.add_argument("text", nargs="*", help="Goal (start) or summary (append)")
    p_trail.add_argument(
        "--seat",
        default="local",
        help="Seat lock on start / purity check (local|remote|grok_tui|hermes|human)",
    )
    p_trail.add_argument(
        "--proactivity",
        default="narrow",
        choices=["narrow", "normal", "wide"],
        help="Proactivity dial (start)",
    )
    p_trail.add_argument("--run", default="", help="run_id (default: active)")
    p_trail.add_argument("--kind", default="note", help="Event kind for append")
    p_trail.add_argument(
        "--core",
        default="",
        help='JSON core for append (PowerShell-hostile); prefer --core-text',
    )
    p_trail.add_argument(
        "--core-text",
        default="",
        help="Plain core text for append → {type: kind or decision, text: …}",
    )
    p_trail.add_argument(
        "--label",
        default="",
        help="append: agent probe label → file_agent_core (kind agent_probe)",
    )
    p_trail.add_argument(
        "--locus",
        default="",
        help="append --label: graph locus for drift (default: label)",
    )
    p_trail.add_argument(
        "--drift-kind",
        default="note",
        dest="drift_kind",
        help="append --label: add|contradict|open_loop|gap|severity|note|finding|ready",
    )
    p_trail.add_argument(
        "--evidence",
        default="",
        help="append --label: short evidence string (file:line / tool)",
    )
    p_trail.add_argument(
        "--base-id",
        default="",
        dest="base_id",
        help="append --label: must match run base or FILE rejected",
    )
    p_trail.add_argument(
        "--git-sha",
        default="",
        dest="git_sha",
        help="start: pin code base SHA into frozen run base (default: git HEAD)",
    )
    p_trail.add_argument(
        "--force",
        action="store_true",
        help="start: close prior open run first",
    )
    p_trail.add_argument("--reason", default="done", help="close reason")
    p_trail.add_argument(
        "--never-remote",
        action="store_true",
        help="start: privacy.never_remote (tier_max T1)",
    )
    sub.add_parser(
        "providers",
        help="List platforms (OpenAI/Gemini/DeepSeek/…) + keys + quota remaining",
    )
    sub.add_parser("quota", help="Usage used/remaining until reset per platform")
    p_pc = sub.add_parser(
        "provider-chat",
        help="Chat via a platform (or --job to auto-pick by budget)",
    )
    p_pc.add_argument("prompt", nargs="+", help="User prompt (public T2 only for remotes)")
    p_pc.add_argument("--provider", default="", help="ollama|openrouter|openai|anthropic|groq|deepseek|gemini|xai|together")
    p_pc.add_argument("--job", default="public_summarize", help="Routing job class if no --provider")
    p_pc.add_argument("--model", default="", help="Override model id")
    p_pc.add_argument("--tier", default="T2", help="T0|T1 blocked on remote")
    p_disp = sub.add_parser(
        "dispatch",
        help="Sovereign hop: local context-pack → auto seat/provider → min tokens",
    )
    p_disp.add_argument("goal", nargs="+", help="What to do")
    p_disp.add_argument("--dry", action="store_true", help="Classify only, no model call")
    p_disp.add_argument("--provider", default="", help="Force provider id")
    p_disp.add_argument(
        "--seat",
        default="",
        help="Force seat: local|remote|grok_tui|hermes",
    )
    p_coord = sub.add_parser(
        "coordinate",
        help="Classify depth + route to Grok plan / DeepSeek heavy / local simple (shared activity)",
    )
    p_coord.add_argument("goal", nargs="+", help="What to do")
    p_coord.add_argument(
        "--depth",
        default="",
        choices=("overview", "plan", "heavy_code", "simple_code", "scut", ""),
        help="Force depth (else auto-classify)",
    )
    p_coord.add_argument("--seat", default="cli", help="Calling seat id")
    p_coord.add_argument("--dry", action="store_true", help="Classify only — do not launch")
    p_coord.add_argument(
        "--background",
        action="store_true",
        help="Queue heavy_code on orchestrator instead of inline delegate",
    )
    p_coord.add_argument("--session", default="", help="Agent session id for delegate mode")
    p_route = sub.add_parser(
        "route",
        help="Unified routing decision (seat, provider, mode) — honest failures",
    )
    p_route.add_argument("goal", nargs="+", help="What to route")
    p_route.add_argument(
        "--depth",
        default="",
        choices=("overview", "plan", "heavy_code", "simple_code", "scut", ""),
        help="Force depth (else auto-classify)",
    )
    p_route.add_argument(
        "--local",
        action="store_true",
        help="If lane=local, execute ask/doctor/smoke now (legacy local runner)",
    )
    p_decide = sub.add_parser(
        "decide",
        help="Framework decision: route + behavioral tips + interference status",
    )
    p_decide.add_argument("goal", nargs="+", help="What to decide")
    p_decide.add_argument(
        "--depth",
        default="",
        choices=("overview", "plan", "heavy_code", "simple_code", "scut", ""),
        help="Force depth",
    )
    p_fkb = sub.add_parser(
        "fkb",
        help="Failure Knowledge Base: search recurring failures / stats",
    )
    p_fkb.add_argument(
        "fkb_args",
        nargs="*",
        help="stats | list [n] | search <query> | record <kind> <tool> <detail>",
    )
    p_agent = sub.add_parser(
        "agent",
        help="Tool-using CLI (DeepSeek/Ollama + Mag tools). Use when Grok tokens are empty.",
    )
    p_agent.add_argument(
        "-q",
        "--query",
        default="",
        help="One-shot goal then exit (else interactive REPL)",
    )
    p_agent.add_argument(
        "--provider",
        default="deepseek",
        help="Brain: deepseek (default) | ollama | openrouter | …",
    )
    p_agent.add_argument("--model", default="", help="Override model id")
    p_orc = sub.add_parser(
        "orchestrator",
        help="Supervise isolated sub-agent tasks (spawn/kill/reap) - one window, short-lived workers",
    )
    p_orc.add_argument(
        "orc_args",
        nargs=argparse.REMAINDER,
        help="subcommand + args, passed to mag.orchestrator.main (run <goal> | list | status <id> | kill <id> | reap | self-test)",
    )

    p_gp = sub.add_parser(
        "gpipes",
        help="Governor pipes: parallel fan-out of sub-agents + merged collection (manifesto Phase 3)",
    )
    p_gp.add_argument(
        "gp_args",
        nargs=argparse.REMAINDER,
        help="subcommand + args, passed to mag.gpipes.main (fan <goals...> | collect <id> | status <id> | kill <id> | list)",
    )

    p_tan = sub.add_parser(
        "tangent",
        help="Queue/run background scout (Gemini/janitor); results in memory/tangents/",
    )
    p_tan.add_argument("prompt", nargs="*", help="Tangent ask (or --list / --process)")
    p_tan.add_argument("--list", action="store_true", help="List recent tangents")
    p_tan.add_argument("--process", action="store_true", help="Process queue (and optional --scan)")
    p_tan.add_argument("--scan", action="store_true", help="Scan live_from_grok for markers")
    p_tan.add_argument("--provider", default="", help="Force provider (e.g. gemini)")
    p_tan.add_argument("--no-run", action="store_true", help="Queue only, do not run yet")
    sub.add_parser(
        "hermes-status",
        help="Whether Nous Hermes Agent CLI is on PATH / HERMES_BIN",
    )
    p_imp = sub.add_parser(
        "improve",
        help="Daily improve loop: scout field → candidates → eval (gated promote)",
    )
    p_imp.add_argument(
        "--once",
        action="store_true",
        help="Scout + eval once (default if no mode flags)",
    )
    p_imp.add_argument("--scout", action="store_true", help="Outbound scout only")
    p_imp.add_argument("--eval", action="store_true", help="Run eval battery only")
    p_imp.add_argument(
        "--synthesize",
        action="store_true",
        help="Rank candidates → field_brief.md only (no scout)",
    )
    p_imp.add_argument("--status", action="store_true", help="Show candidate ledger summary")
    p_imp.add_argument(
        "--dry",
        action="store_true",
        help="Plan source keys + URLs without fetching",
    )
    p_imp.add_argument(
        "--deep",
        action="store_true",
        help="Opt-in deep dig: research-pack + local Ollama on ranked field tickets",
    )
    p_imp.add_argument(
        "--minutes",
        type=int,
        default=None,
        help="With --deep: wall-clock budget minutes (default 60 from improve.yaml)",
    )
    p_imp.add_argument(
        "--max-tickets",
        type=int,
        default=None,
        help="With --deep: max ranked tickets to dig (default 4)",
    )

    p_lat = sub.add_parser(
        "lattice-loop",
        help="Conspiracy test lattice dig loop (Ollama self-directed research)",
    )
    p_lat.add_argument("--status", action="store_true", help="Lattice + dig state")
    p_lat.add_argument("--run", action="store_true", help="Start loop")
    p_lat.add_argument("--bg", action="store_true", help="With --run: background thread")
    p_lat.add_argument("--stop", action="store_true", help="Stop lattice loop")
    p_lat.add_argument(
        "--cycle-seconds",
        type=int,
        default=90,
        help="Seconds between dig units (default 90)",
    )
    p_lat.add_argument(
        "--max-cycles",
        type=int,
        default=0,
        help="0 = unlimited until --stop",
    )

    p_csync = sub.add_parser(
        "canvas-sync",
        help="Sync Cursor Canvas *.tsx → memory/viewports/ manifests",
    )
    p_csync.add_argument(
        "--dry-run",
        action="store_true",
        help="Report counts only; do not write files",
    )

    sub.add_parser(
        "canvas-list",
        help="List synced canvas viewport manifests",
    )

    p_lq = sub.add_parser(
        "lattice-query",
        help="Query memory/lattice store (nodes/edges from lattice-backfill)",
    )
    p_lq.add_argument("--summary", action="store_true", help="Node/edge counts + themes")
    p_lq.add_argument("--theme", default="", help="Filter nodes by dominant theme")
    p_lq.add_argument("--neighbors", default="", help="Edges adjacent to node id")

    p_lbf = sub.add_parser(
        "lattice-backfill",
        help="Rebuild instrument verkle chain + seed memory/lattice store",
    )
    p_lbf.add_argument("--dry-run", action="store_true", help="Report counts only")

    p_va = sub.add_parser(
        "verkle-audit",
        help="Verkle chain audit, ticket reconcile, optional local synth",
    )
    p_va.add_argument("--full", action="store_true", help="Backfill lattice + synth + reconcile")
    p_va.add_argument("--synth", action="store_true", help="Local clerk pass per residual session")
    p_va.add_argument("--backfill", action="store_true", help="Run lattice-backfill first")
    p_va.add_argument("--dry", action="store_true", help="Plan only; no writes or LLM")
    p_va.add_argument("--no-reconcile", action="store_true", help="Skip ticket reconciliation")

    p_blast = sub.add_parser(
        "blast",
        help="Full-blast self-improve plant with influence dials (dash + CLI)",
    )
    p_blast.add_argument("--status", action="store_true", help="Show plant + ollama + influence")
    p_blast.add_argument("--run", action="store_true", help="Start blast (foreground unless --bg)")
    p_blast.add_argument("--bg", action="store_true", help="With --run: background thread")
    p_blast.add_argument("--stop", action="store_true", help="Stop blast plant")
    p_blast.add_argument("--pause", action="store_true", help="Pause digs (keep plant alive)")
    p_blast.add_argument("--resume", action="store_true", help="Resume after pause")
    p_blast.add_argument("--focus", default="", help="Set operator focus text (steers digs)")
    p_blast.add_argument("--minutes", type=int, default=None, help="dig_minutes dial")
    p_blast.add_argument("--max-tickets", type=int, default=None, help="max_tickets dial")
    p_blast.add_argument("--cycle-seconds", type=int, default=None, help="seconds between dig cycles")

    p_promo = sub.add_parser(
        "promote",
        help="Human gate: apply or reject an improve candidate id",
    )
    p_promo.add_argument("candidate_id", help="Candidate id (c-…)")
    p_promo.add_argument(
        "--apply",
        action="store_true",
        help="Mark promoted (practices → playbook; models do not auto-edit lanes)",
    )
    p_promo.add_argument("--reject", action="store_true", help="Mark rejected")
    p_promo.add_argument("--reason", default="", help="Reject/promote note")
    p_promo.add_argument(
        "--force-model",
        action="store_true",
        help="With --apply: allow model promote path (still no auto lanes write in v1)",
    )

    p_rp = sub.add_parser(
        "research-pack",
        help="Scrape URLs → clean ask PDF/JSON for lesser models (local-first routing)",
    )
    p_rp.add_argument("--ask", required=True, help="The ask / research question")
    p_rp.add_argument("--url", action="append", default=[], help="Source URL (repeatable)")
    p_rp.add_argument("--title", default="", help="Short title")
    p_rp.add_argument(
        "--criterion",
        action="append",
        default=[],
        help="Success criterion for lesser models (repeatable)",
    )
    p_rp.add_argument(
        "--run",
        action="store_true",
        help="After build, run local worker on the pack",
    )
    p_rp.add_argument(
        "--elevate",
        action="store_true",
        help="After build, emit Grok-elevation payload (pack only)",
    )
    p_rp.add_argument("--provider", default="", help="With --run: force remote provider")

    p_lab = sub.add_parser(
        "lab",
        help="Integral Mag: one process = watch + companion + dashboard (default)",
    )
    p_lab.add_argument("--host", default=bind_host())
    p_lab.add_argument("--port", type=int, default=8765)
    p_lab.add_argument(
        "--ui-only",
        action="store_true",
        help="Dashboard only (no watch/mag) — not recommended day-to-day",
    )
    p_lab.add_argument(
        "--no-dashboard",
        action="store_true",
        help="Mag+watch only, no HTTP UI",
    )
    p_lab.add_argument(
        "--with-instrument",
        action="store_true",
        help="Print strike desk hint only (optional analysis, not Mag home)",
    )

    # bare: python main.py "goal..."
    args, rest = parser.parse_known_args(argv)
    if args.cmd is None:
        if rest:
            return cmd_run(" ".join(rest))
        if argv and not any(a.startswith("-") for a in (argv or [])):
            return cmd_run(" ".join(argv))
        parser.print_help()
        return 2

    if args.cmd == "run":
        return cmd_run(" ".join(args.goal), thread_id=args.thread)
    if args.cmd == "plan":
        from mag.plan import plan_gate, list_plans, load_plan, set_status

        if args.action == "list":
            for pl in list_plans():
                print(f"{pl['plan_id']}  [{pl['status']}]  {pl['goal'][:70]}")
            return 0
        if args.action == "show":
            pl = load_plan(args.plan_id) if args.plan_id else None
            if not pl:
                print("no such plan")
                return 1
            print(__import__("json").dumps(pl, indent=2, ensure_ascii=False))
            return 0
        if args.action in ("approve", "reject"):
            if not args.plan_id:
                print("need plan_id")
                return 1
            pl = set_status(args.plan_id, "approved" if args.action == "approve" else "rejected")
            if not pl:
                print("no such plan")
                return 1
            print(f"{args.plan_id} -> {pl['status']}")
            return 0
        if args.action == "edit":
            if not args.plan_id:
                print("need plan_id")
                return 1
            pl = load_plan(args.plan_id)
            if not pl:
                print("no such plan")
                return 1
            print("Edit fields in the JSON file, then re-run `plan approve <id>`.")
            print(__import__("json").dumps(pl, indent=2, ensure_ascii=False))
            return 0
        # default: fire gate on a goal
        if args.goal:
            res = plan_gate(args.goal)
            print(__import__("json").dumps(res, indent=2, ensure_ascii=False)[:4000])
            return 0
        print("usage: plan list | plan approve <id> | plan reject <id> | plan --goal '<goal>'")
        return 2
    if args.cmd == "status":
        return cmd_status()
    if args.cmd == "ingest":
        return cmd_ingest_result(args.handoff_id)
    if args.cmd == "watch":
        from watch.tail_session import loop, once

        if args.once:
            return once()
        loop(args.interval)
        return 0
    if args.cmd == "summarize-session":
        from mag.biography import summarize_session
        from watch.tail_session import resolve_session

        if getattr(args, "all_agents", False):
            from mag.chat_source import file_dirty_agent_sessions

            res = file_dirty_agent_sessions(
                use_llm=not args.no_llm,
                force=bool(args.force),
            )
            print(json.dumps(res, indent=2))
            return 0 if res.get("ok") else 1

        sid = args.session.strip()
        src = (getattr(args, "source", None) or "auto").strip()
        if src == "agent":
            src = "mag_agent"
        if not sid:
            if src == "mag_agent":
                sid = "dashboard"
            else:
                resolved = resolve_session()
                if not resolved:
                    print("no active session; pass --session <id> or --source mag_agent")
                    return 1
                sid = resolved[0]
        # Bare agent seat name + auto → prefer agent FILE helper
        if src in ("mag_agent", "auto") and not sid.startswith("019") and "mag-agent" not in sid:
            from mag.chat_source import agent_session_path, file_agent_session

            if agent_session_path(sid).is_file() or src == "mag_agent":
                res = file_agent_session(
                    sid,
                    use_llm=not args.no_llm,
                    force=bool(args.force),
                    pdf=bool(getattr(args, "pdf", False)),
                    visual=bool(getattr(args, "visual", False)),
                )
                print(json.dumps(res, indent=2))
                return 0 if res.get("ok") else 1
        res = summarize_session(
            sid,
            source=src,
            use_llm=not args.no_llm,
            force=args.force,
            pdf=bool(getattr(args, "pdf", False)),
            visual=bool(getattr(args, "visual", False)),
        )
        print(json.dumps(res, indent=2))
        return 0 if res.get("ok") else 1
    if args.cmd == "knot-evolution":
        from mag.verkle_knot import evolution_summary

        print(json.dumps(evolution_summary(), indent=2))
        return 0
    if args.cmd == "dashboard":
        from dashboard.server import run as run_dashboard

        run_dashboard(host=args.host, port=args.port)

    if args.cmd == "api":
        return cmd_api(host=args.host, port=args.port)
        return 0
    if args.cmd == "mag":
        if args.no_harness:
            # patch policy file flag in-process via env
            import os

            os.environ["MAG_NO_HARNESS"] = "1"
        from mag.daemon import run_loop
        from mag.policy import load_policy

        pol = load_policy()
        if args.no_harness or __import__("os").environ.get("MAG_NO_HARNESS"):
            pol["use_grok_harness"] = False
            # monkey-affect: rewrite sense to see env
            import mag.act as act_mod

            _orig = act_mod.load_policy

            def _pol():
                p = _orig()
                p["use_grok_harness"] = False
                return p

            act_mod.load_policy = _pol  # type: ignore
        run_loop(interval=args.interval, once=args.once)
        return 0
    if args.cmd == "brief":
        from mag.brief_local import write_brief

        res = write_brief(
            None if args.session in ("", "latest") else args.session,
            use_llm=not args.no_llm,
        )
        print(json.dumps(res, indent=2))
        return 0 if res.get("ok") else 1
    if args.cmd == "ask":
        from mag.ask import ask as mag_ask

        q = " ".join(args.question)
        res = mag_ask(
            q,
            session_id=args.session.strip() or None,
            use_llm=not args.no_llm,
            speak=not args.no_speak,
        )
        if res.get("answer"):
            print(res["answer"])
        else:
            print(json.dumps(res, indent=2))
        return 0 if res.get("ok") else 1
    if args.cmd == "tts":
        from mag.tts import speak

        text = " ".join(args.text)
        ok = speak(text, force=True)
        print(f"tts ok={ok}")
        return 0 if ok else 1
    if args.cmd == "workshop":
        from mag.socratic import workshop

        res = workshop(" ".join(args.prompt), rounds=args.rounds, speak_result=not args.no_speak)
        if not res.get("ok"):
            print(json.dumps(res, indent=2))
            return 1
        print("=== FINAL PROMPT ===")
        print(res["final"])
        return 0
    if args.cmd == "visual":
        from mag.visual_pack import write_visual_pack

        res = write_visual_pack(
            None if args.session in ("", "latest") else args.session
        )
        print(json.dumps(res, indent=2))
        return 0 if res.get("ok") else 1
    if args.cmd == "doctor":
        from mag.health import sanity
        from mag.guard import doctor_print

        s = sanity()
        doctor_print(s)
        print(json.dumps(s, indent=2, default=str)[:4000])
        return 0 if s.get("status") == "up" else 1
    if args.cmd == "catch-up":
        from mag.health import catch_up

        res = catch_up()
        print(json.dumps(res, indent=2, default=str))
        return 0 if res.get("ok") else 1
    if args.cmd == "probe-lanes":
        from models.probe import probe_all

        res = probe_all(include_l1_chat=not args.no_l1)
        print(json.dumps(res, indent=2, default=str))
        return 0 if res.get("ok") else 1
    if args.cmd == "guard":
        from mag.guard import guard_loop

        guard_loop(interval=args.interval, once=args.once, restart=args.restart)
        return 0
    if args.cmd == "boot":
        from mag.boot import run_boot

        report = run_boot(ensure=args.ensure, light=args.light)
        if args.json:
            print(json.dumps(report, indent=2, default=str)[:8000])
        else:
            print(report.get("text") or json.dumps(report, indent=2, default=str)[:2000])
        return 0 if report.get("ok") else 1
    if args.cmd == "pack-status":
        from mag.records import format_pack_report_text, pack_report, write_kpi

        rep = pack_report(None if args.session in ("all", "*", "") else args.session)
        write_kpi(source="pack-status")
        if args.json:
            print(json.dumps(rep, indent=2, default=str)[:12000])
        else:
            print(format_pack_report_text(rep))
        # exit 1 if holes (records office red)
        if not rep.get("ok"):
            return 1
        if rep.get("mode") == "all" and (rep.get("n_incomplete") or 0) > 0:
            return 1
        if rep.get("mode") == "one" and not rep.get("complete"):
            return 1
        return 0
    if args.cmd == "backfill-sessions":
        from mag.records import backfill_sessions

        res = backfill_sessions(
            use_llm=args.llm,
            dry_run=args.dry_run,
            only_incomplete=not args.all,
        )
        print(json.dumps(res, indent=2, default=str)[:12000])
        return 0 if res.get("ok") else 1
    if args.cmd == "refresh-session-cards":
        from mag.session_card import recompute_all_cards

        res = recompute_all_cards()
        # short human preview
        for c in (res.get("cards") or [])[:12]:
            print(f"\n## {c.get('title') or c.get('session_id')}")
            print(c.get("blurb") or "")
            for b in c.get("bullets") or []:
                print(f"  - {b}")
        print(f"\n# refreshed {res.get('n')} cards")
        return 0 if res.get("ok") else 1
    if args.cmd == "migrate-lean-registry":
        from mag.registry import migrate_all_to_lean
        from mag.records import write_kpi

        res = migrate_all_to_lean()
        kpi = write_kpi(source="migrate-lean")
        print(json.dumps({**res, "kpi": kpi}, indent=2, default=str)[:8000])
        return 0 if res.get("ok") else 1
    if args.cmd == "org-review":
        from mag.operator_os import build_operator_os, format_org_review_text

        pack = build_operator_os(refresh_pack=True)
        if args.json:
            print(json.dumps(pack, indent=2, default=str)[:12000])
        else:
            print(format_org_review_text(pack))
        return 0 if pack.get("ok") else 1
    if args.cmd == "tapestry":
        from mag.tapestry import write_tapestry_pack

        pack = write_tapestry_pack()
        st = pack.get("stats") or {}
        print(
            f"tapestry → {pack.get('path')}\n"
            f"days={st.get('n_days')} nodes={st.get('n_nodes')} edges={st.get('n_edges')}\n"
            f"transforms: {(pack.get('transforms') or {})}"
        )
        return 0
    if args.cmd == "models":
        from models.registry import inventory

        inv = inventory()
        print(json.dumps(inv, indent=2))
        return 0 if inv.get("ok") else 1
    if args.cmd == "multi-smoke":
        from models.multi_smoke import run_multi_smoke

        res = run_multi_smoke()
        print(json.dumps(res, indent=2, default=str))
        print("\n" + res.get("verdict", ""))
        return 0 if res.get("ok") else 1
    if args.cmd == "nervous":
        from mag.nervous_system import build_glance, format_glance_text

        glance = build_glance(write=True)
        if getattr(args, "json", False):
            print(json.dumps(glance, indent=2, default=str))
        elif getattr(args, "quiet", False):
            pass
        else:
            face = ROOT / "memory" / "nervous_system.md"
            if face.is_file():
                print(face.read_text(encoding="utf-8"))
            else:
                print(format_glance_text(glance))
        return 0 if glance.get("ok") else 1
    if args.cmd == "lattice":
        from mag.lattice_dashboard import build_lattice_summary

        print(json.dumps(build_lattice_summary(), indent=2, default=str))
        return 0
    if args.cmd == "canvas-sync":
        from mag.canvas_bridge import sync_canvases

        print(json.dumps(sync_canvases(dry_run=bool(args.dry_run)), indent=2, default=str))
        return 0
    if args.cmd == "canvas-list":
        from mag.canvas_bridge import list_viewports

        print(json.dumps(list_viewports(), indent=2, default=str))
        return 0
    if args.cmd == "lattice-query":
        from mag.lattice_query import neighbors, query_by_theme, summary

        if getattr(args, "neighbors", ""):
            print(json.dumps(neighbors(args.neighbors), indent=2, default=str))
            return 0
        if getattr(args, "theme", ""):
            print(json.dumps(query_by_theme(args.theme), indent=2, default=str))
            return 0
        print(json.dumps(summary(), indent=2, default=str))
        return 0
    if args.cmd == "lattice-backfill":
        from mag.lattice_backfill import run_backfill

        res = run_backfill(dry_run=bool(getattr(args, "dry_run", False)))
        print(json.dumps(res, indent=2, default=str))
        return 0 if res.get("ok") else 1
    if args.cmd == "verkle-audit":
        from mag.verkle_audit import run_audit

        res = run_audit(
            full=bool(getattr(args, "full", False)),
            synth=bool(getattr(args, "synth", False)),
            reconcile=not bool(getattr(args, "no_reconcile", False)),
            backfill_lattice=bool(getattr(args, "backfill", False) or getattr(args, "full", False)),
            dry=bool(getattr(args, "dry", False)),
        )
        print(json.dumps(res, indent=2, default=str))
        return 0 if res.get("ok") else 1
    if args.cmd == "field-steal":
        from mag.field_steal import run_field_steal

        root = (getattr(args, "root", None) or "").strip()
        if not root:
            root = str(ROOT.parent / "field-strike-the-chord")
        res = run_field_steal(root, max_files=int(getattr(args, "max_files", 0) or 0))
        if getattr(args, "json", False):
            print(json.dumps(res, indent=2, default=str))
        else:
            print(json.dumps(res, indent=2, default=str))
            md = (res.get("paths") or {}).get("latest_md")
            if md and Path(md).is_file():
                print("\n" + Path(md).read_text(encoding="utf-8")[:8000])
        return 0 if res.get("ok") else 1
    if args.cmd == "context-pack":
        from mag.context_pack import (
            build_context_pack,
            format_agent_preamble,
            format_context_pack_text,
        )

        # text for humans/Grok; also write latest for hooks
        pack = build_context_pack(refresh_bonds=bool(getattr(args, "refresh_bonds", False)))
        out = ROOT / "memory" / "context_pack_latest.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        text = format_context_pack_text(pack)
        out.write_text(text, encoding="utf-8")
        (ROOT / "memory" / "context_pack_latest.json").write_text(
            json.dumps(pack, indent=2, default=str), encoding="utf-8"
        )
        if getattr(args, "agent", False):
            preamble = format_agent_preamble(
                pack,
                goal=(getattr(args, "goal", None) or "").strip(),
            )
            ap = ROOT / "memory" / "agent_preamble_latest.md"
            ap.write_text(preamble, encoding="utf-8")
            print(preamble)
            return 0
        print(text)
        return 0
    if args.cmd == "bonds":
        from mag.bonds import BONDS_MD, ingest_bonds, load_bonds_json, scan_conflicts

        scan_text = (getattr(args, "scan", None) or "").strip()
        if scan_text:
            bj = load_bonds_json() or {}
            existing = [str(x) for x in (bj.get("residual_bonds") or [])]
            hits = scan_conflicts(scan_text, existing)
            print(json.dumps({"ok": True, "candidate": scan_text, "conflicts": hits}, indent=2, default=str))
            return 0

        sid = (getattr(args, "session", None) or "").strip() or None
        res = ingest_bonds(session_id=sid, write=True)
        print(json.dumps(res, indent=2, default=str))
        if getattr(args, "print_bonds", False) and BONDS_MD.is_file():
            print("\n" + BONDS_MD.read_text(encoding="utf-8")[:6000])
        return 0 if res.get("ok") else 1

    if args.cmd == "diary":
        from mag.diary import build_diary, format_diary_markdown, write_diary_face
        newest = bool(getattr(args, "newest", False))
        if getattr(args, "write", False):
            d = write_diary_face(newest_first=newest)
        else:
            d = build_diary(newest_first=newest)
        if getattr(args, "json", False):
            print(json.dumps(d, indent=2, default=str)[:50000])
        else:
            print(format_diary_markdown(d)[:20000])
            if d.get("face"):
                print("\n# face:", d.get("face"))
        return 0 if d.get("ok") else 1

    if args.cmd == "ideas":
        from mag import idea_graph as ig

        action = (getattr(args, "action", None) or "list").strip().lower()
        ids = list(getattr(args, "ids", None) or [])
        as_json = bool(getattr(args, "json", False))
        try:
            if action == "summary":
                res = ig.summary()
                print(json.dumps(res, indent=2, default=str))
                return 0
            if action == "seed":
                res = ig.seed_from_working_and_agent_state()
                print(json.dumps(res, indent=2, default=str))
                return 0 if res.get("ok") else 1
            if action == "add":
                title = (getattr(args, "title", None) or "").strip()
                if not title and ids:
                    title = " ".join(ids)
                if not title:
                    print(json.dumps({"ok": False, "error": "need --title or positional title"}))
                    return 1
                ntype = (getattr(args, "idea_type", None) or "topic").strip() or "topic"
                status = (getattr(args, "status", None) or "open").strip() or "open"
                node = ig.add_node(
                    title=title,
                    ntype=ntype,
                    status=status,
                    body=(getattr(args, "body", None) or "").strip(),
                    source="human",
                )
                ig.write_latest_face()
                print(json.dumps({"ok": True, "node": node}, indent=2, default=str))
                return 0
            if action == "link":
                if len(ids) < 2:
                    print(json.dumps({"ok": False, "error": "ideas link SRC DST [--type related]"}))
                    return 1
                etype = (getattr(args, "idea_type", None) or "related").strip() or "related"
                edge = ig.link(
                    ids[0],
                    ids[1],
                    etype=etype,
                    note=(getattr(args, "note", None) or "").strip(),
                    ref=(getattr(args, "ref", None) or "").strip(),
                )
                ig.write_latest_face()
                print(json.dumps({"ok": True, "edge": edge}, indent=2, default=str))
                return 0
            if action == "pack":
                nid = (ids[0] if ids else "").strip()
                if not nid:
                    print(json.dumps({"ok": False, "error": "ideas pack NODE_ID"}))
                    return 1
                text = ig.pack_node(nid)
                if as_json:
                    print(json.dumps({"ok": True, "pack": text}, indent=2))
                else:
                    print(text)
                return 0 if not text.startswith("(idea pack:") else 1
            if action == "show":
                nid = (ids[0] if ids else "").strip()
                if not nid:
                    print(json.dumps({"ok": False, "error": "ideas show NODE_ID"}))
                    return 1
                nb = ig.neighborhood(nid, depth=1)
                print(json.dumps(nb, indent=2, default=str))
                return 0 if nb.get("ok") else 1
            # list (default)
            status = (getattr(args, "status", None) or "").strip() or None
            ntype = (getattr(args, "idea_type", None) or "").strip() or None
            rows = ig.list_nodes(
                status=status,
                ntype=ntype,
                limit=int(getattr(args, "limit", 40) or 40),
            )
            if as_json:
                print(json.dumps({"ok": True, "nodes": rows, **ig.summary()}, indent=2, default=str))
            else:
                print(ig.format_list(rows))
                sm = ig.summary()
                print(f"\n# {sm.get('n_nodes')} nodes · {sm.get('n_edges')} edges · {sm.get('schema')}")
            return 0
        except ValueError as e:
            print(json.dumps({"ok": False, "error": str(e)}))
            return 1
    if args.cmd == "agent-state":
        from mag import agent_state as ast

        if getattr(args, "list_versions", False):
            rows = ast.list_versions(limit=30)
            print(json.dumps(rows, indent=2, default=str))
            return 0
        show = (getattr(args, "show", None) or "").strip()
        if show:
            ver = ast.load_version(show)
            if not ver:
                print(json.dumps({"ok": False, "error": f"not found: {show}"}))
                return 1
            if getattr(args, "json", False):
                print(json.dumps(ver, indent=2, default=str)[:20000])
            else:
                print(ast.format_load_markdown(ver))
            return 0
        if getattr(args, "link_residual", False):
            res = ast.link_to_residual((getattr(args, "session", None) or "").strip() or None)
            print(json.dumps(res, indent=2, default=str))
            return 0 if res.get("ok") else 1
        commit_reason = (getattr(args, "commit", None) or "").strip()
        if commit_reason:
            payload: dict = {}
            ff = (getattr(args, "from_file", None) or "").strip()
            if ff:
                p = Path(ff)
                if not p.is_file():
                    p = ROOT / ff
                payload = json.loads(p.read_text(encoding="utf-8"))
            else:
                # minimal commit without full payload — still versioned
                prev = ast.load_latest() or {}
                payload = {
                    "commitment": f"agent-state-manual-{commit_reason[:40]}",
                    "one_line": prev.get("one_line")
                    or "Manual agent-state commit — fill via --from-file next time",
                    "do_not_redesign": prev.get("do_not_redesign")
                    or ["LOAD LATEST before redesign"],
                    "compose_bundles": prev.get("compose_bundles") or [],
                    "next_moves": prev.get("next_moves") or [],
                    "stack": prev.get("stack") or {},
                    "paths": prev.get("paths") or {},
                    "leave": prev.get("leave") or [],
                    "notes": commit_reason,
                }
            res = ast.commit_state(
                payload,
                label=commit_reason[:80],
                reason=commit_reason,
            )
            print(json.dumps(res, indent=2, default=str))
            return 0 if res.get("ok") else 1
        # default: --load or status
        if getattr(args, "load", False) or not getattr(args, "json", False):
            print(ast.format_load_markdown())
            if getattr(args, "json", False):
                lat = ast.load_latest()
                print("\n--- JSON ---\n")
                print(json.dumps(lat, indent=2, default=str)[:12000] if lat else "{}")
            return 0
        lat = ast.load_latest()
        print(json.dumps(lat or {"ok": False, "error": "no state"}, indent=2, default=str)[:16000])
        return 0 if lat else 1
    if args.cmd == "compose-status":
        from mag.modules import (
            attach_related_runs_to_residual,
            compose_status,
            format_compose_status,
        )

        if getattr(args, "attach_runs", False):
            att = attach_related_runs_to_residual(
                (getattr(args, "session", None) or "").strip() or None
            )
            print(json.dumps(att, indent=2, default=str))
            if not att.get("ok"):
                return 1
        st = compose_status()
        if getattr(args, "json", False):
            print(json.dumps(st, indent=2, default=str)[:16000])
        else:
            print(format_compose_status(st))
        return 0 if st.get("ok") else 1
    if args.cmd == "trail":
        from mag import run_trail as rt

        action = args.action
        rid = (getattr(args, "run", None) or "").strip() or None
        text = " ".join(getattr(args, "text", None) or []).strip()

        if action == "start":
            if not text:
                print(json.dumps({"ok": False, "error": "goal required"}))
                return 1
            res = rt.start_run(
                text,
                seat=args.seat,
                proactivity=args.proactivity,
                force=bool(args.force),
                never_remote=bool(getattr(args, "never_remote", False)),
                git_sha=(getattr(args, "git_sha", None) or "").strip(),
            )
            print(json.dumps(res, indent=2, default=str))
            return 0 if res.get("ok") else 1

        if action == "append":
            if not text:
                print(json.dumps({"ok": False, "error": "summary required"}))
                return 1
            label = (getattr(args, "label", None) or "").strip()
            if label:
                # Multi-agent FILE into trail (Elias rope) — not peer chat.
                res = rt.file_agent_core(
                    label,
                    text,
                    run_id=rid,
                    text=(getattr(args, "core_text", None) or "").strip() or text,
                    locus=(getattr(args, "locus", None) or "").strip(),
                    drift_kind=(getattr(args, "drift_kind", None) or "note").strip(),
                    evidence=(getattr(args, "evidence", None) or "").strip(),
                    base_id=(getattr(args, "base_id", None) or "").strip(),
                )
                print(json.dumps(res, indent=2, default=str))
                return 0 if res.get("ok") else 1
            core = None
            core_text = (getattr(args, "core_text", None) or "").strip()
            core_raw = (getattr(args, "core", None) or "").strip()
            if core_text:
                core = {
                    "type": (args.kind if args.kind not in ("note", "run_start") else "decision"),
                    "text": core_text[:800],
                }
            elif core_raw:
                try:
                    core = json.loads(core_raw)
                except json.JSONDecodeError as e:
                    print(json.dumps({"ok": False, "error": f"core json: {e}; use --core-text"}))
                    return 1
            # Do not pass default --seat on append (would false-fail purity).
            # Seat purity is for check-seat / explicit mid-run thrash detection.
            res = rt.append_event(
                args.kind,
                text,
                run_id=rid,
                seat=None,
                core=core,
            )
            print(json.dumps(res, indent=2, default=str))
            return 0 if res.get("ok") else 1

        if action == "status":
            print(json.dumps(rt.status(), indent=2, default=str))
            return 0

        if action == "close":
            res = rt.close_run(rid, reason=args.reason)
            print(json.dumps(res, indent=2, default=str))
            return 0 if res.get("ok") else 1

        if action == "check-seat":
            res = rt.check_seat(args.seat, run_id=rid)
            print(json.dumps(res, indent=2, default=str))
            return 0 if res.get("ok") else 1

        if action == "cores":
            cores = rt.cores_for_reinject(rid)
            print(json.dumps({"ok": True, "n": len(cores), "cores": cores}, indent=2, default=str))
            return 0

        if action == "pack":
            res = rt.trail_pack_excerpt(run_id=rid)
            print(json.dumps(res, indent=2, default=str))
            return 0

        if action == "base":
            res = rt.ensure_run_base(rid)
            print(json.dumps(res, indent=2, default=str))
            return 0 if res.get("ok") else 1

        if action == "drifts":
            res = rt.list_drifts(rid)
            print(json.dumps(res, indent=2, default=str))
            return 0 if res.get("ok") else 1

        print(json.dumps({"ok": False, "error": f"unknown action {action}"}))
        return 1
    if args.cmd == "providers":
        from models.providers import status_table

        print(json.dumps(status_table(), indent=2, default=str))
        return 0
    if args.cmd == "quota":
        from models.quota import all_budgets

        print(json.dumps(all_budgets(), indent=2, default=str))
        return 0
    if args.cmd == "provider-chat":
        from models.providers import chat_provider, chat_routed

        prompt = " ".join(args.prompt)
        system = "You are Mag L1 helper. Public text only. Be concise."
        if args.provider:
            res = chat_provider(
                args.provider,
                system,
                prompt,
                model=args.model or None,
                tier=args.tier,
            )
        else:
            res = chat_routed(
                system,
                prompt,
                job=args.job,
                tier=args.tier,
                model=args.model or None,
            )
        print(json.dumps(res, indent=2, default=str)[:4000])
        return 0 if res.get("ok") else 1
    if args.cmd == "hermes-status":
        from harness.hermes_cli import hermes_status

        res = hermes_status()
        print(json.dumps(res, indent=2, default=str))
        return 0 if res.get("available") else 1
    if args.cmd == "dispatch":
        from mag.dispatch import dispatch

        res = dispatch(
            " ".join(args.goal),
            execute=not args.dry,
            force_provider=args.provider or None,
            force_seat=args.seat or None,
        )
        print(json.dumps(res, indent=2, default=str)[:5000])
        return 0 if res.get("ok") else 1
    if args.cmd == "coordinate":
        from mag.coordination import coordinate

        goal = " ".join(args.goal)
        res = coordinate(
            goal,
            depth=(args.depth or None),
            seat=(args.seat or "cli").strip() or "cli",
            actor="cli",
            launch=not args.dry,
            background=bool(args.background),
            session_id=(args.session or "").strip() or None,
        )
        print(json.dumps(res, indent=2, default=str)[:8000])
        return 0 if res.get("ok") else 1
    if args.cmd == "route":
        goal = " ".join(args.goal)
        if getattr(args, "local", False):
            from mag.route import route_goal

            res = route_goal(goal, run_local=True)
        else:
            from mag.router import route

            res = route(goal, depth=(args.depth or None))
        print(json.dumps(res, indent=2, default=str)[:8000])
        return 0 if res.get("ok") else 1
    if args.cmd == "decide":
        from mag.decision_framework import decide

        goal = " ".join(args.goal)
        res = decide(goal, depth=(args.depth or None))
        print(json.dumps(res, indent=2, default=str)[:8000])
        return 0 if res.get("ok") else 1
    if args.cmd == "fkb":
        from mag.failure_kb import _cli as fkb_cli

        return fkb_cli(list(getattr(args, "fkb_args", []) or []))
    if args.cmd == "orchestrator":
        from mag.orchestrator import main as orc_main

        return orc_main(list(getattr(args, "orc_args", []) or []))
    if args.cmd == "gpipes":
        from mag.gpipes import main as gp_main

        return gp_main(list(getattr(args, "gp_args", []) or []))
    if args.cmd == "agent":
        from mag.agent_cli import run_agent

        return run_agent(
            provider=(args.provider or "deepseek").strip(),
            model=(args.model or "").strip() or None,
            one_shot=(args.query or "").strip() or None,
        )
    if args.cmd == "tangent":
        from mag.tangent import enqueue, list_tangents, process_one, process_queue, scan_live_for_tangents

        if args.list:
            print(json.dumps(list_tangents(), indent=2, default=str)[:8000])
            return 0
        if args.scan:
            print(json.dumps(scan_live_for_tangents(auto_run=False), indent=2, default=str))
        if args.process or args.scan:
            res = process_queue(max_n=3 if args.process else 1)
            print(json.dumps(res, indent=2, default=str)[:6000])
            return 0
        prompt = " ".join(args.prompt or []).strip()
        if not prompt:
            print("usage: main.py tangent \"go check …\" | --list | --process | --scan")
            return 2
        enq = enqueue(
            prompt,
            source="cli",
            provider=args.provider or None,
            prefer_gemini=not bool(args.provider),
            run_async=False,
        )
        if not enq.get("ok"):
            print(json.dumps(enq, indent=2, default=str))
            return 1
        if args.no_run:
            print(json.dumps(enq, indent=2, default=str))
            return 0
        res = process_one(str(enq.get("id")))
        print(json.dumps({"queued": enq, "result": res}, indent=2, default=str)[:6000])
        return 0 if res.get("ok") else 1
    if args.cmd == "improve":
        from mag.improve import improve_once, scout, status_summary, run_eval, deep_dive

        if args.status:
            print(json.dumps(status_summary(), indent=2, default=str))
            return 0
        if args.deep:
            res = deep_dive(
                minutes=args.minutes,
                max_tickets=args.max_tickets,
                dry=args.dry,
            )
            print(json.dumps(res, indent=2, default=str)[:12000])
            return 0 if res.get("ok") else 1
        if args.synthesize and not args.scout and not args.eval:
            res = improve_once(synthesize_only=True, dry=args.dry)
            print(json.dumps(res, indent=2, default=str))
            return 0 if res.get("ok") else 1
        if args.scout and not args.eval:
            res = scout(dry=args.dry)
            print(json.dumps(res, indent=2, default=str))
            return 0 if res.get("ok") else 1
        if args.eval and not args.scout:
            res = run_eval()
            print(json.dumps(res, indent=2, default=str))
            return 0 if res.get("ok") else 1
        # --once or default (scout + eval + synthesis)
        res = improve_once(
            scout_only=False,
            eval_only=False,
            dry=args.dry,
        )
        if args.scout and args.eval:
            res = improve_once(dry=args.dry)
        print(json.dumps(res, indent=2, default=str))
        return 0 if res.get("ok") else 1
    if args.cmd == "promote":
        from mag.improve import promote_apply, promote_reject

        if args.reject:
            res = promote_reject(args.candidate_id, reason=args.reason)
        elif args.apply:
            res = promote_apply(args.candidate_id, force_model=args.force_model)
        else:
            print("pass --apply or --reject")
            return 2
        print(json.dumps(res, indent=2, default=str))
        return 0 if res.get("ok") else 1
    if args.cmd == "lattice-loop":
        from mag.lattice_loop import plant_status as lattice_status, start_loop, stop_loop

        if getattr(args, "backfill", False):
            from mag.lattice_backfill import run_backfill

            res = run_backfill(dry_run=bool(getattr(args, "dry_run", False)))
            print(json.dumps(res, indent=2, default=str))
            return 0 if res.get("ok") else 1
        if args.stop:
            # signal stop via state file (works for detached process too)
            st_path = (
                __import__("pathlib").Path(__file__).resolve().parent
                / "memory"
                / "improve"
                / "blast"
                / "lattice"
                / "state.json"
            )
            res = stop_loop()
            if st_path.is_file():
                try:
                    st = json.loads(st_path.read_text(encoding="utf-8"))
                    st["run"] = False
                    st_path.write_text(json.dumps(st, indent=2), encoding="utf-8")
                except Exception:
                    pass
            print(json.dumps(res, indent=2, default=str)[:8000])
            return 0
        if args.run and args.bg:
            # Detached lasting process (daemon thread dies when CLI exits)
            import subprocess
            import sys

            py = sys.executable
            log = ROOT / "logs" / "lattice_loop_stdout.log"
            log.parent.mkdir(parents=True, exist_ok=True)
            cmd = [
                py,
                str(ROOT / "main.py"),
                "lattice-loop",
                "--run",
                f"--cycle-seconds={int(args.cycle_seconds or 90)}",
                f"--max-cycles={int(args.max_cycles or 0)}",
            ]
            # Windows: new process group, don't wait
            creation = 0
            if sys.platform == "win32":
                creation = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
                creation |= getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
            from datetime import datetime, timezone

            with log.open("a", encoding="utf-8") as lf:
                lf.write(f"\n--- spawn {datetime.now(timezone.utc).isoformat()} ---\n")
                lf.write(" ".join(cmd) + "\n")
            log_handle = log.open("a", encoding="utf-8")
            proc = subprocess.Popen(
                cmd,
                cwd=str(ROOT),
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                env={**__import__("os").environ},
                creationflags=creation if sys.platform == "win32" else 0,
                start_new_session=(sys.platform != "win32"),
            )
            # pid file
            pid_path = (
                ROOT / "memory" / "improve" / "blast" / "lattice" / "loop.pid"
            )
            pid_path.parent.mkdir(parents=True, exist_ok=True)
            pid_path.write_text(str(proc.pid), encoding="utf-8")
            print(
                json.dumps(
                    {
                        "ok": True,
                        "started": True,
                        "detached": True,
                        "pid": proc.pid,
                        "log": str(log),
                        "status": lattice_status(),
                    },
                    indent=2,
                    default=str,
                )[:12000]
            )
            return 0
        if args.run:
            res = start_loop(
                background=False,
                cycle_seconds=int(args.cycle_seconds or 90),
                max_cycles=int(args.max_cycles or 0),
            )
            print(json.dumps(res, indent=2, default=str)[:12000])
            return 0 if res.get("ok") else 1
        print(json.dumps(lattice_status(), indent=2, default=str)[:12000])
        return 0
    if args.cmd == "blast":
        from mag.blast import (
            plant_status,
            start_blast,
            stop_blast,
            pause_blast,
            write_influence,
        )

        if args.focus or args.minutes is not None or args.max_tickets is not None or args.cycle_seconds is not None:
            patch: dict = {}
            if args.focus:
                patch["focus"] = args.focus
            if args.minutes is not None:
                patch["dig_minutes"] = args.minutes
            if args.max_tickets is not None:
                patch["max_tickets"] = args.max_tickets
            if args.cycle_seconds is not None:
                patch["cycle_seconds"] = args.cycle_seconds
            write_influence(patch, by="cli")
        if args.stop:
            print(json.dumps(stop_blast(), indent=2, default=str)[:8000])
            return 0
        if args.pause:
            print(json.dumps(pause_blast(True), indent=2, default=str)[:8000])
            return 0
        if args.resume:
            print(json.dumps(pause_blast(False), indent=2, default=str)[:8000])
            return 0
        if args.run:
            res = start_blast(background=bool(args.bg))
            print(json.dumps(res, indent=2, default=str)[:12000])
            return 0 if res.get("ok") else 1
        # default / --status
        print(json.dumps(plant_status(), indent=2, default=str)[:12000])
        return 0
    if args.cmd == "research-pack":
        from mag.research_pack import build_research_pack, load_pack, run_pack

        built = build_research_pack(
            args.ask,
            urls=list(args.url or []),
            success_criteria=list(args.criterion) or None,
            title=args.title or "",
            elevate_to="grok_tui" if args.elevate else "local",
        )
        print(json.dumps(built, indent=2, default=str))
        if not built.get("ok"):
            return 1
        if args.run or args.elevate:
            pack = load_pack(built.get("json"))
            seat = "grok_tui" if args.elevate else "local"
            if args.provider:
                seat = "remote"
            ran = run_pack(
                pack,
                seat=seat,
                provider=args.provider or None,
            )
            print("--- run ---")
            print(json.dumps(ran, indent=2, default=str)[:6000])
        return 0
    if args.cmd == "lab":
        return cmd_lab(
            host=args.host,
            port=args.port,
            ui_only=args.ui_only,
            no_dashboard=args.no_dashboard,
            with_instrument=args.with_instrument,
        )
    if args.cmd == "governor":
        from mag.governor import main as governor_main
        return governor_main(["--dry", str(args.dry)] if args.dry else ["--run", str(args.run)])
    if args.cmd == "autopilot":
        from mag.autopilot import autopilot_once
        import json as _json

        res = autopilot_once(
            queue_improve=not args.no_queue,
            governor=not args.no_governor,
            drain=bool(args.drain),
            max_queue=int(args.max_queue or 2),
        )
        print(_json.dumps(res, indent=2, default=str))
        return 0 if res.get("ok") else 1
    if args.cmd == "autorun":
        from mag.governor_autorun import main as autorun_main

        argv: list[str] = []
        if getattr(args, "once", False):
            argv.append("--once")
        if getattr(args, "dry", False):
            argv.append("--dry")
        if getattr(args, "no_fill", False):
            argv.append("--no-fill")
        if getattr(args, "fill_only", False):
            argv.append("--fill-only")
        if getattr(args, "interval", None):
            argv.extend(["--interval", str(args.interval)])
        return autorun_main(argv)
    if args.cmd == "seat-guard":
        from mag.seat_guard import main as sg_main
        return sg_main(args.sg_args)
    parser.print_help()
    return 2


def cmd_lab(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    ui_only: bool = False,
    no_dashboard: bool = False,
    with_instrument: bool = False,
) -> int:
    """One integral process: watch + Mag (+ dashboard by default)."""
    if with_instrument:
        print(
            "instrument (optional analysis only): "
            "sovereign-mirror-scaffold :8743 — not Mag brand"
        )
    if ui_only:
        from dashboard.server import run as run_dashboard

        print("=== Mag UI only (no watch) — live board will go stale ===")
        run_dashboard(host=host, port=port)
        return 0

    from mag.runtime import run_integral

    # Dashboard in same process; watch+mag integral
    if no_dashboard:
        run_integral(with_dashboard=False, host=host, port=port)
    else:
        run_integral(with_dashboard=True, host=host, port=port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


def cmd_governor(args):
    # Autorun the governor loop (the product).
    from mag.governor import main as governor_main
    return governor_main(["--run", str(args.run if hasattr(args, "run") else 1)])
