#!/usr/bin/env python3
"""Local Mag history dashboard — browse sessions, PDFs, Verkle, ingest.

  python main.py dashboard
  → http://127.0.0.1:8765/
"""
from __future__ import annotations

import json
import mimetypes
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from config import bind_host  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BIO = ROOT / "memory" / "biography"
INGEST = ROOT / "memory" / "ingest"
STATIC = Path(__file__).resolve().parent / "static"
DEFAULT_HOST = bind_host()
DEFAULT_PORT = 8765


def _read_json(path: Path) -> Any | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _read_jsonl(path: Path, limit: int = 500) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows[-limit:]


def _ensure_session(sessions: dict[str, dict[str, Any]], sid: str) -> dict[str, Any]:
    if sid not in sessions:
        sessions[sid] = {
            "session_id": sid,
            "title": sid[:12],
            "has_pdf": False,
            "has_md": False,
            "has_dossier": False,
            "has_visual": False,
        }
    return sessions[sid]


def list_sessions() -> list[dict[str, Any]]:
    """Index sessions — prefer lean registry (hot path), else residual/legacy scan."""
    sessions: dict[str, dict[str, Any]] = {}

    # Hot path: registry.jsonl
    try:
        from mag.registry import list_registry

        for reg in list_registry(limit=300):
            sid = reg.get("session_id")
            if not sid:
                continue
            row = _ensure_session(sessions, sid)
            row.update(
                {
                    "session_id": sid,
                    "title": reg.get("title") or sid[:12],
                    "one_liner": reg.get("one_liner") or "",
                    "blurb": reg.get("blurb") or "",
                    "bullets": reg.get("bullets") or [],
                    "start_minute": reg.get("start_minute"),
                    "end_minute": reg.get("end_minute"),
                    "duration_minutes": reg.get("duration_minutes"),
                    "dominant_theme": reg.get("dominant_theme"),
                    "chord_commitment": reg.get("chord_commitment"),
                    "tension_index": reg.get("tension_index"),
                    "has_pdf": bool(reg.get("has_pdf")),
                    "has_md": bool(reg.get("has_md")),
                    "has_dossier": bool(reg.get("has_residual")),
                    "has_visual": bool(reg.get("has_visual")),
                    "has_residual": bool(reg.get("has_residual")),
                    "has_leaf": bool(reg.get("has_leaf")),
                    "residual_hash": reg.get("residual_hash"),
                    "verkle_filename": reg.get("leaf_filename"),
                    "commit": reg.get("content_commit"),
                    "from_registry": True,
                }
            )
    except Exception:
        pass

    if BIO.is_dir():
        # residual/ + legacy dossiers fill gaps not in registry
        residual_dir = BIO / "residual"
        dossier_paths = list(BIO.glob("*.dossier.json"))
        if residual_dir.is_dir():
            dossier_paths.extend(residual_dir.glob("*.json"))
        for p in dossier_paths:
            if p.name.startswith("latest"):
                continue
            sid = p.stem if p.parent.name == "residual" else p.name.replace(
                ".dossier.json", ""
            )
            if sid in sessions and sessions[sid].get("blurb"):
                continue
            d = _read_json(p) or {}
            time = d.get("time") or {}
            chord = d.get("chord") or {}
            sk = d.get("scalar_knot") or {}
            row = _ensure_session(sessions, sid)
            card = d.get("session_card") or {}
            if not card.get("blurb"):
                try:
                    from mag.session_card import build_session_card

                    card = build_session_card(d)
                except Exception:
                    card = {}
            title = card.get("title") or time.get("title") or sid[:12]
            from mag.registry import find_derived

            row.update(
                {
                    "session_id": sid,
                    "title": title,
                    "one_liner": card.get("one_liner") or (d.get("tldr") or "")[:120],
                    "blurb": card.get("blurb") or d.get("tldr") or "",
                    "bullets": card.get("bullets") or [],
                    "start_minute": (time.get("created_at") or {}).get("iso_minute"),
                    "end_minute": (time.get("updated_at") or {}).get("iso_minute"),
                    "duration_minutes": sk.get("duration_minutes"),
                    "dominant_theme": card.get("dominant_theme")
                    or (sk.get("theme_vector") or {}).get("dominant"),
                    "chord_commitment": chord.get("commitment_hash"),
                    "tension_index": sk.get("tension_index"),
                    "has_pdf": find_derived(sid, "pdf") is not None,
                    "has_md": find_derived(sid, "md") is not None,
                    "has_dossier": True,
                    "has_residual": True,
                    "has_visual": find_derived(sid, "visual_pack") is not None,
                    "verkle_filename": (d.get("verkle_knot") or {}).get("filename"),
                    "commit": (d.get("content_commit") or {}).get("hex"),
                    "mtime": p.stat().st_mtime,
                }
            )

        for p in BIO.glob("*.pdf"):
            if p.name.startswith("latest"):
                continue
            sid = p.name.replace(".pdf", "")
            row = _ensure_session(sessions, sid)
            row["has_pdf"] = True
            row["mtime"] = max(row.get("mtime") or 0, p.stat().st_mtime)

        for p in BIO.glob("*.md"):
            if p.name.startswith("latest"):
                continue
            sid = p.name.replace(".md", "")
            if sid in ("index", "README"):
                continue
            row = _ensure_session(sessions, sid)
            row["has_md"] = True
            row["mtime"] = max(row.get("mtime") or 0, p.stat().st_mtime)
            # first line title fallback
            if row.get("title") in (None, sid[:12]):
                try:
                    head = p.read_text(encoding="utf-8", errors="replace")[:200]
                    for line in head.splitlines():
                        line = line.strip().lstrip("#").strip()
                        if line and len(line) > 3:
                            row["title"] = line[:80]
                            break
                except OSError:
                    pass

        for p in BIO.glob("*.visual_pack.json"):
            if p.name.startswith("latest"):
                continue
            sid = p.name.replace(".visual_pack.json", "")
            row = _ensure_session(sessions, sid)
            row["has_visual"] = True
            row["mtime"] = max(row.get("mtime") or 0, p.stat().st_mtime)
            vp = _read_json(p) or {}
            if vp.get("session_id"):
                row["session_id"] = sid
            if not row.get("commit") and vp.get("commit"):
                row["commit"] = vp.get("commit")
            en = vp.get("english") or {}
            if en.get("headline") and row.get("title") in (None, sid[:12]):
                row["title"] = str(en["headline"])[:80]

    # enrich from verkle chain
    for row_v in _read_jsonl(BIO / "verkle_chain.jsonl"):
        sid = row_v.get("session_id")
        if not sid:
            continue
        row = _ensure_session(sessions, sid)
        row["verkle_filename"] = row_v.get("filename")
        row["leaf_hash"] = row_v.get("leaf_hash")
        row["verkle_root_at"] = row_v.get("verkle_root")
        if row_v.get("start_minute"):
            row["start_minute"] = row_v.get("start_minute")
        if row_v.get("dominant_theme"):
            row["dominant_theme"] = row_v.get("dominant_theme")

    out = list(sessions.values())
    # Prefer clock fields; fall back to file mtime so incomplete sessions still sort
    def _sort_key(x: dict[str, Any]) -> str:
        if x.get("end_minute"):
            return str(x["end_minute"])
        if x.get("start_minute"):
            return str(x["start_minute"])
        mt = x.get("mtime") or 0
        try:
            from datetime import datetime, timezone

            return datetime.fromtimestamp(float(mt), tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
        except (TypeError, ValueError, OSError):
            return ""

    out.sort(key=_sort_key, reverse=True)
    return out


def api_overview() -> dict[str, Any]:
    tip = _read_json(BIO / "verkle_tip.json") or {}
    evo = _read_json(BIO / "topic_evolution.json") or {}
    catalog = _read_json(INGEST / "catalog.json") or {}
    sessions = list_sessions()
    latest_sid = None
    try:
        from mag.registry import get_latest_session_id

        latest_sid = get_latest_session_id()
    except Exception:
        latest_sid = None
    if not latest_sid and sessions:
        latest_sid = sessions[0].get("session_id")
    return {
        "ok": True,
        "root": str(ROOT),
        "session_count": len(sessions),
        "sessions": sessions[:100],
        "verkle_tip": tip,
        "topic_evolution": {
            "n_leaves": evo.get("n_leaves"),
            "verkle_root": evo.get("verkle_root"),
            "mean_theme_vector": evo.get("mean_theme_vector")
            if "mean_theme_vector" in evo
            else None,
            "series_tail": (evo.get("series") or [])[-20:],
            "theme_basis": evo.get("theme_basis"),
        },
        "ingest": {
            "count": catalog.get("count"),
            "roots": catalog.get("roots"),
            "items": list((catalog.get("items") or {}).values())[:200],
        },
        "latest": {
            "session_id": latest_sid,
            "pdf": "/files/biography/latest.pdf",
            "dossier": "/api/dossier/latest",
            "md": "/files/biography/latest.md",
            "knot": "/api/knot/latest",
        },
    }


def api_session(sid: str) -> dict[str, Any]:
    dossier = None
    try:
        from mag.registry import load_residual

        dossier = load_residual(sid)
    except Exception:
        dossier = None
    if not dossier:
        dossier = _read_json(BIO / f"{sid}.dossier.json")
    if not dossier and sid == "latest":
        dossier = _read_json(BIO / "latest.dossier.json")
        sid = (dossier or {}).get("session_id") or "latest"
    md_path = BIO / f"{sid}.md"
    md = md_path.read_text(encoding="utf-8", errors="replace") if md_path.is_file() else None
    try:
        from mag.registry import find_derived, residual_path

        pdf_p = find_derived(sid, "pdf")
        vis_p = find_derived(sid, "visual_pack")
        md_d = find_derived(sid, "md")
        res_p = residual_path(sid) if sid and sid != "latest" else None
        has_pdf = pdf_p is not None
        has_visual = vis_p is not None
        has_residual = bool(dossier) or (res_p is not None and res_p.is_file())
    except Exception:
        has_pdf = (BIO / f"{sid}.pdf").is_file()
        has_visual = (BIO / f"{sid}.visual_pack.json").is_file() or (
            sid == "latest" and (BIO / "latest.visual_pack.json").is_file()
        )
        has_residual = bool(dossier)
        pdf_p = BIO / f"{sid}.pdf" if has_pdf else None
        md_d = None
        res_p = BIO / f"{sid}.dossier.json" if (BIO / f"{sid}.dossier.json").is_file() else None

    if not md and md_d is not None and md_d.is_file():
        md = md_d.read_text(encoding="utf-8", errors="replace")

    knot_name = (dossier or {}).get("verkle_knot", {}).get("filename")
    knot = None
    if knot_name:
        knot = _read_json(BIO / "knots" / knot_name)
    card = (dossier or {}).get("session_card") if dossier else None
    if dossier and not (card or {}).get("blurb"):
        try:
            from mag.session_card import build_session_card

            card = build_session_card(dossier)
        except Exception:
            card = card or {}

    sk = (dossier or {}).get("scalar_knot") or {}
    stats = {
        "tension_index": sk.get("tension_index"),
        "Q_proxy": sk.get("Q_proxy"),
        "duration_minutes": sk.get("duration_minutes"),
        "dominant_theme": (card or {}).get("dominant_theme")
        or (sk.get("theme_vector") or {}).get("dominant"),
        "num_messages": ((dossier or {}).get("time") or {}).get("num_messages"),
        "num_chat_messages": ((dossier or {}).get("time") or {}).get("num_chat_messages"),
        "content_commit": ((dossier or {}).get("content_commit") or {}).get("hex"),
        "leaf": ((dossier or {}).get("verkle_knot") or {}).get("filename"),
    }

    # Prefer derived paths for exports; residual for data
    pdf_url = (
        f"/files/biography/derived/{sid}.pdf"
        if has_pdf
        else None
    )
    residual_url = (
        f"/files/biography/residual/{sid}.json"
        if has_residual
        else f"/api/v1/sessions/{sid}/residual"
    )
    return {
        "ok": bool(dossier or md or has_visual or has_pdf or has_residual),
        "session_id": sid,
        "dossier": dossier,
        "narrative_md": md,
        "session_card": card,
        "stats": stats,
        "has_residual": has_residual,
        "has_visual": has_visual,
        "has_pdf": has_pdf,
        "knot": knot,
        "links": {
            "pdf": pdf_url or f"/files/biography/{sid}.pdf",
            "residual": residual_url,
            "dossier_json": f"/files/biography/residual/{sid}.json"
            if has_residual
            else f"/files/biography/{sid}.dossier.json",
            "md": f"/files/biography/derived/{sid}.md"
            if md_d
            else f"/files/biography/{sid}.md",
            "visual": f"/api/visual/{sid}",
            "export": "/api/export",
            "assets": f"/files/biography/{sid}/assets/",
        },
    }


def safe_file(rel: str) -> Path | None:
    """Resolve path under ROOT/memory or STATIC only."""
    rel = unquote(rel).lstrip("/").replace("\\", "/")
    if ".." in rel.split("/"):
        return None
    # map /files/biography/... → memory/biography/...
    if rel.startswith("files/"):
        rel = "memory/" + rel[len("files/") :]
    if rel.startswith("static/"):
        candidate = STATIC / rel[len("static/") :]
    elif rel.startswith("memory/"):
        candidate = ROOT / rel
    else:
        return None
    try:
        candidate = candidate.resolve()
        root = ROOT.resolve()
        static = STATIC.resolve()
        if not (str(candidate).startswith(str(root)) or str(candidate).startswith(str(static))):
            return None
        if candidate.is_file():
            return candidate
    except OSError:
        return None
    return None


class Handler(BaseHTTPRequestHandler):
    server_version = "MagDashboard/1.0"

    def log_message(self, fmt: str, *args) -> None:
        # quieter
        print(f"[dash] {self.address_string()} {fmt % args}")

    def _json(self, code: int, obj: Any) -> None:
        body = json.dumps(obj, indent=2, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _bytes(self, code: int, data: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        if "pdf" in content_type:
            self.send_header("Content-Disposition", "inline")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            index = STATIC / "index.html"
            data = index.read_bytes()
            return self._bytes(200, data, "text/html; charset=utf-8")

        if path in ("/shell", "/shell.html"):
            sh = STATIC / "sovereign_shell.html"
            if not sh.is_file():
                return self._json(404, {"error": "sovereign shell not found"})
            return self._bytes(200, sh.read_bytes(), "text/html; charset=utf-8")

        if path.startswith("/static/"):
            f = safe_file(path.lstrip("/"))
            if not f:
                return self._json(404, {"error": "not found"})
            ctype = mimetypes.guess_type(str(f))[0] or "application/octet-stream"
            return self._bytes(200, f.read_bytes(), ctype)

        if path.startswith("/files/"):
            f = safe_file(path.lstrip("/"))
            if not f:
                return self._json(404, {"error": "not found", "path": path})
            ctype = mimetypes.guess_type(str(f))[0] or "application/octet-stream"
            return self._bytes(200, f.read_bytes(), ctype)

        # SSE live fleet stream (real-time dashboard, no polling)
        if path == "/api/v1/stream":
            return self._stream_fleet()

        # Prefer RESTful dispatch table (v1 + legacy aliases)
        if path.startswith("/api/"):
            from dashboard.rest import dispatch

            q = {k: (v[0] if v else "") for k, v in parse_qs(parsed.query).items()}
            # deprecated: GET catch-up → same as POST
            if path == "/api/catch-up":
                hit = dispatch("POST", "/api/v1/catch-up", None, q)
                if hit:
                    return self._json(hit[0], hit[1])
            hit = dispatch("GET", path, None, q)
            if hit:
                # normalize sessions list shape for old UI when using legacy path
                if path == "/api/sessions" and "sessions" in hit[1] and "count" in hit[1]:
                    return self._json(200, {"sessions": hit[1]["sessions"]})
                return self._json(hit[0], hit[1])

        # One-offs not yet fully moved into rest.py
        if path == "/api/dossier/latest":
            d = _read_json(BIO / "latest.dossier.json")
            return self._json(200, d or {"error": "no latest dossier"})

        if path == "/api/knot/latest":
            d = _read_json(BIO / "latest.knot.json")
            return self._json(200, d or {"error": "no latest knot"})

        if path == "/api/multi-smoke/latest":
            from models.multi_smoke import last_smoke

            s = last_smoke()
            return self._json(
                200, s or {"ok": False, "error": "no smoke yet — POST /api/multi-smoke"}
            )

        if path == "/api/usage-report":
            import json as _json

            prov_path = ROOT / "logs" / "provider_usage.jsonl"
            probe_path = ROOT / "logs" / "probe_status_latest.json"
            local_tok = remote_tok = 0
            local_c = remote_c = 0
            if prov_path.is_file():
                for line in prov_path.read_text(encoding="utf-8", errors="replace").splitlines():
                    if not line.strip():
                        continue
                    try:
                        r = _json.loads(line)
                    except _json.JSONDecodeError:
                        continue
                    p = r.get("provider") or "?"
                    tok = int(r.get("tokens") or 0)
                    c = int(r.get("calls") or 1)
                    if p == "ollama":
                        local_tok += tok
                        local_c += c
                    else:
                        remote_tok += tok
                        remote_c += c
            probe = _read_json(probe_path) if probe_path.is_file() else None
            return self._json(
                200,
                {
                    "ok": True,
                    "local": {"calls": local_c, "tokens": local_tok},
                    "remote": {"calls": remote_c, "tokens": remote_tok},
                    "grok_tui": "unknown — check xAI account UI",
                    "probe": probe,
                    "note": "Green providers = last probe ok, not merely key present.",
                },
            )

        if path == "/api/probe-status":
            p = ROOT / "logs" / "probe_status_latest.json"
            data = _read_json(p)
            return self._json(
                200,
                data
                or {
                    "ok": False,
                    "error": "no probe yet — POST /api/probe-status or run scripts/probe_status_cache.py",
                },
            )

        return self._json(404, {"error": "not found", "path": path})

    def _read_json_body(self) -> tuple[dict[str, Any] | None, str | None]:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        if not raw.strip():
            return {}, None
        try:
            data = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return None, "bad json"
        if not isinstance(data, dict):
            return None, "body must be a JSON object"
        return data, None

    def _remote_write_ok(self) -> bool:
        from mag.distributed_surface import check_write_auth

        ok, err = check_write_auth(dict(self.headers))
        if not ok:
            self._json(401, {"ok": False, "error": err or "unauthorized"})
            return False
        return True

    def do_POST(self) -> None:  # noqa: N802
        if not self._remote_write_ok():
            return
        parsed = urlparse(self.path)
        path = parsed.path
        data, err = self._read_json_body()
        if err:
            return self._json(400, {"ok": False, "error": err})

        if path == "/api/v1/agent/stream":
            return self._stream_agent(data or {})

        if path == "/api/v1/agent/steer":
            # Dashboard steer channel: push a !steer/!pause/!continue/!escape
            # into the live turn's queue (mag.agent_cli.push_steer). The running
            # run_turn picks it up at its next checkpoint.
            cmd = str((data or {}).get("cmd") or "").strip()
            if not cmd:
                return self._json(400, {"ok": False, "error": "cmd required"})
            try:
                from mag.agent_cli import push_steer
                queued = push_steer(cmd)
            except Exception as e:  # noqa: BLE001
                return self._json(500, {"ok": False, "error": str(e)})
            return self._json(200, {"ok": True, "queued": queued, "cmd": cmd})

        if path.startswith("/api/"):
            from dashboard.rest import dispatch

            q = {k: (v[0] if v else "") for k, v in parse_qs(parsed.query).items()}
            hit = dispatch("POST", path, data or {}, q)
            if hit:
                return self._json(hit[0], hit[1])

        if path == "/api/probe-status":
            # run live probe (can take ~minutes if many keys)
            import subprocess
            import sys

            script = ROOT / "scripts" / "probe_status_cache.py"
            try:
                subprocess.run(
                    [sys.executable, str(script)],
                    cwd=str(ROOT),
                    timeout=180,
                    check=False,
                    capture_output=True,
                )
            except Exception as e:
                return self._json(500, {"ok": False, "error": str(e)})
            out = _read_json(ROOT / "logs" / "probe_status_latest.json")
            return self._json(200, out or {"ok": False, "error": "probe produced no file"})

        return self._json(404, {"ok": False, "error": "not found", "path": path})

    def _stream_fleet(self) -> None:
        """Server-Sent Events: push the sub-agent fleet snapshot every 2s."""
        import json as _json
        import time as _time
        from mag.orchestrator import list_tasks_live

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        try:
            while True:
                tasks = list_tasks_live(limit=50)
                payload = _json.dumps({"type": "fleet", "tasks": tasks},
                                      ensure_ascii=False, default=str)
                self.wfile.write(("data: " + payload + "\n\n").encode("utf-8"))
                self.wfile.flush()
                _time.sleep(2)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            pass

    def _stream_agent(self, data: dict[str, Any]) -> None:
        """SSE: run one Mag agent turn, streaming deltas live, then a done event.

        POST /api/v1/agent/stream  {goal, provider, model, session_id, reset}
        Events:
          data: {"type":"delta","text":"..."}   -- streamed model text
          data: {"type":"tool","name":"...","args":"..."}  -- tool call trace
          data: {"type":"done","answer":"...","tools":[...],"provider":"...","ok":true}
          data: {"type":"error","error":"..."}
        """
        import json as _json

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        def _send(obj: dict[str, Any]) -> None:
            try:
                self.wfile.write(
                    ("data: " + _json.dumps(obj, ensure_ascii=False, default=str) + "\n\n").encode("utf-8")
                )
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                raise

        goal = str(data.get("goal") or data.get("question") or data.get("q") or "").strip()
        if not goal:
            _send({"type": "error", "error": "goal required"})
            return
        provider = str(data.get("provider") or "deepseek").strip() or "deepseek"
        model = str(data.get("model") or "").strip() or None
        session_id = str(data.get("session_id") or "dashboard").strip() or "dashboard"
        reset = bool(data.get("reset"))

        from mag.agent_cli import api_agent_turn

        def _on_stream(delta: str) -> None:
            _send({"type": "delta", "text": delta})

        def _on_status(ev: dict[str, Any]) -> None:
            _send(ev)

        try:
            res = api_agent_turn(
                goal,
                provider=provider,
                model=model,
                session_id=session_id,
                reset=reset,
                on_stream=_on_stream,
                on_status=_on_status,
            )
        except Exception as e:  # noqa: BLE001
            _send({"type": "error", "error": str(e)})
            return
        if not res.get("ok"):
            _send({"type": "error", "error": res.get("error") or "agent failed"})
            return
        _send(
            {
                "type": "done",
                "answer": res.get("answer") or "",
                "tools": res.get("tools") or [],
                "provider": res.get("provider") or provider,
                "model": res.get("model"),
                "session_id": res.get("session_id"),
                "tip": res.get("tip"),
                "n_messages": res.get("n_messages"),
            }
        )

    def do_PATCH(self) -> None:  # noqa: N802
        """RESTful partial update (ideas status, etc.)."""
        if not self._remote_write_ok():
            return
        parsed = urlparse(self.path)
        path = parsed.path
        data, err = self._read_json_body()
        if err:
            return self._json(400, {"ok": False, "error": err})
        if path.startswith("/api/"):
            from dashboard.rest import dispatch

            q = {k: (v[0] if v else "") for k, v in parse_qs(parsed.query).items()}
            hit = dispatch("PATCH", path, data or {}, q)
            if hit:
                return self._json(hit[0], hit[1])
        return self._json(404, {"ok": False, "error": "not found", "path": path})

    def do_OPTIONS(self) -> None:  # noqa: N802
        """CORS preflight for local tools (same-origin UI does not need this)."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Mag-Token")
        self.send_header("Content-Length", "0")
        self.end_headers()


def run(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    from config import print_bind_banner

    STATIC.mkdir(parents=True, exist_ok=True)
    httpd = ThreadingHTTPServer((host, port), Handler)
    print_bind_banner(host=host, port=port)
    print(f"  biography: {BIO}")
    print(f"  ingest:    {INGEST}")
    print("Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run()
