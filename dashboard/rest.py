"""RESTful API surface for Mag dashboard (v1).

Resource-oriented paths. Legacy /api/* handlers remain as thin aliases.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote

from config import ROOT

BIO = ROOT / "memory" / "biography"
INGEST = ROOT / "memory" / "ingest"

HandlerFn = Callable[[dict[str, str], dict[str, Any] | None], tuple[int, dict[str, Any]]]


def _ok(data: dict[str, Any] | None = None, *, status: int = 200, schema: str | None = None) -> tuple[int, dict]:
    """Uniform success envelope."""
    body: dict[str, Any] = {"ok": True}
    if schema:
        body["schema"] = schema
    if data:
        body.update(data)
    return status, body


def _err(code: int, message: str, **extra: Any) -> tuple[int, dict]:
    """Uniform error envelope — use real HTTP codes, not 200 + ok:false."""
    body: dict[str, Any] = {"ok": False, "error": str(message)[:500]}
    body.update(extra)
    return code, body


def _read_json(path: Path) -> Any | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _read_jsonl(path: Path, limit: int = 500) -> list[Any]:
    if not path.is_file():
        return []
    rows: list[Any] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows[-limit:]


def _pid_alive(pid: int | None) -> bool:
    """Liveness check that works on Windows (os.kill(pid,0) is unreliable there)."""
    if not pid:
        return False
    try:
        import psutil

        return psutil.pid_exists(pid)
    except Exception:
        pass
    if os.name == "nt":
        # Windows-native liveness via OpenProcess (no psutil dependency).
        try:
            import ctypes
            from ctypes import wintypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            h = ctypes.windll.kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid)
            )
            if not h:
                return False
            try:
                ec = wintypes.DWORD()
                ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(ec))
                return ec.value == 259  # STILL_ACTIVE
            finally:
                ctypes.windll.kernel32.CloseHandle(h)
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


# --- handlers ---


def h_health(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.health import sanity

    return 200, sanity()


def h_fleet_triad(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    """Always-on triad (engine / scribe / dashboard) from the supervisor state
    file + live pid checks. Lets the board show the persistent agents next to
    the one-shot fleet."""
    import os
    from config import ROOT

    state_path = ROOT / "state" / "mag_launch.json"
    roles = [
        ("backend", "Backend", "FastAPI tool service - 127.0.0.1:8000"),
        ("engine", "Engineer", "the Mag seat / planner"),
        ("scribe", "Scribe", "synthesis_agent.py - running commentary"),
        ("dashboard", "Dashboard", "this board - 127.0.0.1:8765"),
        ("mirror", "Mirror desk", "Sovereign Mirror strike - 127.0.0.1:8743"),
        ("drainer", "Drainer", "optional queue auto-advance"),
    ]
    out = []
    try:
        st = json.loads(state_path.read_text(encoding="utf-8"))
        pids = st.get("pids") or {}
        notes = st.get("notes") or {}
        health = st.get("health") or {}
    except Exception:
        pids, notes, health = {}, {}, {}
    for key, label, desc in roles:
        pid = pids.get(key)
        alive = _pid_alive(pid)
        out.append({
            "key": key, "label": label, "desc": desc,
            "pid": pid, "alive": alive,
            "health": health.get(key),
            "note": notes.get(key, ""),
        })
    return 200, {"ok": True, "triad": out}


def h_chronicle(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    """Tripartite Chronicle — file-backed pulse from synthesis_agent + structured events."""
    from mag.chronicle import build_chronicle_payload

    return 200, build_chronicle_payload()


def h_seats(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    """Inbound clients (Cursor, dashboard, Grok TUI) + outbound API providers."""
    from mag.seat_registry import list_registered
    from mag.seats import build_seats_registry

    reg = build_seats_registry()
    reg["registered"] = list_registered(limit=40, live_only=True)
    return 200, reg


def h_seats_register(_p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    """Register desktop/cloud seat with orchestrator mesh — returns MAG_TASK_ID."""
    from mag.seat_registry import register

    data = dict(body or {})
    seat = str(data.get("seat") or "cursor").strip() or "cursor"
    goal = str(data.get("goal") or data.get("detail") or "").strip()
    mode = str(data.get("mode") or "interactive").strip() or "interactive"
    task_id = str(data.get("task_id") or data.get("mag_task_id") or "").strip() or None
    pid = data.get("pid")
    try:
        pid = int(pid) if pid is not None else None
    except (TypeError, ValueError):
        pid = None
    rec = register(
        seat=seat,
        goal=goal,
        mode=mode,
        task_id=task_id,
        pid=pid,
        tag=str(data.get("tag") or "").strip(),
        parent=str(data.get("parent") or "api").strip() or "api",
    )
    return 200, rec


def h_seats_heartbeat(_p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    """Refresh liveness for a registered seat."""
    from mag.seat_registry import heartbeat

    data = dict(body or {})
    task_id = str(data.get("task_id") or data.get("mag_task_id") or _p.get("id") or "").strip()
    if not task_id:
        return _err(400, "task_id required")
    rec = heartbeat(
        task_id,
        phase=str(data.get("phase") or "").strip() or None,
        goal=str(data.get("goal") or "").strip() or None,
        seat=str(data.get("seat") or "").strip() or None,
    )
    return (200 if rec.get("ok") else 404), rec


def h_seats_unregister(_p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.seat_registry import unregister

    data = dict(body or {})
    task_id = str(data.get("task_id") or data.get("mag_task_id") or _p.get("id") or "").strip()
    if not task_id:
        return _err(400, "task_id required")
    status = str(data.get("status") or "done").strip() or "done"
    detail = str(data.get("detail") or "").strip()
    rec = unregister(task_id, status=status, detail=detail)
    return (200 if rec.get("ok") else 404), rec


def h_power(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.power import stack_status

    return 200, stack_status()


def h_power_stop(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    """Kill switch — stops stack (may terminate this dashboard process)."""
    import threading

    from mag.power import stop_all

    def _run() -> None:
        time.sleep(0.3)
        stop_all()

    threading.Thread(target=_run, daemon=True).start()
    return 200, {
        "ok": True,
        "action": "stopping",
        "hint": "Stack shutting down — refresh will fail until mag.cmd power start",
    }


def h_power_start(_p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.power import start_all

    data = dict(body or {})
    open_browser = bool(data.get("browser") or data.get("open_browser"))
    return 200, start_all(open_browser=open_browser)


def h_improve_cloud(_p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    """Cloud agent files handoff + optional improve cycle enqueue."""
    from mag.improve_loop import write_cloud_handoff

    data = dict(body or {})
    goal = str(data.get("goal") or data.get("question") or "").strip()
    claim = str(data.get("claim") or "").strip()
    brief = str(data.get("brief") or data.get("body") or "").strip()
    if not (goal or claim or brief):
        return _err(400, "goal, claim, or brief required")
    enqueue = bool(data.get("enqueue") or data.get("queue"))
    res = write_cloud_handoff(
        goal=goal,
        claim=claim,
        brief=brief,
        source=str(data.get("source") or "cursor-cloud").strip(),
        depth=str(data.get("depth") or "simple_code").strip(),
        enqueue=enqueue,
        run_id=str(data.get("run_id") or "").strip() or None,
        meta=data.get("meta") if isinstance(data.get("meta"), dict) else None,
    )
    return (200 if res.get("ok") else 422), res


def h_improve_cycle(_p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    """Run one improve cycle — behavioral + queue + nervous + spider."""
    from mag.improve_loop import run_improve_cycle

    data = dict(body or {})
    source = str(data.get("source") or "api").strip() or "api"
    res = run_improve_cycle(
        source=source,
        max_improve=int(data.get("max_improve") or 2),
        drain_one=bool(data.get("drain") or data.get("drain_one")),
        spider_inject=bool(data.get("spider_inject")),
        scout=bool(data.get("scout")),
    )
    return (200 if res.get("ok") else 500), res


def h_governance(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.governance import build_governance

    return 200, build_governance()


def h_post_governance(_p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    """Toggle autonomy prefs or broadcast steer to chat + running workers."""
    from mag.governance import broadcast_steer
    from mag.preferences import set_drainer, set_inject_behavioral_pack, set_operator_active

    data = body or {}
    if "steer" in data or data.get("cmd"):
        cmd = str(data.get("steer") or data.get("cmd") or "").strip()
        if not cmd:
            return _err(400, "steer/cmd required")
        return 200, {"ok": True, **broadcast_steer(cmd)}
    out: dict[str, Any] = {"ok": True}
    if "drainer" in data:
        set_drainer(bool(data["drainer"]))
        out["drainer"] = True
    if "operator_active" in data:
        set_operator_active(bool(data["operator_active"]))
        out["operator_active"] = True
    if "inject_behavioral_pack" in data:
        set_inject_behavioral_pack(bool(data["inject_behavioral_pack"]))
        out["inject_behavioral_pack"] = True
    from mag.governance import build_governance

    out["governance"] = build_governance()
    return 200, out


def h_operator_inbox(_p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.operator_inbox import clear_pending, commit_guidance, status as inbox_status

    if body is None or not body:
        return 200, inbox_status()
    action = str(body.get("action") or "commit").strip().lower()
    if action == "clear":
        return 200, clear_pending()
    text = str(body.get("text") or "").strip()
    if not text:
        return _err(400, "text required")
    return 200, commit_guidance(text, source=str(body.get("source") or "dashboard"))


def h_mag_os(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    """Mag OS v2 card + live provenance (dashboard load)."""
    from mag.os_v2 import live_status

    return 200, live_status()


def h_home_summary(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    """One payload for the Home tab: health, tip, latest bead, loops, economy."""
    from mag.health import sanity

    health = sanity()
    tip = _read_json(BIO / "verkle_tip.json") or {}
    root = str(tip.get("root") or "")

    dig_edges_n = 0
    res_dir = BIO / "residual"
    if res_dir.is_dir():
        for p in res_dir.glob("*.json"):
            try:
                o = json.loads(p.read_text(encoding="utf-8", errors="replace"))
            except (json.JSONDecodeError, OSError):
                continue
            kind = str(o.get("kind") or "").lower()
            edges = o.get("edges") if isinstance(o.get("edges"), dict) else {}
            if kind in ("dig_leaf", "dig", "corpus_leaf") or edges.get("dig_leaf"):
                dig_edges_n += 1
            digs = edges.get("dig_leaves") or edges.get("related_digs") or []
            if isinstance(digs, list) and digs:
                dig_edges_n += len(digs)

    bonds: dict[str, Any] = {}
    open_loops: list[str] = []
    residual_bonds: list[str] = []
    next_moves: list[str] = []
    try:
        from mag.bonds import BONDS_MD, ingest_bonds, load_bonds_json

        if not BONDS_MD.is_file():
            ingest_bonds(write=True)
        bonds = load_bonds_json() or {}
        open_loops = [str(x)[:200] for x in (bonds.get("open_loops") or [])[:8]]
        residual_bonds = [str(x)[:160] for x in (bonds.get("residual_bonds") or [])[:8]]
        next_moves = [str(x)[:200] for x in (bonds.get("next_moves") or [])[:6]]
    except Exception as e:
        bonds = {"error": str(e)}

    latest: dict[str, Any] = {}
    previous: dict[str, Any] = {}
    n_sessions = 0
    try:
        from mag.registry import get_latest_session_id, list_registry, load_residual

        rows = list_registry(limit=300)
        n_sessions = len(rows)
        sid = get_latest_session_id()
        if not sid and rows:
            sid = rows[0].get("session_id")

        def _bead_from(reg: dict, res: dict | None = None) -> dict[str, Any]:
            res = res if isinstance(res, dict) else {}
            card = (res.get("session_card") if res else None) or {}
            bid = reg.get("session_id") or ""
            return {
                "session_id": bid,
                "title": card.get("title") or reg.get("title") or (bid[:12] if bid else "—"),
                "blurb": card.get("blurb") or reg.get("blurb") or reg.get("one_liner") or "",
                "bullets": (card.get("bullets") or reg.get("bullets") or [])[:6],
                "dominant_theme": reg.get("dominant_theme") or res.get("dominant_theme"),
                "end_minute": reg.get("end_minute") or (res.get("time") or {}).get("end_minute"),
                "has_residual": bool(res),
            }

        if sid:
            reg = next((r for r in rows if r.get("session_id") == sid), {}) or {}
            res = load_residual(sid) or {}
            latest = _bead_from(reg, res)
            # previous distinct session in registry order
            for r in rows:
                if r.get("session_id") and r.get("session_id") != sid:
                    previous = {
                        "session_id": r.get("session_id"),
                        "title": r.get("title") or str(r.get("session_id"))[:12],
                        "blurb": r.get("blurb") or r.get("one_liner") or "",
                        "end_minute": r.get("end_minute"),
                    }
                    break
    except Exception as e:
        latest = {"error": str(e)}

    economy: dict[str, Any] = {}
    try:
        from mag.token_economy import economy_snapshot

        economy = economy_snapshot()
    except Exception as e:
        economy = {"error": str(e)}

    smoke: dict[str, Any] = {}
    try:
        from models.multi_smoke import last_smoke

        smoke = last_smoke() or {}
    except Exception:
        smoke = {}

    working_open: list[str] = []
    working_lane = ""
    wp = ROOT / "memory" / "working.md"
    if wp.is_file():
        text = wp.read_text(encoding="utf-8", errors="replace")
        in_open = False
        in_lane = False
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("## "):
                title = s[3:].strip().lower()
                in_open = title == "open"
                in_lane = "lane" in title
                continue
            if in_lane and s.startswith("- ") and not working_lane:
                working_lane = s[2:].strip()[:200]
            if s.startswith("- [ ]") or s.startswith("- [DOING]") or "**DOING**" in s:
                working_open.append(s[:180])
            elif in_open and s.startswith("- "):
                working_open.append(s[2:].strip()[:180])
            if len(working_open) >= 8:
                break

    ideas_open: list[dict[str, Any]] = []
    ideas_n = 0
    ideas_root = None
    try:
        from mag import idea_graph as ig

        ideas_n = len(ig.load_nodes())
        for n in ig.list_nodes(status="open", limit=8):
            ideas_open.append(
                {
                    "id": n.get("id"),
                    "type": n.get("type"),
                    "title": n.get("title"),
                    "status": n.get("status"),
                }
            )
        spine = ig.get_node("n_spine_workspace")
        if spine:
            ideas_root = spine.get("id")
    except Exception:
        pass

    integral = (health.get("integral") or {}) if isinstance(health, dict) else {}
    recording = (health.get("recording") or {}) if isinstance(health, dict) else {}
    lanes = (health.get("lanes") or {}) if isinstance(health, dict) else {}

    ollama_ok = bool((lanes.get("L0_ollama") or {}).get("ok") if isinstance(lanes, dict) else False) or bool(
        (health.get("L0_ollama") or {}).get("ok") if isinstance(health, dict) else False
    )
    # dashboard-only mode still useful: port open + tip + residual
    port_ok = bool(integral.get("port_8765")) or True  # this handler running ⇒ port ok
    office_up = bool(integral.get("up") or health.get("status") == "up")
    # if only dashboard (no integral heartbeat), still "viewport up"
    live_stale = bool(recording.get("live_stale"))
    has_bead = bool(latest.get("has_residual") or latest.get("session_id"))
    smoke_ok = smoke.get("ok")
    if smoke_ok is None:
        smoke_ok = False

    compose: dict[str, Any] = {}
    active_run = None
    try:
        from mag.modules import compose_status

        cs = compose_status()
        rt = cs.get("runtime") or {}
        active_run = rt.get("active_run")
        compose = {
            "ok": bool(cs.get("ok")),
            "n_modules": cs.get("n_modules"),
            "missing": cs.get("n_missing_paths"),
            "active_run": active_run,
        }
    except Exception as e:
        compose = {"ok": False, "error": str(e)}

    # Provenance paths (zeitgeist: files remember)
    sid = latest.get("session_id")
    provenance: dict[str, Any] = {
        "session_id": sid,
        "residual_rel": f"memory/biography/residual/{sid}.json" if sid else None,
        "tip_rel": "memory/biography/verkle_tip.json",
        "bonds_rel": "memory/bonds_active.md",
        "operator_card": "docs/ref/OPERATOR_CARD.md",
        "mirror_presented": "docs/ref/MIRROR_PRESENTED.md",
    }
    if sid:
        try:
            from mag.registry import residual_path

            rp = residual_path(sid)
            if rp and rp.is_file():
                try:
                    provenance["residual_rel"] = str(rp.relative_to(ROOT)).replace("\\", "/")
                except ValueError:
                    provenance["residual_abs"] = str(rp)
        except Exception:
            pass

    # ARK-shaped ship badge → Mag gates (authorship / DNA, not civic)
    caveats: list[str] = []
    provisional: list[str] = []
    if not has_bead:
        provisional.append("No residual bead for latest day")
    if not tip.get("n_leaves"):
        provisional.append("No Verkle tip leaves")
    if not ollama_ok:
        caveats.append("Ollama L0 not OK")
    if live_stale:
        caveats.append("Live board stale — refresh the board when you care")
    if not smoke_ok:
        caveats.append("multi-smoke not PASS (or never run)")
    # dig_edges / "case lattice" removed from operator-facing caveats (noise, not signal)
    if open_loops and len(open_loops) >= 5:
        caveats.append(f"{len(open_loops)} open loops stacking")
    if compose.get("ok") is False:
        caveats.append("module compose not clean")
    if active_run:
        caveats.append(f"Open run active: {active_run}")

    if provisional:
        ship = "PROVISIONAL"
        ship_why = provisional + caveats
    elif caveats:
        ship = "CAVEATS"
        ship_why = caveats
    else:
        ship = "OK"
        ship_why = ["day chain live", "latest day filed", "local smoke ok"]

    # Phoenix: self-correct when stack degrades (Mag dual of ARK)
    phoenix_on = ship != "OK"
    phoenix_reasons = list(ship_why) if phoenix_on else []
    phoenix_fix = []
    if live_stale:
        phoenix_fix.append("mag.cmd catch-up  (or dashboard Catch up)")
    if not smoke_ok:
        phoenix_fix.append("mag.cmd multi-smoke")
    if not has_bead:
        phoenix_fix.append("Close session / backfill residual")
    if not phoenix_fix and phoenix_on:
        phoenix_fix.append("mag.cmd doctor")

    # Verify day (60s dual of ARK challenge checklist)
    verify = [
        {"id": "residual", "label": "Residual DNA exists for latest day", "ok": bool(has_bead)},
        {
            "id": "tip",
            "label": "Tip has leaves (chain alive)",
            "ok": bool(tip.get("n_leaves")),
        },
        {
            "id": "tip_match",
            "label": "Tip last session matches latest bead",
            "ok": bool(
                sid
                and tip.get("last_session_id")
                and str(tip.get("last_session_id")) == str(sid)
            ),
        },
        {
            "id": "blurb",
            "label": "Bead has blurb (filed story, not empty)",
            "ok": bool((latest.get("blurb") or "").strip()),
        },
        {
            "id": "smoke",
            "label": "multi-smoke PASS",
            "ok": bool(smoke_ok),
        },
        {
            "id": "dig",
            "label": "Research notes linked to a workday (optional)",
            "ok": dig_edges_n > 0,
        },
    ]
    verify_pass = sum(1 for v in verify if v["ok"])
    verify_n = len(verify)

    # Short chips for Office advanced — plain language
    zeitgeist = [
        "Find truth → file a note → load a short pack next time",
        "Your files are the memory",
        "Quote yourself as written",
        "Brief the model; don’t dump the whole chat",
        "No king of the network",
    ]

    primary_next = ""
    if ideas_open:
        primary_next = str(ideas_open[0].get("title") or "")
    elif next_moves:
        primary_next = str(next_moves[0])
    elif working_open:
        primary_next = str(working_open[0])
    elif open_loops:
        primary_next = str(open_loops[0])

    last_title = (latest.get("title") or "").strip() or "no day filed yet"
    # Plain operator headline for Office home — not status-bar chrome
    if ship == "OK":
        headline = f"Last day filed: {last_title[:90]}"
    elif ship == "CAVEATS":
        headline = f"Last day: {last_title[:70]} · note: {(ship_why[0] if ship_why else 'check Status')[:60]}"
    else:
        headline = f"No solid day on file yet · {(ship_why[0] if ship_why else 'file a day')[:70]}"

    tip_short = (root[:12] + "…") if len(root) > 12 else (root or "—")

    payload = {
        "ok": True,
        "schema": "mag_home_summary.v2",
        "path": "FIND → FILE → LOAD",
        "operator_card": "docs/ref/OPERATOR_CARD.md",
        "headline": headline,
        "zeitgeist": zeitgeist,
        "ship": {
            "status": ship,
            "why": ship_why[:8],
            "note": "Internal health for Status tab — not the top-bar chrome",
        },
        "phoenix": {
            "on": phoenix_on,
            "reasons": phoenix_reasons[:6],
            "fixes": phoenix_fix[:5],
        },
        "verify": {
            "pass": verify_pass,
            "n": verify_n,
            "items": verify,
        },
        "provenance": provenance,
        "compose": compose,
        "health": {
            "status": health.get("status") if isinstance(health, dict) else "unknown",
            "up": office_up or port_ok,
            "office_up": office_up,
            "live_stale": live_stale,
            "port_8765": port_ok,
            "ollama": ollama_ok,
        },
        "tip": {
            "root_short": tip_short,
            "n_leaves": tip.get("n_leaves"),
            "last_filename": tip.get("last_filename"),
            "last_session_id": tip.get("last_session_id"),
            "updated_minute": tip.get("updated_minute"),
            "dig_edges_n": dig_edges_n,
        },
        "n_sessions": n_sessions,
        "latest_bead": latest,
        "previous_bead": previous,
        "trail": {"latest": latest, "previous": previous or None},
        "trajectory": {
            "primary_next": primary_next,
            "ideas_open": ideas_open[:6],
            "loops": open_loops[:6],
            "next_moves": next_moves[:6],
            "working_open": working_open[:6],
        },
        "now": {
            "working_lane": working_lane,
            "active_run": active_run,
            "tip_short": tip_short,
            "n_sessions": n_sessions,
        },
        "ideas": {
            "n": ideas_n,
            "open": ideas_open[:8],
            "root_id": ideas_root,
        },
        "open_loops": open_loops,
        "residual_bonds": residual_bonds,
        "next_moves": next_moves,
        "working_open": working_open,
        "economy_today": (economy.get("today") or {}) if isinstance(economy, dict) else {},
        "multi_smoke_ok": smoke_ok,
        "multi_smoke_models": smoke.get("models_seen"),
    }
    try:
        from mag.launch_pad import build_launch_pad

        payload["launch_pad"] = build_launch_pad(n_sessions=n_sessions, ship=ship)
    except Exception:
        payload["launch_pad"] = {"show": False}
    try:
        from mag.autorun_status import autorun_dashboard_status

        ar = autorun_dashboard_status()
        gov = ar.get("governor") or {}
        last_auto = (ar.get("autorun") or {}).get("last_tick") or {}
        drainer_on = bool(gov.get("drainer_enabled"))
        alive = bool(gov.get("autorun_alive"))
        open_mag = int(gov.get("open_todo_mag") or 0)
        if not drainer_on:
            autorun_headline = "Autorun off — add queue lines or set MAG_DRAINER=1"
            autorun_state = "idle"
        elif alive:
            autorun_headline = "Mag is working away"
            autorun_state = "active"
        elif open_mag:
            autorun_headline = f"Queued — {open_mag} [mag] item(s) waiting"
            autorun_state = "queued"
        else:
            autorun_headline = "Drainer on — nothing queued"
            autorun_state = "idle"
        payload["autorun"] = {
            "state": autorun_state,
            "headline": autorun_headline,
            "drainer_enabled": drainer_on,
            "open_todo_mag": open_mag,
            "last_tick_ts": last_auto.get("ts"),
            "last_action": last_auto.get("action") or (gov.get("last_cycle") or {}).get("action"),
            "hints": (ar.get("hints") or {}),
        }
    except Exception as e:
        payload["autorun"] = {"state": "unknown", "headline": "Autorun status unavailable", "error": str(e)[:120]}
    return 200, payload


def h_ideas(p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    """GET collection: idea cards (optional ?status= & ?type= & ?limit=)."""
    try:
        from mag import idea_graph as ig

        status = (p.get("status") or "").strip() or None
        ntype = (p.get("type") or "").strip() or None
        try:
            limit = int(p.get("limit") or 80)
        except ValueError:
            limit = 80
        nodes = ig.list_nodes(status=status, ntype=ntype, limit=max(1, min(limit, 200)))
        return _ok({**ig.summary(), "nodes": nodes, "filter": {"status": status, "type": ntype}})
    except Exception as e:
        return _err(500, str(e), nodes=[])


def h_idea_one(p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    """GET one idea resource."""
    nid = (p.get("id") or "").strip()
    if not nid:
        return _err(400, "id required")
    try:
        from mag import idea_graph as ig

        node = ig.get_node(nid)
        if not node:
            return _err(404, f"idea not found: {nid}")
        nb = ig.neighborhood(str(node["id"]), depth=1)
        return _ok(
            {
                "schema": ig.SCHEMA,
                "id": node["id"],
                "node": node,
                "neighborhood": {
                    "n_nodes": nb.get("n_nodes"),
                    "n_edges": nb.get("n_edges"),
                    "edges": nb.get("edges") or [],
                },
            }
        )
    except Exception as e:
        return _err(500, str(e))


def h_idea_pack(p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    """GET brief (pack) subresource for one idea — LOAD slice for models."""
    nid = (p.get("id") or "").strip()
    if not nid:
        return _err(400, "id required")
    try:
        from mag import idea_graph as ig

        node = ig.get_node(nid)
        if not node:
            return _err(404, f"idea not found: {nid}")
        text = ig.pack_node(str(node["id"]))
        return _ok({"schema": ig.SCHEMA, "id": node["id"], "node": node, "pack": text})
    except Exception as e:
        return _err(500, str(e))


def h_ideas_create(_p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    """POST collection — create a card (title required)."""
    body = body or {}
    title = str(body.get("title") or "").strip()
    if not title:
        return _err(400, "title required")
    try:
        from mag import idea_graph as ig

        node = ig.add_node(
            title=title,
            ntype=str(body.get("type") or body.get("ntype") or "open_loop"),
            status=str(body.get("status") or "open"),
            body=str(body.get("body") or ""),
            refs=list(body.get("refs") or []) if isinstance(body.get("refs"), list) else None,
            tags=list(body.get("tags") or []) if isinstance(body.get("tags"), list) else None,
            source=str(body.get("source") or "human"),
        )
        ig.write_latest_face()
        return _ok({"schema": ig.SCHEMA, "node": node, "id": node["id"]}, status=201)
    except ValueError as e:
        return _err(400, str(e))
    except Exception as e:
        return _err(500, str(e))


def h_idea_patch(p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    """PATCH one idea — status / title / body (mark done, shelf, reopen)."""
    nid = (p.get("id") or "").strip()
    if not nid:
        return _err(400, "id required")
    body = body or {}
    try:
        from mag import idea_graph as ig

        kwargs: dict[str, Any] = {}
        if "status" in body and body["status"] is not None:
            kwargs["status"] = str(body["status"])
        if "title" in body and body["title"] is not None:
            kwargs["title"] = str(body["title"])
        if "body" in body and body["body"] is not None:
            kwargs["body"] = str(body["body"])
        if "tags" in body and isinstance(body["tags"], list):
            kwargs["tags"] = body["tags"]
        if not kwargs:
            return _err(400, "nothing to patch — send status, title, body, and/or tags")
        node = ig.patch_node(nid, **kwargs)
        return _ok({"schema": ig.SCHEMA, "id": node["id"], "node": node})
    except KeyError as e:
        return _err(404, str(e))
    except ValueError as e:
        return _err(400, str(e))
    except Exception as e:
        return _err(500, str(e))


def h_ideas_seed(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    """POST action: import open items from working notes + agent_state paths."""
    try:
        from mag import idea_graph as ig

        res = ig.seed_from_working_and_agent_state()
        return _ok(res if isinstance(res, dict) else {"result": res})
    except Exception as e:
        return _err(500, str(e))





def h_diary(params: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    """Day-by-day story spine from filed beads."""
    from mag.diary import build_diary, write_diary_face
    newest = str(params.get('newest') or params.get('order') or '').lower() in ('1', 'true', 'newest', 'desc')
    write = str(params.get('write') or '').lower() in ('1', 'true', 'yes')
    if write:
        d = write_diary_face(newest_first=newest)
    else:
        d = build_diary(newest_first=newest)
    return 200, d


def h_story(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    """Full thesis + hero journey for Story dock tab."""
    from mag.story import build_story

    try:
        return 200, build_story(write_face=True)
    except Exception as e:
        return 500, {"ok": False, "error": str(e)[:400], "schema": "mag_story.v1"}


def h_story_file(params: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    """Read a small text artifact for Story tab (path under Mag ROOT only)."""
    rel = unquote(str(params.get("path") or "")).replace("\\", "/").lstrip("/")
    if not rel or ".." in rel.split("/"):
        return 400, {"ok": False, "error": "bad path"}
    # Stay inside Mag root — no path escape
    path = (ROOT / rel).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError:
        return 403, {"ok": False, "error": "path outside Mag root"}
    if not path.is_file():
        return 404, {"ok": False, "error": "not found", "path": rel}
    if path.suffix.lower() not in {".md", ".txt", ".json", ".yaml", ".yml", ".rhai", ".ps1"}:
        return 415, {"ok": False, "error": "type not text-previewable"}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return 500, {"ok": False, "error": str(e)[:200]}
    if len(text) > 120_000:
        text = text[:120_000] + "\n…(clipped)"
    return 200, {
        "ok": True,
        "path": rel,
        "bytes": path.stat().st_size,
        "text": text,
    }

def h_router_status(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    """Router dashboard: honest quotas, live connections, ingest — not fake savings."""
    from datetime import datetime, timezone

    out: dict[str, Any] = {
        "ok": True,
        "schema": "mag_router_status.v1",
        "ts": datetime.now(timezone.utc).isoformat(),
        "product": "Sovereign router — plug into others' infrastructure; residual stays local",
        "honesty": (
            "Budgets are Mag-tracked from configs/providers.yaml + logs/quota_state.json. "
            "They are NOT Grok TUI / ChatGPT web plan percentages. Vendor dashboards are source of truth for subscription %.")
    }

    # --- connections (providers) ---
    try:
        from models.providers import status_table, load_providers
        from models.quota import all_budgets

        st = status_table()
        budgets = {b.get("provider"): b for b in (all_budgets().get("providers") or [])}
        prefer = list((load_providers().get("defaults") or {}).get("prefer_order") or [])
        connections = []
        for row in st.get("providers") or []:
            pid = row.get("id")
            b = budgets.get(pid) or {}
            max_c = b.get("max_calls")
            used_c = int(b.get("used_calls") or 0)
            max_t = b.get("max_tokens")
            used_t = int(b.get("used_tokens") or 0)
            pct_c = round(100.0 * used_c / max_c, 1) if max_c else None
            pct_t = round(100.0 * used_t / max_t, 1) if max_t else None
            # primary pressure signal
            pct = pct_c if pct_c is not None else pct_t
            if pct_c is not None and pct_t is not None:
                pct = max(pct_c, pct_t)
            connections.append({
                "id": pid,
                "name": row.get("name") or pid,
                "live": bool(row.get("configured")),
                "local": bool(row.get("free_local")),
                "model": row.get("default_model"),
                "tier_max": row.get("tier_max"),
                "key_env": row.get("key_env"),
                "used_calls": used_c,
                "max_calls": max_c,
                "used_tokens": used_t,
                "max_tokens": max_t,
                "pct_used": pct,
                "remaining_calls": b.get("remaining_calls"),
                "remaining_tokens": b.get("remaining_tokens"),
                "reset_in_hours": b.get("reset_in_hours"),
                "budget_ok": b.get("budget_ok", True),
                "unlimited": b.get("unlimited", False),
                "note": b.get("note") or "",
            })
        # sort: live first, then by pressure
        connections.sort(key=lambda r: (0 if r["live"] else 1, -(r["pct_used"] or 0), r["id"]))
        out["connections"] = connections
        out["prefer_order"] = prefer
        out["n_live"] = sum(1 for c in connections if c["live"])
        out["n_remote_live"] = sum(1 for c in connections if c["live"] and not c["local"])
    except Exception as e:
        out["connections_error"] = str(e)[:300]

    # --- usage today (honest, not counterfactual) ---
    try:
        from mag.lanes import usage_today_counts, grok_escalations_today, load_lanes
        lanes = load_lanes()
        max_d = int((lanes.get("grok_budget") or {}).get("max_escalations_per_day") or 8)
        used_g = grok_escalations_today()
        out["usage_today"] = {
            "by_lane": usage_today_counts(),
            "grok_escalations": used_g,
            "grok_escalation_budget": max_d,
            "grok_escalation_pct": round(100.0 * used_g / max_d, 1) if max_d else None,
            "note": "Lane counts from Mag logs. Grok *TUI subscription* % is not visible to Mag.",
        }
    except Exception as e:
        out["usage_error"] = str(e)[:200]

    # --- ingest / websites ---
    try:
        cat = _read_json(INGEST / "catalog.json") or {}
        items = cat.get("items") or {}
        if isinstance(items, dict):
            item_list = list(items.values())
        elif isinstance(items, list):
            item_list = items
        else:
            item_list = []
        urls = []
        kinds: dict[str, int] = {}
        for it in item_list:
            if not isinstance(it, dict):
                continue
            k = str(it.get("kind") or "other")
            kinds[k] = kinds.get(k, 0) + 1
            u = it.get("url")
            if u:
                urls.append({
                    "title": (it.get("title") or "")[:80],
                    "url": str(u)[:200],
                    "kind": k,
                    "id": it.get("id"),
                })
        # newest last in dict insertion — reverse for recent
        urls = list(reversed(urls))[:40]
        out["ingest"] = {
            "count": cat.get("count") or len(item_list),
            "kinds": kinds,
            "recent_urls": urls[:12],
            "all_urls_n": sum(1 for it in item_list if isinstance(it, dict) and it.get("url")),
        }
    except Exception as e:
        out["ingest_error"] = str(e)[:200]

    # --- local memory spine ---
    try:
        from mag import idea_graph as ig
        nodes = ig.load_nodes()
        out["memory"] = {
            "idea_nodes": len(nodes),
            "idea_open": sum(1 for n in nodes if n.get("status") == "open"),
            "idea_edges": len(ig.load_edges()),
        }
    except Exception as e:
        out["memory"] = {"error": str(e)[:120]}

    try:
        from mag.registry import list_registry
        rows = list_registry(limit=500)
        out["memory"] = dict(out.get("memory") or {})
        out["memory"]["sessions_filed"] = len(rows)
    except Exception:
        pass

    # --- nervous keys (presence only) ---
    try:
        from mag.nervous_system import build_glance
        g = build_glance(write=False)
        out["body"] = {
            "ollama": bool((g.get("body") or {}).get("ollama") or g.get("body_alive")),
            "ok": g.get("ok"),
            "keys": g.get("keys") or [],
            "open_loops": (g.get("open_loops") or [])[:5],
        }
    except Exception as e:
        out["body_error"] = str(e)[:120]

    # --- supervisor (mag_launch.json) ---
    try:
        ml = _read_json(ROOT / "state" / "mag_launch.json") or {}
        pids = ml.get("pids") or {}
        wanted = ml.get("wanted") or {}
        alive = {}
        for role, pid in pids.items():
            if pid and _pid_alive(pid):
                alive[role] = pid
        # supervisor "running" = any wanted role has a live pid
        any_live = any(alive.get(r) for r in wanted if wanted.get(r))
        out["supervisor"] = {
            "running": any_live,
            "pids": alive,
            "wanted": wanted,
            "started": ml.get("started"),
            "check_s": ml.get("check_s"),
        }
    except Exception as e:
        out["supervisor_error"] = str(e)[:120]

    # --- orchestrator fleet ---
    try:
        from mag.orchestrator import TASK_DIR, TERMINAL
        tasks = []
        if TASK_DIR.is_dir():
            for p in TASK_DIR.glob("*.json"):
                try:
                    t = json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    continue
                tasks.append({
                    "task_id": t.get("task_id"),
                    "goal": (t.get("goal") or "")[:80],
                    "status": t.get("status"),
                    "provider": t.get("provider"),
                    "created": t.get("created"),
                    "finished": t.get("finished"),
                    "exit_code": t.get("exit_code"),
                })
        tasks.sort(key=lambda t: t.get("created") or "", reverse=True)
        out["fleet"] = {
            "total": len(tasks),
            "running": sum(1 for t in tasks if t["status"] not in TERMINAL),
            "done": sum(1 for t in tasks if t["status"] == "done"),
            "failed": sum(1 for t in tasks if t["status"] in ("failed", "died")),
            "killed": sum(1 for t in tasks if t["status"] == "killed"),
            "recent": tasks[:10],
        }
        # --- orchestrator task queue (auto-advance) ---
        try:
            from mag.orchestrator import queue_status as _qs
            out["queue"] = _qs()
        except Exception as qe:
            out["queue_error"] = str(qe)[:120]
    except Exception as e:
        out["fleet_error"] = str(e)[:120]

    # headline pressure
    hot = []
    for c in out.get("connections") or []:
        if c.get("live") and not c.get("local") and c.get("pct_used") is not None and c["pct_used"] >= 25:
            hot.append(f"{c['id']} ~{c['pct_used']}% of Mag budget")
    out["pressure"] = hot[:6]
    out["headline"] = (
        f"{out.get('n_live', 0)} live routes · "
        + (f"pressure: {', '.join(hot[:2])}" if hot else "no Mag-budget pressure")
    )

    try:
        from mag.preferences import drainer_status

        out["drainer"] = drainer_status()
    except Exception as e:
        out["drainer"] = {"error": str(e)[:120]}

    try:
        import urllib.request

        mirror_up = False
        try:
            with urllib.request.urlopen("http://127.0.0.1:8743/", timeout=1.5) as resp:
                mirror_up = 200 <= resp.status < 300
        except Exception:
            mirror_up = False
        out["mirror"] = {
            "port": 8743,
            "up": mirror_up,
            "url": "http://127.0.0.1:8743/",
            "mag_tab": "http://127.0.0.1:8743/?preset=demo",
        }
    except Exception as e:
        out["mirror"] = {"error": str(e)[:120]}

    return 200, out


def h_seat_feed(p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.seat_feed import unified_seat_feed

    try:
        n = int(p.get("n") or 40)
    except ValueError:
        n = 40
    return 200, unified_seat_feed(limit=max(5, min(n, 80)))


def h_coordination(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    """Shared activity feed — all seats see who is doing what."""
    from mag.coordination import activity_summary, read_activity

    try:
        limit = int(_p.get("limit") or 20)
    except ValueError:
        limit = 20
    summary = activity_summary(limit=max(1, min(limit, 80)))
    summary["entries"] = read_activity(limit=summary.get("recent") and limit or limit)
    return 200, summary


def h_coordination_post(_p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    """Log heartbeat / status from any seat (DeepSeek, Cursor, etc.)."""
    from mag.coordination import log_activity

    data = dict(body or {})
    goal = str(data.get("goal") or data.get("detail") or "heartbeat").strip()
    row = log_activity(
        seat=str(data.get("seat") or "unknown").strip() or "unknown",
        depth=str(data.get("depth") or "scut").strip(),
        goal=goal,
        status=str(data.get("status") or "running").strip(),
        actor=str(data.get("actor") or data.get("seat") or "").strip() or None,
        detail=str(data.get("detail") or "")[:300],
        task_id=str(data.get("task_id") or "").strip() or None,
    )
    return 200, {"ok": True, "activity": row}


def h_route(_p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    """Unified routing decision — classify + seat + provider + honest failure."""
    from mag.router import route

    data = dict(body or {})
    goal = str(data.get("goal") or data.get("question") or "").strip()
    if not goal:
        return _err(400, "goal required")
    depth = str(data.get("depth") or "").strip() or None
    force_seat = str(data.get("force_seat") or "").strip() or None
    force_provider = str(data.get("force_provider") or "").strip() or None
    res = route(
        goal,
        depth=depth,
        force_seat=force_seat,
        force_provider=force_provider,
    )
    launch = data.get("launch", False)
    if isinstance(launch, str):
        launch = launch.lower() not in ("0", "false", "no")
    if launch:
        from mag.coordination import coordinate

        exec_res = coordinate(
            goal,
            depth=depth,
            seat=str(data.get("caller_seat") or data.get("seat") or "api"),
            actor=str(data.get("actor") or "api"),
            launch=True,
            background=bool(data.get("background")),
            session_id=str(data.get("session_id") or "").strip() or None,
        )
        return (200 if exec_res.get("ok") else 500), {"route": res, "execution": exec_res}
    return 200, res


def h_decide(_p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    """Framework decision: route + behavioral tips + breadcrumb interference status."""
    from mag.decision_framework import decide

    data = dict(body or {})
    goal = str(data.get("goal") or data.get("question") or "").strip()
    if not goal and not _p.get("goal"):
        return _err(400, "goal required")
    goal = goal or str(_p.get("goal") or "").strip()
    depth = str(data.get("depth") or _p.get("depth") or "").strip() or None
    res = decide(goal, depth=depth)
    return (200 if res.get("ok") else 422), res


def h_coordinate(_p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    """Classify depth + optionally launch the appropriate seat."""
    from mag.coordination import coordinate

    data = dict(body or {})
    goal = str(data.get("goal") or data.get("question") or "").strip()
    if not goal:
        return _err(400, "goal required")
    depth = str(data.get("depth") or "").strip() or None
    seat = str(data.get("seat") or "api").strip() or "api"
    launch = data.get("launch", True)
    if isinstance(launch, str):
        launch = launch.lower() not in ("0", "false", "no")
    background = bool(data.get("background"))
    res = coordinate(
        goal,
        depth=depth,
        seat=seat,
        actor=str(data.get("actor") or seat),
        launch=bool(launch),
        background=background,
        session_id=str(data.get("session_id") or "").strip() or None,
    )
    code = 200 if res.get("ok") else 500
    return code, res


def h_drainer_status(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.preferences import drainer_status

    st = drainer_status()
    try:
        ml = _read_json(ROOT / "state" / "mag_launch.json") or {}
        pids = ml.get("pids") or {}
        pid = pids.get("drainer")
        st["supervisor_pid"] = pid
        st["alive"] = bool(pid and _pid_alive(int(pid)))
    except Exception:
        st["alive"] = False
    return 200, {"ok": True, **st}


def h_drainer_toggle(_p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.preferences import drainer_status, set_drainer

    body = body or {}
    enabled = body.get("enabled")
    if enabled is None:
        return _err(400, "enabled boolean required")
    set_drainer(bool(enabled))
    st = drainer_status()
    return 200, {"ok": True, "drainer": st, "hint": st.get("hint")}


def h_workspace_tree(p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.workspace_api import list_tree

    rel = str(p.get("path") or "").strip()
    try:
        depth = int(p.get("depth") or 2)
    except ValueError:
        depth = 2
    return 200, list_tree(rel, max_depth=max(1, min(depth, 4)))


def h_workspace_file_get(p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.workspace_api import read_file

    rel = str(p.get("path") or "").strip()
    if not rel:
        return _err(400, "path required")
    res = read_file(rel)
    return (200 if res.get("ok") else 404), res


def h_workspace_file_post(_p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.workspace_api import write_file

    body = body or {}
    rel = str(body.get("path") or "").strip()
    if not rel:
        return _err(400, "path required")
    res = write_file(rel, str(body.get("text") or ""))
    return (200 if res.get("ok") else 400), res


def h_autopilot(_p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.autopilot import autopilot_once

    body = body or {}
    res = autopilot_once(
        queue_improve=body.get("queue_improve", True) is not False,
        governor=body.get("governor", True) is not False,
        drain=bool(body.get("drain")),
        max_queue=int(body.get("max_queue") or 2),
    )
    return 200, res


def h_orchestrator_queue_post(_p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.orchestrator import enqueue

    body = body or {}
    goal = str(body.get("goal") or "").strip()
    if not goal:
        return _err(400, "goal required")
    rec = enqueue(
        goal,
        provider=str(body.get("provider") or "deepseek"),
        tag=str(body.get("tag") or "api"),
    )
    return 200, {"ok": True, **rec}


def h_seat_task(_p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    """Unified Cursor→Mag tasking: {goal?, seat?, mode: delegate|queue|autopilot|agent|dispatch}."""
    data = dict(body or {})
    mode = str(data.get("mode") or "delegate").strip().lower()
    seat = str(data.get("seat") or "cursor").strip() or "cursor"
    goal = str(data.get("goal") or data.get("question") or data.get("q") or "").strip()

    if mode == "autopilot":
        code, res = h_autopilot(_p, data)
        if isinstance(res, dict):
            res.setdefault("mode", mode)
            res.setdefault("seat", seat)
        return code, res

    if mode in ("queue", "enqueue"):
        if not goal:
            return _err(400, "goal required for queue mode")
        tag = str(data.get("tag") or f"{seat}-queued").strip()
        code, res = h_orchestrator_queue_post(_p, {**data, "goal": goal, "tag": tag})
        if isinstance(res, dict):
            res.setdefault("mode", mode)
            res.setdefault("seat", seat)
        return code, res

    if mode in ("agent", "delegate", "ask"):
        if not goal:
            return _err(400, "goal required")
        session = str(data.get("session_id") or data.get("session") or seat).strip() or seat
        code, res = h_post_agent(_p, {**data, "goal": goal, "session_id": session})
        if isinstance(res, dict):
            res.setdefault("mode", mode)
            res.setdefault("seat", seat)
        return code, res

    if mode == "dispatch":
        if not goal:
            return _err(400, "goal required")
        code, res = h_post_dispatch(_p, {**data, "goal": goal, "seat": seat})
        if isinstance(res, dict):
            res.setdefault("mode", mode)
            res.setdefault("seat", seat)
        return code, res

    return _err(
        400,
        f"unknown mode {mode!r} — use delegate|queue|autopilot|agent|dispatch",
    )


def h_kpi(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.records import write_kpi

    return 200, write_kpi(source="api")


def h_registry(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.registry import list_registry

    rows = list_registry(limit=300)
    return 200, {"ok": True, "count": len(rows), "sessions": rows}


def h_sessions(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    from dashboard.server import list_sessions

    rows = list_sessions()
    return 200, {"ok": True, "count": len(rows), "sessions": rows}


def h_session(params: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    from dashboard.server import api_session

    data = api_session(unquote(params["id"]))
    code = 200 if data.get("ok") else 404
    return code, data


def h_session_residual(params: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.registry import load_residual

    sid = unquote(params["id"])
    d = load_residual(sid)
    if not d:
        return 404, {"ok": False, "error": "residual not found", "session_id": sid}
    return 200, {"ok": True, "session_id": sid, "residual": d}


def h_board(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.lanes import board_pack

    return 200, board_pack()


def h_chain(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    return 200, {
        "ok": True,
        "tip": _read_json(BIO / "verkle_tip.json"),
        "chain": _read_jsonl(BIO / "verkle_chain.jsonl"),
        "evolution": _read_json(BIO / "topic_evolution.json"),
        "timeline": _read_jsonl(BIO / "knot_timeline.jsonl"),
    }


def h_ingest(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    cat = _read_json(INGEST / "catalog.json") or {}
    reg = _read_jsonl(INGEST / "registry.jsonl", limit=200)
    return 200, {"ok": True, "catalog": cat, "registry_tail": reg}


def h_overview(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    from dashboard.server import api_overview

    return 200, api_overview()


def h_nervous(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    """Agent-ops nervous system glance (no secrets)."""
    from mag.nervous_system import build_glance

    return 200, build_glance(write=True)


def h_grove(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    """Tesuji Grove — poem skill tree nodes (v3-012)."""
    from mag.grove import build, list_nodes

    limit = 20
    try:
        limit = max(1, min(100, int(_p.get("limit") or "20")))
    except ValueError:
        pass
    refresh = str(_p.get("refresh") or "").lower() in ("1", "true", "yes")
    build_report = build(dry=False) if refresh else None
    nodes = list_nodes(limit=limit)
    return 200, {
        "ok": True,
        "schema": "grove_list.v1",
        "nodes": nodes,
        "count": len(nodes),
        "build": build_report,
    }


def h_lattice_history(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    """Verkle lattice history + planning summary for dashboard."""
    from mag.lattice_dashboard import build_lattice_summary

    return 200, build_lattice_summary()


def h_viewports(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    """List synced Cursor Canvas viewports."""
    from mag.canvas_bridge import list_viewports

    rows = list_viewports()
    return _ok({"viewports": rows, "count": len(rows)}, schema="viewports_list.v1")


def h_viewport_one(p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    """One canvas viewport manifest."""
    from mag.canvas_bridge import load_viewport

    vid = unquote(p.get("id") or "")
    res = load_viewport(vid)
    if not res.get("ok"):
        return _err(404, str(res.get("error") or "not found"))
    return _ok({"viewport": res["viewport"]}, schema="canvas_viewport.v1")


def h_viewports_sync(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    """Run canvas sync from external *.canvas.tsx sources."""
    from mag.canvas_bridge import sync_canvases

    dry = bool((_b or {}).get("dry_run"))
    return _ok(sync_canvases(dry_run=dry), schema="canvas_sync.v1")


def h_models(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    from models.registry import inventory

    return 200, inventory()


def h_providers(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    from models.providers import status_table

    return 200, status_table()


def h_quota(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    from models.quota import all_budgets

    return 200, all_budgets()


def h_economy(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.token_economy import economy_snapshot, load_chat_system_prompt

    snap = economy_snapshot()
    try:
        prompt = load_chat_system_prompt()
        snap["chat_prompt_preview"] = prompt[:500]
        snap["chat_prompt_chars"] = len(prompt)
    except Exception as e:
        snap["chat_prompt_error"] = str(e)
    return 200, snap


def h_usage(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.lanes import (
        grok_escalations_today,
        load_lanes,
        usage_tail,
        usage_today_counts,
    )

    lanes = load_lanes()
    max_d = int((lanes.get("grok_budget") or {}).get("max_escalations_per_day") or 8)
    used = grok_escalations_today()
    return 200, {
        "ok": True,
        "today": usage_today_counts(),
        "grok_escalations_today": used,
        "grok_budget_max": max_d,
        "tail": usage_tail(50),
        "lanes": lanes,
    }


def h_idea_flow(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.idea_flow import build_idea_flow

    try:
        return 200, build_idea_flow()
    except Exception as e:
        return 500, {"ok": False, "error": str(e)}


def h_brief_latest(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.lanes import briefs_dir, latest_brief_text

    text = latest_brief_text()
    return 200, {
        "ok": bool(text),
        "text": text,
        "dir": str(briefs_dir()),
    }


def h_visual(params: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    sid = unquote(params.get("id") or "latest")
    from mag.registry import find_derived

    if sid == "latest":
        vp = _read_json(BIO / "latest.visual_pack.json")
    else:
        p = find_derived(sid, "visual_pack")
        vp = _read_json(p) if p else None
        if not vp:
            vp = _read_json(BIO / f"{sid}.visual_pack.json")
    if not vp:
        return 404, {"ok": False, "error": "no visual pack", "session_id": sid}
    return 200, vp if isinstance(vp, dict) else {"ok": True, "pack": vp}


def h_post_catch_up(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.health import catch_up

    return 200, catch_up()


def h_post_ask(_p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.ask import ask as mag_ask

    data = body or {}
    q = str(data.get("question") or data.get("q") or "").strip()
    if not q:
        return 400, {"ok": False, "error": "question required"}
    sid = (data.get("session_id") or data.get("session") or "").strip() or None
    use_llm = bool(data.get("use_llm", True))
    return 200, mag_ask(q, session_id=sid, use_llm=use_llm)


def h_post_dispatch(_p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    """Chat / API: route a goal through Mag dispatch (local first)."""
    from mag.dispatch import REMOTE_PROVIDERS, dispatch as mag_dispatch

    data = body or {}
    goal = str(data.get("goal") or data.get("question") or data.get("q") or "").strip()
    if not goal:
        return 400, {"ok": False, "error": "goal required"}
    dry = bool(data.get("dry") or data.get("classify_only"))
    provider = str(data.get("provider") or "").strip() or None
    seat = str(data.get("seat") or "").strip() or None
    # Dashboard remote seats: provider alone must not silently land on local
    if provider and provider.lower() in REMOTE_PROVIDERS and not seat:
        seat = "remote"
    try:
        res = mag_dispatch(
            goal,
            execute=not dry,
            force_provider=provider,
            force_seat=seat,
        )
        return 200, res if isinstance(res, dict) else {"ok": True, "result": res}
    except Exception as e:
        return 500, {"ok": False, "error": str(e)}


def h_post_agent(_p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    """Tool-using Mag agent turn (DeepSeek + local tools). Dashboard Agent mode."""
    from mag.agent_cli import api_agent_reset, api_agent_turn

    data = body or {}
    session_id = str(data.get("session_id") or "dashboard").strip() or "dashboard"
    # Reset only (no model call)
    if data.get("reset_only") or (data.get("reset") and not str(data.get("goal") or "").strip()):
        try:
            return 200, api_agent_reset(session_id)
        except Exception as e:
            return 500, {"ok": False, "error": str(e)}
    goal = str(data.get("goal") or data.get("question") or data.get("q") or "").strip()
    if not goal:
        return 400, {"ok": False, "error": "goal required"}
    provider = str(data.get("provider") or "deepseek").strip() or "deepseek"
    model = str(data.get("model") or "").strip() or None
    reset = bool(data.get("reset"))
    try:
        res = api_agent_turn(
            goal,
            provider=provider,
            model=model,
            session_id=session_id,
            reset=reset,
        )
        return 200, res
    except Exception as e:
        return 500, {"ok": False, "error": str(e)}


def h_post_agent_upload(_p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    """Save pasted/dropped image or text blob under memory/agent_uploads/ (Grok-compose steal)."""
    import base64
    import re
    from datetime import datetime, timezone

    data = body or {}
    name = str(data.get("filename") or "paste.bin")
    name = re.sub(r"[^\w.\-]+", "_", name)[:80]
    b64 = data.get("data") or data.get("base64") or ""
    if isinstance(b64, str) and "," in b64 and b64.strip().startswith("data:"):
        b64 = b64.split(",", 1)[1]
    if not b64:
        return 400, {"ok": False, "error": "data (base64) required"}
    try:
        raw = base64.b64decode(b64)
    except Exception as e:
        return 400, {"ok": False, "error": f"bad base64: {e}"}
    if len(raw) > 12 * 1024 * 1024:
        return 400, {"ok": False, "error": "max 12MB"}
    up = ROOT / "memory" / "agent_uploads"
    up.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = up / f"{ts}_{name}"
    path.write_bytes(raw)
    rel = str(path.relative_to(ROOT)).replace("\\", "/")
    meta: dict[str, Any] = {
        "ok": True,
        "path": rel,
        "abs": str(path),
        "bytes": len(raw),
        "filename": name,
    }
    # image dimensions if possible
    try:
        from PIL import Image
        from io import BytesIO

        with Image.open(BytesIO(raw)) as im:
            meta["format"] = im.format
            meta["width"], meta["height"] = im.size
            meta["mode"] = im.mode
            meta["kind"] = "image"
            meta["chip"] = (
                f"Image — {im.format or '?'} · {im.size[0]}x{im.size[1]} · "
                f"{len(raw)/1024:.1f} KB · `{rel}`"
            )
            meta["attach_text"] = (
                f"[Image attachment — pixels not sent to model yet; path for tools]\n"
                f"path: {rel}\nformat: {im.format} size: {im.size[0]}x{im.size[1]} "
                f"({len(raw)} bytes)\n"
                f"Operator: describe what you need; agent can read path metadata via tools."
            )
    except Exception:
        meta["kind"] = "file"
        meta["chip"] = f"File — {name} · {len(raw)/1024:.1f} KB · `{rel}`"
        try:
            text = raw.decode("utf-8")
            meta["attach_text"] = f"[Attached file: {rel}]\n```\n{text[:12000]}\n```"
        except Exception:
            meta["attach_text"] = (
                f"[Binary file: {rel} · {len(raw)} bytes — not inlined; use tools if needed]"
            )
    return 200, meta


def h_context_pack(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    """Fresh context-pack + paste block for DeepSeek web / external seats."""
    import json as _json

    from mag.context_pack import build_context_pack, format_context_pack_text

    try:
        pack = build_context_pack(max_brief=900, max_live=500)
        text = format_context_pack_text(pack)
        try:
            md = ROOT / "memory" / "context_pack_latest.md"
            md.parent.mkdir(parents=True, exist_ok=True)
            md.write_text(text, encoding="utf-8")
            (ROOT / "memory" / "context_pack_latest.json").write_text(
                _json.dumps(pack, indent=2, default=str), encoding="utf-8"
            )
        except Exception:
            pass
        law = (
            "# Mag cold start (stateless decoder)\n"
            "You are a seat on my Mag boundary — not a new throne.\n"
            "LOAD the pack below. Residual DNA is on my disk, not this chat.\n"
            "- One job. Truth-only. Artifact > transcript. Chat is heat.\n"
            "- Pack+goal only. Do not invent keys/online status.\n"
            "- Confirm pack loaded (tip/leaves) in one short block, then do the goal.\n\n"
            "## MAG CONTEXT PACK\n"
        )
        paste = law + text
        if len(paste) > 14000:
            paste = paste[:13900] + "\n…[truncated for paste size]\n"
        return 200, {
            "ok": True,
            "text": text,
            "paste": paste,
            "chars": len(paste),
            "path": "memory/context_pack_latest.md",
            "tip": (pack.get("tip") or {}) if isinstance(pack, dict) else {},
        }
    except Exception as e:
        return 500, {"ok": False, "error": str(e)}


def h_tangents(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.tangent import list_tangents

    return 200, list_tangents(limit=30)


def h_post_tangent(_p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    """Queue a background tangent (janitor/Gemini). Optional immediate run."""
    from mag.tangent import enqueue, process_one

    data = body or {}
    prompt = str(data.get("prompt") or data.get("goal") or data.get("q") or "").strip()
    if not prompt:
        return 400, {"ok": False, "error": "prompt required"}
    provider = str(data.get("provider") or "").strip() or None
    run_now = bool(data.get("run", True))
    prefer_gemini = data.get("prefer_gemini")
    if prefer_gemini is None:
        prefer_gemini = True
    enq = enqueue(
        prompt,
        source=str(data.get("source") or "dashboard"),
        provider=provider,
        prefer_gemini=bool(prefer_gemini),
        run_async=bool(data.get("async")),
    )
    if not enq.get("ok"):
        return 400, enq
    if run_now and not data.get("async"):
        ran = process_one(str(enq.get("id")))
        return 200, {"ok": True, "queued": enq, "result": ran}
    return 200, enq


def h_post_tangent_process(_p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.tangent import process_queue, scan_live_for_tangents

    data = body or {}
    if data.get("scan_live"):
        scan_live_for_tangents(auto_run=False)
    return 200, process_queue(max_n=int(data.get("max_n") or 1))


def h_post_brief(_p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.brief_local import write_brief

    data = body or {}
    sid = (data.get("session_id") or data.get("session") or "").strip() or None
    use_llm = bool(data.get("use_llm", True))
    return 200, write_brief(sid, use_llm=use_llm)


def h_post_visual(_p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.visual_pack import write_visual_pack

    data = body or {}
    sid = (data.get("session_id") or data.get("session") or "").strip() or None
    return 200, write_visual_pack(sid)


def h_post_export(_p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    """On-demand PDF/visual from residual (export layer)."""
    from mag.biography import export_session_artifacts

    data = body or {}
    sid = (data.get("session_id") or data.get("session") or data.get("id") or "").strip()
    if not sid:
        return 400, {"ok": False, "error": "session_id required"}
    pdf = data.get("pdf")
    visual = data.get("visual")
    # defaults: pdf true if neither specified; allow explicit false
    if pdf is None and visual is None:
        pdf, visual = True, False
    else:
        pdf = bool(pdf) if pdf is not None else False
        visual = bool(visual) if visual is not None else False
    result = export_session_artifacts(sid, pdf=pdf, visual=visual)
    code = 200 if result.get("ok") else 404 if "not found" in str(result.get("error") or "") else 500
    return code, result


def h_post_multi_smoke(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    from models.multi_smoke import run_multi_smoke

    return 200, run_multi_smoke()


def h_post_probe_lanes(_p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    from models.probe import probe_all

    data = body or {}
    return 200, probe_all(include_l1_chat=bool(data.get("include_l1", True)))


def h_operator_os(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.operator_os import build_operator_os

    return 200, build_operator_os(refresh_pack=True)


def h_tapestry(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.tapestry import build_tapestry_pack, write_tapestry_pack

    # always rebuild from live residual (sample render stays fresh)
    pack = write_tapestry_pack()
    pack["ok"] = True
    return 200, pack


def h_post_tapestry(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    return h_tapestry(_p, _b)


def h_lattice_lab(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    """Pointer + inventory for test conspiracy lattice (Sovereign Mirror instrument)."""
    sm = (
        Path.home()
        / "Documents"
        / "projects"
        / "worktrees"
        / "sovereign-mirror-scaffold"
    )
    knots_dir = sm / "data" / "knots"
    preset_path = sm / "data" / "presets" / "conspiracy_lattice.json"
    knots: list[dict[str, str]] = []
    if knots_dir.is_dir():
        for p in sorted(knots_dir.glob("*.txt")):
            knots.append({"id": p.stem, "title": p.stem.replace("_", " ")})
    preset = _read_json(preset_path) or {}
    port = 8743
    open_url = f"http://127.0.0.1:{port}/?preset=conspiracy"
    return 200, {
        "ok": True,
        "instrument": "sovereign-mirror-scaffold",
        "role": "Lattice lab for multi-frame capture-loop exploration — not Mag DNA",
        "mag_home": "http://127.0.0.1:8765/",
        "open_url": open_url,
        "open_demo_url": f"http://127.0.0.1:{port}/?preset=demo",
        "start": (
            r'cd Documents\projects\worktrees\sovereign-mirror-scaffold; '
            r'.\scripts\start-dashboard.ps1 --port 8743'
        ),
        "preset": preset.get("id") or "conspiracy_lattice",
        "event_title": preset.get("event_title"),
        "default_stack": preset.get("default_stack") or [],
        "knots": knots,
        "n_knots": len(knots),
        "law": preset.get("law")
        or [
            "Not courtroom proof",
            "Rhyme is not identity",
            "Consent residual stays open",
        ],
        "page": "/static/lattice.html",
    }


def h_blast(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.blast import plant_status

    return 200, plant_status()


def h_post_blast(_p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    """Influence plant: start/stop/pause/resume/patch dials."""
    from mag.blast import (
        plant_status,
        start_blast,
        stop_blast,
        pause_blast,
        write_influence,
    )

    data = body or {}
    action = str(data.get("action") or data.get("cmd") or "").strip().lower()
    if action in ("start", "run"):
        return 200, start_blast(background=True)
    if action == "stop":
        return 200, stop_blast()
    if action == "pause":
        return 200, pause_blast(True)
    if action == "resume":
        return 200, pause_blast(False)
    if action in ("influence", "set", "patch", ""):
        patch = data.get("influence") if isinstance(data.get("influence"), dict) else data
        # strip control keys
        clean = {
            k: patch[k]
            for k in (
                "run",
                "paused",
                "focus",
                "notes",
                "dig_minutes",
                "max_tickets",
                "cycle_seconds",
                "scout_every_n_cycles",
                "max_cycles",
            )
            if k in patch
        }
        if clean:
            write_influence(clean, by="dashboard")
        return 200, plant_status()
    return 400, {"ok": False, "error": f"unknown action {action}"}


def h_post_blast_promote(_p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.improve import promote_apply, promote_reject

    data = body or {}
    cid = str(data.get("id") or data.get("candidate_id") or "").strip()
    if not cid:
        return 400, {"ok": False, "error": "id required"}
    if data.get("reject"):
        return 200, promote_reject(cid, reason=str(data.get("reason") or "dash reject"))
    return 200, promote_apply(cid, force_model=bool(data.get("force_model")))


# --- Orchestrator: sub-agent fleet (spawn / monitor / intervene) ---


def h_agents(p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    """List sub-agent tasks — default: running + recent (48h), not soak corpses."""
    from mag.orchestrator import TERMINAL, list_tasks_live
    from mag.seats import build_workers_summary

    scope = (p.get("scope") or "recent").strip().lower()
    if scope in ("all", "full"):
        tasks = list_tasks_live(limit=200)
        return 200, {
            "ok": True,
            "tasks": tasks,
            "count": len(tasks),
            "scope": "all",
            "note": "Full history including soak tests — prefer scope=recent",
        }
    w = build_workers_summary(recent_hours=48.0)
    tasks = w["running"] + w["recent"]
    # Enrich running rows with live phase when requested
    live = list_tasks_live(limit=30)
    live_map = {t.get("task_id"): t for t in live if t.get("status") not in TERMINAL}
    for t in tasks:
        lid = live_map.get(t.get("task_id"))
        if lid:
            t.update({k: lid[k] for k in ("phase", "heartbeat_age_s", "alive") if k in lid})
    return 200, {
        "ok": True,
        "tasks": tasks,
        "count": len(tasks),
        "scope": "recent",
        "archived_hidden": w.get("archived_hidden", 0),
        "layman": w.get("layman"),
    }


def h_agents_spawn(_p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    """Spawn a sub-agent process: {goal, provider?, model?, timeout?, tag?}."""
    from mag.orchestrator import spawn_task

    data = body or {}
    goal = str(data.get("goal") or data.get("question") or "").strip()
    if not goal:
        return 400, {"ok": False, "error": "goal required"}
    provider = str(data.get("provider") or "deepseek").strip() or "deepseek"
    model = str(data.get("model") or "").strip() or None
    try:
        timeout = max(60, min(int(data.get("timeout") or 900), 7200))
    except (TypeError, ValueError):
        timeout = 900
    tag = str(data.get("tag") or "").strip()
    try:
        task = spawn_task(goal, provider=provider, model=model, timeout=timeout, tag=tag)
        return 200, {"ok": True, "task": task}
    except Exception as e:
        return 500, {"ok": False, "error": str(e)}


def h_agent_one(p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    """Live task status incl. heartbeat age + agent-reported phase."""
    from mag.orchestrator import task_status

    t = task_status(p.get("id") or "")
    if not t:
        return 404, {"ok": False, "error": "no such task"}
    return 200, {"ok": True, "task": t}


def h_agent_kill(p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.orchestrator import kill_task

    res = kill_task(p.get("id") or "")
    return (200 if res.get("ok") else 404), res


def h_agent_log(p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.orchestrator import tail_log

    try:
        n = max(1, min(int(p.get("n") or 50), 500))
    except (TypeError, ValueError):
        n = 50
    text = tail_log(p.get("id") or "", n=n)
    return 200, {"ok": True, "log": text}


def h_agents_reap(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    from mag.orchestrator import reap_stale

    return 200, reap_stale()


def h_agents_heal(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    """Watchdog: mark dead-pid tasks died + re-spawn them (bounded retries)."""
    from mag.orchestrator import respawn_dead

    return 200, respawn_dead()


def h_agent_cmd(p: dict[str, str], body: dict[str, Any] | None) -> tuple[int, dict]:
    """Live intervention over the knot mailbox: {cmd: steer|pause|continue|escape, context?}."""
    from mag import pigeonhole as ph

    tid = p.get("id") or ""
    data = body or {}
    cmd = str(data.get("cmd") or "").strip().lower()
    if not tid:
        return 400, {"ok": False, "error": "task id required"}
    if cmd == "steer":
        ctx = str(data.get("context") or data.get("goal") or "").strip()
        if not ctx:
            return 400, {"ok": False, "error": "steer requires context"}
        ph.post_steer(tid, ctx)
        return 200, {"ok": True, "sent": "steer", "task_id": tid}
    if cmd in ("pause", "continue", "escape"):
        ph.post_cmd(tid, cmd)
        return 200, {"ok": True, "sent": cmd, "task_id": tid}
    return 400, {"ok": False, "error": "cmd must be steer|pause|continue|escape"}


def h_api_index(_p: dict[str, str], _b: dict[str, Any] | None) -> tuple[int, dict]:
    return 200, {
        "ok": True,
        "name": "Mag Resource Harness API",
        "version": "v1",
        "product": "Local OS for filed work + idea board; models load packs, not chat dumps",
        "primary": {
            "ideas": "Topic board — cards you still hold (model-as-OS working set)",
            "sessions": "Workdays filed as residual DNA",
            "home": "Been → now → next aggregate",
            "dispatch": "Route a goal to a seat with pack-first context",
        },
        "resources": {
            # --- Ideas (OS board) ---
            "GET /api/v1/ideas": "List cards (?status=open|held|done|parked & ?type=)",
            "POST /api/v1/ideas": "Create card {title, type?, status?, body?}",
            "GET /api/v1/ideas/{id}": "One card + 1-hop neighborhood",
            "PATCH /api/v1/ideas/{id}": "Update status/title/body/tags (done, shelf, reopen)",
            "GET /api/v1/ideas/{id}/pack": "LOAD brief for models / Chat",
            "POST /api/v1/ideas/seed": "Import open items from working notes",
            # --- Days / sessions ---
            "GET /api/v1/sessions": "Workdays list",
            "GET /api/v1/sessions/{id}": "Day detail",
            "GET /api/v1/sessions/{id}/residual": "Residual DNA JSON",
            "GET /api/v1/sessions/{id}/visual": "Visual pack if derived",
            "GET /api/v1/home": "Office summary (tip, bead, open ideas, economy)",
            "GET /api/v1/diary": "Day-by-day narrative spine",
            "GET /api/v1/story": "Thesis / journey / artifacts",
            "GET /api/v1/story/file?path=": "Text artifact under Mag root",
            # --- Body / router ---
            "GET /api/v1/health": "Is the lab up?",
            "GET /api/v1/nervous": "Containment glance (no secrets)",
            "GET /api/v1/grove": "Tesuji Grove nodes ?limit=20&refresh=1",
            "GET /api/v1/status": "Router: providers, quota, honesty",
            "GET /api/v1/providers": "Provider status",
            "GET /api/v1/quota": "Quota budgets",
            "GET /api/v1/economy": "Token savings snapshot",
            "GET /api/v1/chain": "Verkle tip + chain",
            "GET /api/v1/overview": "Aggregate dashboard payload",
            "GET /api/v1/board": "Ops board snapshot",
            "GET /api/v1/brief": "Latest brief",
            "GET /api/v1/tapestry": "3D connection graph pack",
            "POST /api/v1/tapestry/rebuild": "Rebuild tapestry from residual",
            "POST /api/v1/dispatch": "Classify seat + run (pack-first)",
            "POST /api/v1/ask": "Local biographer ask",
            "POST /api/v1/catch-up": "Watch + amend live board",
            "POST /api/v1/export": "PDF/visual from residual",
            "GET /api/v1/blast": "Background improve plant",
            "POST /api/v1/blast": "Plant control (start|stop|…)",
            # --- Sub-agent fleet (orchestrator) ---
            "GET /api/v1/agents": "List sub-agent tasks (newest first)",
            "POST /api/v1/agents": "Spawn sub-agent {goal, provider?, model?, timeout?, tag?}",
            "GET /api/v1/agents/{id}": "Live task status (heartbeat age, phase)",
            "GET /api/v1/agents/{id}/log": "Tail task log ?n=50",
            "POST /api/v1/agents/{id}/kill": "Kill task (process tree)",
            "POST /api/v1/agents/{id}/cmd": "Live knot cmd: steer|pause|continue|escape",
            "POST /api/v1/agents/reap": "Mark dead-pid tasks as died",
            "POST /api/v1/agents/heal": "Watchdog: mark dead died + auto-respawn (bounded)",
            "GET /api/v1/seats": "Inbound + outbound seats + live registered external seats",
            "POST /api/v1/seats/register": "Register desktop/cloud seat → MAG_TASK_ID",
            "POST /api/v1/seats/heartbeat": "Refresh registered seat liveness",
            "POST /api/v1/seats/unregister": "Mark registered seat done/failed",
            "GET /api/v1/power": "Stack status — kill switch / turn-on glance",
            "POST /api/v1/power/stop": "Kill switch — stop entire Mag stack",
            "POST /api/v1/power/start": "Turn-on — boot supervisor + core services",
            "POST /api/v1/improve/cloud": "Cloud handoff JSON → behavioral + optional queue",
            "POST /api/v1/improve/cycle": "Improve cycle → queue + nervous + spider",
            "GET /api/v1/governance": "Steering + behavioral loop + autonomy prefs",
            "POST /api/v1/governance": "Toggle drainer/behavioral pack or broadcast steer",
            "GET /api/v1/operator-inbox": "Deferred guidance queue (process at checkpoint)",
            "POST /api/v1/operator-inbox": "Queue guidance {text} or clear pending",
            "GET /api/v1/seat-feed": "Unified activity feed (Grok/Cursor/agent/orchestrator)",
            "GET /api/v1/chronicle": "File-backed pulse (attention + fleet + sources)",
            "POST /api/v1/seat/task": "Cursor→Mag task {goal?, seat?, mode: delegate|queue|autopilot|agent|dispatch}",
            "GET /api/v1/viewports": "Cursor Canvas manifests (synced viewports)",
            "GET /api/v1/viewports/{id}": "One canvas viewport manifest",
            "POST /api/v1/viewports/sync": "Sync *.canvas.tsx → memory/viewports/",
        },
        "conventions": {
            "envelope": "{ ok: true|false, ... } — errors use real HTTP 4xx/5xx",
            "truth": "Files under memory/ are source of truth; API is a viewport",
            "legacy": "Bare /api/* aliases still route; prefer /api/v1/*",
        },
    }


# (method, pattern, handler) — pattern uses {id} etc.
ROUTES: list[tuple[str, str, HandlerFn]] = [
    ("GET", "/api/v1/fleet/triad", h_fleet_triad),
    ("GET", "/api/v1", h_api_index),
    ("GET", "/api/v1/", h_api_index),
    ("GET", "/api/v1/operator-os", h_operator_os),
    ("GET", "/api/v1/org-review", h_operator_os),
    ("GET", "/api/v1/tapestry", h_tapestry),
    ("POST", "/api/v1/tapestry/rebuild", h_post_tapestry),
    ("GET", "/api/v1/lattice-lab", h_lattice_lab),
    ("GET", "/api/v1/health", h_health),
    ("GET", "/api/v1/doctor", h_health),
    ("GET", "/api/v1/mag-os", h_mag_os),
    ("GET", "/api/v1/os", h_mag_os),
    ("GET", "/api/v1/kpi", h_kpi),
    ("GET", "/api/v1/registry", h_registry),
    ("GET", "/api/v1/sessions", h_sessions),
    ("GET", "/api/v1/sessions/{id}", h_session),
    ("GET", "/api/v1/sessions/{id}/residual", h_session_residual),
    ("GET", "/api/v1/sessions/{id}/visual", h_visual),
    ("GET", "/api/v1/board", h_board),
    ("GET", "/api/v1/chain", h_chain),
    ("GET", "/api/v1/ingest", h_ingest),
    ("GET", "/api/v1/overview", h_overview),
    ("GET", "/api/v1/nervous", h_nervous),
    ("GET", "/api/nervous", h_nervous),
    ("GET", "/api/v1/grove", h_grove),
    ("GET", "/api/grove", h_grove),
    ("GET", "/api/v1/lattice-history", h_lattice_history),
    ("GET", "/api/lattice-history", h_lattice_history),
    ("GET", "/api/v1/viewports", h_viewports),
    ("GET", "/api/v1/viewports/{id}", h_viewport_one),
    ("POST", "/api/v1/viewports/sync", h_viewports_sync),

    ("GET", "/api/v1/home", h_home_summary),
    ("GET", "/api/v1/summary", h_home_summary),
    # Ideas — primary OS board (collection + item + pack + seed)
    ("GET", "/api/v1/ideas", h_ideas),
    ("POST", "/api/v1/ideas", h_ideas_create),
    ("GET", "/api/v1/ideas/{id}/pack", h_idea_pack),  # before {id}
    ("GET", "/api/v1/ideas/{id}", h_idea_one),
    ("PATCH", "/api/v1/ideas/{id}", h_idea_patch),
    ("POST", "/api/v1/ideas/seed", h_ideas_seed),
    ("GET", "/api/v1/models", h_models),
    ("GET", "/api/v1/providers", h_providers),
    ("GET", "/api/v1/quota", h_quota),
    ("GET", "/api/v1/router-status", h_router_status),
    ("GET", "/api/v1/status", h_router_status),
    ("GET", "/api/v1/diary", h_diary),
    ("GET", "/api/v1/story", h_story),
    ("GET", "/api/v1/story/file", h_story_file),
    ("GET", "/api/v1/usage", h_usage),
    ("GET", "/api/v1/economy", h_economy),
    ("GET", "/api/v1/flow", h_idea_flow),
    ("GET", "/api/v1/brief", h_brief_latest),
    ("GET", "/api/v1/visual/latest", lambda p, b: h_visual({**p, "id": "latest"}, b)),
    ("POST", "/api/v1/catch-up", h_post_catch_up),
    ("POST", "/api/v1/ask", h_post_ask),
    ("POST", "/api/v1/dispatch", h_post_dispatch),
    ("POST", "/api/v1/agent", h_post_agent),
    ("POST", "/api/agent", h_post_agent),
    ("POST", "/api/v1/agent/upload", h_post_agent_upload),
    ("POST", "/api/agent/upload", h_post_agent_upload),
    ("GET", "/api/v1/context-pack", h_context_pack),
    ("GET", "/api/context-pack", h_context_pack),
    ("GET", "/api/v1/tangents", h_tangents),
    ("POST", "/api/v1/tangent", h_post_tangent),
    ("POST", "/api/v1/tangent/process", h_post_tangent_process),
    ("POST", "/api/v1/brief", h_post_brief),
    ("POST", "/api/v1/visual", h_post_visual),
    ("POST", "/api/v1/export", h_post_export),
    ("POST", "/api/v1/multi-smoke", h_post_multi_smoke),
    ("POST", "/api/v1/probe-lanes", h_post_probe_lanes),
    ("GET", "/api/v1/blast", h_blast),
    ("POST", "/api/v1/blast", h_post_blast),
    ("POST", "/api/v1/blast/promote", h_post_blast_promote),
    # Orchestrator — sub-agent fleet (spawn + monitor + intervene)
    ("GET", "/api/v1/agents", h_agents),
    ("POST", "/api/v1/agents", h_agents_spawn),
    ("POST", "/api/v1/agents/reap", h_agents_reap),
    ("POST", "/api/v1/agents/heal", h_agents_heal),
    ("GET", "/api/v1/agents/{id}", h_agent_one),
    ("GET", "/api/v1/agents/{id}/log", h_agent_log),
    ("POST", "/api/v1/agents/{id}/kill", h_agent_kill),
    ("POST", "/api/v1/agents/{id}/cmd", h_agent_cmd),
    # Tripartite Chronicle (Synthesis Agent running commentary)
    ("GET", "/api/v1/chronicle", h_chronicle),
    ("GET", "/api/v1/seats", h_seats),
    ("POST", "/api/v1/seats/register", h_seats_register),
    ("POST", "/api/v1/seats/heartbeat", h_seats_heartbeat),
    ("POST", "/api/v1/seats/unregister", h_seats_unregister),
    ("GET", "/api/v1/power", h_power),
    ("POST", "/api/v1/power/stop", h_power_stop),
    ("POST", "/api/v1/power/start", h_power_start),
    ("POST", "/api/v1/improve/cloud", h_improve_cloud),
    ("POST", "/api/v1/improve/cycle", h_improve_cycle),
    ("GET", "/api/v1/governance", h_governance),
    ("POST", "/api/v1/governance", h_post_governance),
    ("GET", "/api/v1/operator-inbox", h_operator_inbox),
    ("POST", "/api/v1/operator-inbox", h_operator_inbox),
    ("GET", "/api/v1/seat-feed", h_seat_feed),
    ("GET", "/api/v1/coordination", h_coordination),
    ("POST", "/api/v1/coordination", h_coordination_post),
    ("POST", "/api/v1/coordinate", h_coordinate),
    ("POST", "/api/v1/route", h_route),
    ("GET", "/api/v1/route", h_route),
    ("POST", "/api/v1/decide", h_decide),
    ("GET", "/api/v1/decide", h_decide),
    ("GET", "/api/v1/drainer", h_drainer_status),
    ("POST", "/api/v1/drainer", h_drainer_toggle),
    ("GET", "/api/v1/workspace/tree", h_workspace_tree),
    ("GET", "/api/v1/workspace/file", h_workspace_file_get),
    ("POST", "/api/v1/workspace/file", h_workspace_file_post),
    ("POST", "/api/v1/autopilot", h_autopilot),
    ("POST", "/api/v1/orchestrator/queue", h_orchestrator_queue_post),
    ("POST", "/api/v1/seat/task", h_seat_task),
]

# Legacy aliases → same handlers (compat for existing UI)
LEGACY: list[tuple[str, str, HandlerFn]] = [
    ("GET", "/api/operator-os", h_operator_os),
    ("GET", "/api/org-review", h_operator_os),
    ("GET", "/api/health", h_health),
    ("GET", "/api/doctor", h_health),
    ("GET", "/api/mag-os", h_mag_os),
    ("GET", "/api/os", h_mag_os),
    ("GET", "/api/sessions", h_sessions),
    ("GET", "/api/session/{id}", h_session),
    ("GET", "/api/board", h_board),
    ("GET", "/api/verkle", h_chain),
    ("GET", "/api/ingest", h_ingest),
    ("GET", "/api/overview", h_overview),
    ("GET", "/api/home", h_home_summary),
    ("GET", "/api/diary", h_diary),
    ("GET", "/api/story", h_story),
    ("GET", "/api/summary", h_home_summary),
    ("GET", "/api/models", h_models),
    ("GET", "/api/providers", h_providers),
    ("GET", "/api/quota", h_quota),
    ("GET", "/api/usage", h_usage),
    ("GET", "/api/economy", h_economy),
    ("GET", "/api/idea-flow", h_idea_flow),
    ("GET", "/api/brief/latest", h_brief_latest),
    ("GET", "/api/visual/latest", lambda p, b: h_visual({**p, "id": "latest"}, b)),
    ("GET", "/api/visual/{id}", h_visual),
    ("GET", "/api/timeline", lambda p, b: (200, {"rows": _read_jsonl(BIO / "knot_timeline.jsonl")})),
    ("POST", "/api/catch-up", h_post_catch_up),
    ("POST", "/api/ask", h_post_ask),
    ("POST", "/api/dispatch", h_post_dispatch),
    ("GET", "/api/tangents", h_tangents),
    ("POST", "/api/tangent", h_post_tangent),
    ("POST", "/api/tangent/process", h_post_tangent_process),
    ("POST", "/api/brief", h_post_brief),
    ("POST", "/api/visual/rebuild", h_post_visual),
    ("POST", "/api/export", h_post_export),
    ("POST", "/api/multi-smoke", h_post_multi_smoke),
    ("POST", "/api/probe-lanes", h_post_probe_lanes),
    ("GET", "/api/blast", h_blast),
    ("POST", "/api/blast", h_post_blast),
    ("POST", "/api/blast/promote", h_post_blast_promote),
    ("GET", "/api/chronicle", h_chronicle),
    ("GET", "/api/seats", h_seats),
    ("GET", "/api/governance", h_governance),
    ("POST", "/api/governance", h_post_governance),
    ("GET", "/api/operator-inbox", h_operator_inbox),
    ("POST", "/api/operator-inbox", h_operator_inbox),
    ("GET", "/api/seat-feed", h_seat_feed),
    ("GET", "/api/drainer", h_drainer_status),
    ("POST", "/api/drainer", h_drainer_toggle),
    ("GET", "/api/workspace/tree", h_workspace_tree),
    ("GET", "/api/workspace/file", h_workspace_file_get),
    ("POST", "/api/workspace/file", h_workspace_file_post),
    ("POST", "/api/autopilot", h_autopilot),
    ("POST", "/api/orchestrator/queue", h_orchestrator_queue_post),
    ("POST", "/api/seat/task", h_seat_task),
]


def _compile(pattern: str) -> tuple[re.Pattern[str], list[str]]:
    names: list[str] = []

    def repl(m: re.Match[str]) -> str:
        names.append(m.group(1))
        return r"([^/]+)"

    rx = re.sub(r"\{(\w+)\}", repl, pattern)
    return re.compile("^" + rx + "$"), names


_COMPILED: list[tuple[str, re.Pattern[str], list[str], HandlerFn]] = []
for method, pat, fn in ROUTES + LEGACY:
    cre, names = _compile(pat)
    _COMPILED.append((method, cre, names, fn))


def dispatch(
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    query: dict[str, str] | None = None,
) -> tuple[int, dict[str, Any]] | None:
    """Return (status, json_body) or None if no route matched.

    Path params win over query for the same key. Query enables
    RESTful filters: GET /api/v1/ideas?status=open
    """
    for m, cre, names, fn in _COMPILED:
        if m != method:
            continue
        match = cre.match(path)
        if not match:
            continue
        params: dict[str, str] = dict(query or {})
        for i, name in enumerate(names):
            params[name] = match.group(i + 1)
        try:
            return fn(params, body)
        except Exception as e:
            return 500, {"ok": False, "error": str(e)[:400]}
    return None
