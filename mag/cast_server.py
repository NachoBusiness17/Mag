#!/usr/bin/env python3
"""Read-only cast receiver — Spotify-to-Roku style LAN pulse + optional voice POC.

Serves:
  GET /                   → server-rendered cast page (Roku-safe, meta refresh)
  GET /voice              → phone voice UI (Web Speech STT + TTS)
  GET /health             → instant ping
  GET /api/v1/display     → TV-safe JSON
  POST /api/v1/voice/turn → local janitor answer (narrow — no shell/desk control)

Default: 127.0.0.1:8766 — use --lan for WiFi receivers you point at manually.
"""
from __future__ import annotations

import html
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

STATIC = Path(__file__).resolve().parents[1] / "dashboard" / "static"
DEFAULT_PORT = 8766
REFRESH_SECONDS = 15

_ALLOWED = frozenset(
    {
        "/",
        "/cast.html",
        "/voice",
        "/control",
        "/health",
        "/api/v1/display",
        "/api/display",
        "/api/v1/voice/turn",
        "/api/v1/remote/status",
        "/api/v1/remote/intent",
    }
)

_CAST_CSS = """
:root { color-scheme: dark; font-family: system-ui, sans-serif; background: #0a0e14; color: #e6edf3; }
body { margin: 0; padding: 1.25rem; line-height: 1.45; }
h1 { font-size: 1.35rem; margin: 0 0 0.35rem; }
.muted { color: #8b949e; font-size: 0.9rem; }
.headline { font-size: 1.15rem; margin: 1rem 0; }
.events { margin-top: 1rem; }
.event { padding: 0.35rem 0; border-top: 1px solid #21262d; }
.pulse { display: inline-block; width: 0.55rem; height: 0.55rem; border-radius: 50%; background: #3fb950; margin-right: 0.35rem; vertical-align: middle; }
.pulse.thinking { background: #d29922; }
"""


def render_cast_page(payload: dict[str, Any]) -> str:
    """Server-rendered HTML — works on Roku / thin browsers (no JS required)."""
    lp = payload.get("local_pulse") or {}
    desk = payload.get("desk") or {}
    thinking = bool(lp.get("thinking"))
    status = html.escape(str(payload.get("status") or "—"))
    ts = html.escape(str(payload.get("ts") or ""))
    headline = html.escape(str(payload.get("headline") or "Mag pulse"))
    goal = html.escape(str(desk.get("goal") or ""))
    tail_bits = [html.escape(str(x)) for x in (desk.get("dialogue_tail") or [])[-2:]]
    desk_parts = [f"Goal: {goal}"] if goal else []
    desk_parts.extend(tail_bits)
    desk_line = " · ".join(desk_parts)
    events = "".join(
        f'<div class="event">{html.escape(str(e))}</div>' for e in (payload.get("events") or [])[:8]
    )
    pulse_cls = "thinking" if thinking else "idle"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta http-equiv="refresh" content="{REFRESH_SECONDS}" />
  <title>Mag Cast</title>
  <style>{_CAST_CSS}</style>
</head>
<body>
  <h1>Mag Cast</h1>
  <div class="muted"><span class="pulse {pulse_cls}"></span>{status} · {ts}</div>
  <div class="headline">{headline}</div>
  <div class="muted">{desk_line or "—"}</div>
  <div class="events">{events or '<div class="muted">No recent events</div>'}</div>
  <p class="muted" style="margin-top:1rem">Phone voice: <a href="/voice">/voice</a> (hold-to-talk)</p>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "MagCast/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path.startswith("/static/"):
            return self._static(path[len("/static/") :])
        if path not in _ALLOWED:
            self._json(404, {"ok": False, "error": "cast receiver — read-only routes only"})
            return
        if path == "/health":
            self._json(
                200,
                {
                    "ok": True,
                    "service": "mag-cast",
                    "voice": True,
                    "routes": ["GET /", "GET /voice", "POST /api/v1/voice/turn"],
                },
            )
            return
        if path == "/voice":
            return self._file(STATIC / "cast-voice.html", "text/html; charset=utf-8")
        if path == "/control":
            return self._file(STATIC / "control.html", "text/html; charset=utf-8")
        if path == "/api/v1/remote/status":
            from mag.remote_control import authorized, status, token_from_headers

            if not authorized(token_from_headers(self.headers)):
                self._json(401, {"ok": False, "error": "valid remote token required"})
                return
            self._json(200, status())
            return
        if path in ("/", "/cast.html"):
            from mag.display import build_display_payload

            page = render_cast_page(build_display_payload())
            raw = page.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self._cors()
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        if path in ("/api/v1/display", "/api/display"):
            from mag.display import build_display_payload

            self._json(200, build_display_payload())
            return

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path not in {"/api/v1/voice/turn", "/api/v1/remote/intent"}:
            self._json(405, {"ok": False, "error": "unsupported cast action"})
            return
        try:
            length = int(self.headers.get("Content-Length") or "0")
            raw = self.rfile.read(length) if length else b"{}"
            body = json.loads(raw.decode("utf-8") or "{}")
        except Exception as exc:
            self._json(400, {"ok": False, "error": f"bad JSON: {exc!s}"[:120]})
            return
        if path == "/api/v1/remote/intent":
            from mag.remote_control import authorized, submit_intent, token_from_headers

            if not authorized(token_from_headers(self.headers)):
                self._json(401, {"ok": False, "error": "valid remote token required"})
                return
            out = submit_intent(body)
            self._json(202 if out.get("ok") else 400, out)
            return

        from mag.voice_turn import handle_voice_turn

        out = handle_voice_turn(body)
        self._json(200 if out.get("ok") else 400, out)

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Mag-Token")

    def _json(self, code: int, body: dict[str, Any]) -> None:
        raw = json.dumps(body, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self._cors()
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _file(self, path: Path, content_type: str) -> None:
        if not path.is_file():
            self._json(404, {"ok": False, "error": "missing cast.html"})
            return
        raw = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self._cors()
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _static(self, rel: str) -> None:
        safe = Path(rel).name if rel else ""
        path = STATIC / safe
        if not path.is_file() or path.resolve().parent != STATIC.resolve():
            self._json(404, {"ok": False, "error": "not found"})
            return
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self._file(path, ctype)


def run(*, host: str = "127.0.0.1", port: int = DEFAULT_PORT) -> None:
    from config import print_bind_banner

    httpd = ThreadingHTTPServer((host, port), Handler)
    print_bind_banner(host=host, port=port, service="cast")
    print("  routes: GET / · GET /voice · POST /api/v1/voice/turn · GET /health")
    print(f"  auto-refresh every {REFRESH_SECONDS}s — Roku-safe (no JavaScript)")
    print("  no network discovery — type URL on receiver manually")
    print("Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run()
