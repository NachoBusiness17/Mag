"""ASCII table view — DF/roguelike projection of engine state.

Schema: mag_table_view.v1
Law: glyphs only from campaign/scene — never LLM geometry.
"""
from __future__ import annotations

from typing import Any

SCHEMA = "mag_table_view.v1"
W, H = 23, 13  # odd sizes so center is clean

LEGEND = {
    "#": "wall",
    ".": "floor",
    "@": "you",
    "g": "foe",
    "+": "door/exit",
    "≈": "hook/prop",
    "<": "exit west cue",
    ">": "exit east cue",
    "^": "exit north cue",
    "v": "exit south cue",
    " ": "void",
}


def _blank() -> list[list[str]]:
    g = [[" " for _ in range(W)] for _ in range(H)]
    return g


def _carve_room(g: list[list[str]]) -> None:
    # inner chamber
    x0, x1 = 2, W - 3
    y0, y1 = 2, H - 3
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            g[y][x] = "."
    for x in range(x0 - 1, x1 + 2):
        g[y0 - 1][x] = "#"
        g[y1 + 1][x] = "#"
    for y in range(y0 - 1, y1 + 2):
        g[y][x0 - 1] = "#"
        g[y][x1 + 1] = "#"


def _doors(g: list[list[str]], exits: list[str] | None) -> None:
    exits = [str(e).lower() for e in (exits or [])]
    cx, cy = W // 2, H // 2
    x0, x1 = 2, W - 3
    y0, y1 = 2, H - 3
    if any(e in ("north", "n", "up") for e in exits):
        g[y0 - 1][cx] = "+"
        if cy - 2 >= 0:
            g[1][cx] = "^"
    if any(e in ("south", "s", "down", "deeper") for e in exits):
        g[y1 + 1][cx] = "+"
        if H - 2 < H:
            g[H - 2][cx] = "v"
    if any(e in ("east", "e", "right") for e in exits):
        g[cy][x1 + 1] = "+"
        g[cy][W - 2] = ">"
    if any(e in ("west", "w", "left", "back") for e in exits):
        g[cy][x0 - 1] = "+"
        g[cy][1] = "<"
    if any(e in ("woods", "side") for e in exits):
        # side path — punch east-south corner-ish
        g[y1 + 1][x1 - 2] = "+"
        g[H - 2][x1 - 2] = "v"


def _rows(g: list[list[str]]) -> list[str]:
    return ["".join(row) for row in g]


def build_view_from_scene(
    scene: dict[str, Any] | None,
    *,
    legal: list[dict[str, Any]] | None = None,
    campaign_id: str = "",
    room_id: str = "",
    status: str = "",
) -> dict[str, Any]:
    """Build ASCII grid from scene_context-like dict."""
    sc = scene or {}
    g = _blank()
    has_room = bool(sc.get("room_name") or sc.get("room_desc"))

    if not has_room:
        # void field — intentional DF-ish empty
        for y in range(H):
            for x in range(W):
                g[y][x] = "." if 0 < y < H - 1 and 0 < x < W - 1 else "#"
        msg = "no campaign — classic one"
        mid = H // 2
        start = max(1, (W - len(msg)) // 2)
        for i, ch in enumerate(msg[: W - 2]):
            g[mid][start + i] = ch
        grid = _rows(g)
        return {
            "ok": True,
            "schema": SCHEMA,
            "skin": "ascii",
            "w": W,
            "h": H,
            "grid": grid,
            "grid_text": "\n".join(grid),
            "legend": LEGEND,
            "scene": sc,
            "legal": legal or [],
            "campaign_id": campaign_id,
            "room_id": room_id,
            "status": status or "void",
            "title": "Void",
        }

    _carve_room(g)
    exits = sc.get("exits") or []
    if not exits and legal:
        exits = [a.get("direction") for a in legal if a.get("type") == "move" and a.get("direction")]
    _doors(g, list(exits) if isinstance(exits, list) else [])

    cx, cy = W // 2, H // 2
    # hook prop slightly off center
    if sc.get("hook"):
        g[cy + 1][cx - 2] = "≈"
        g[cy + 1][cx - 1] = "≈"
    enc = sc.get("encounter") or {}
    if enc and int(enc.get("hp") or 0) > 0:
        g[cy][cx + 2] = "g"
    g[cy][cx] = "@"

    grid = _rows(g)
    title = str(sc.get("room_name") or room_id or "Room")
    out = {
        "ok": True,
        "schema": SCHEMA,
        "skin": "ascii",
        "w": W,
        "h": H,
        "grid": grid,
        "grid_text": "\n".join(grid),
        "legend": LEGEND,
        "scene": {
            "room_name": sc.get("room_name"),
            "room_desc": sc.get("room_desc"),
            "hook": sc.get("hook"),
            "exits": sc.get("exits"),
            "player": sc.get("player"),
            "encounter": sc.get("encounter"),
            "flags": sc.get("flags"),
        },
        "legal": legal or sc.get("legal") or [],
        "campaign_id": campaign_id,
        "room_id": room_id,
        "status": status or "active",
        "title": title,
    }
    try:
        from mag.training_events import emit

        emit(
            "table_view",
            join={"campaign_id": campaign_id or "", "room_id": room_id or ""},
            action={"skin": "ascii", "title": title[:80]},
            outcome={"has_encounter": bool(enc and int(enc.get("hp") or 0) > 0)},
            pattern_tags=["game", "table", "ascii", "rest"],
            tier_max="T1",
            exportable=False,
        )
    except Exception:
        pass
    return out


def _session_aliases(session_id: str) -> list[str]:
    """Table UI session vs lane-prefixed voice sessions (vlane-dig-…)."""
    import re

    raw = (session_id or "").strip()
    if not raw:
        return []
    out: list[str] = []
    seen: set[str] = set()

    def add(s: str) -> None:
        s = (s or "").strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)

    add(raw)
    base = raw
    for p in (
        "vlane-voice-",
        "vlane-dig-",
        "vlane-code-",
        "vlane-harness-",
        "vlane-janitor-",
    ):
        if base.startswith(p):
            base = base[len(p) :]
            break
    base = re.sub(r"[^a-zA-Z0-9_-]+", "", base)[:48] or base
    add(base)
    for p in (
        "vlane-voice-",
        "vlane-dig-",
        "vlane-code-",
        "vlane-harness-",
        "vlane-janitor-",
    ):
        add(p + base)
    return out


def build_view(
    *,
    session_id: str = "",
    campaign_id: str = "",
) -> dict[str, Any]:
    """LOAD campaign for session and project ASCII view."""
    from mag.game_campaign import latest_for_session, list_legal_actions, load_campaign, scene_context

    camp = None
    if campaign_id:
        camp = load_campaign(campaign_id)
    if not camp and session_id:
        for sid in _session_aliases(session_id):
            camp = latest_for_session(sid)
            if camp:
                break
    if not camp:
        return build_view_from_scene(None, status="void")

    sc = scene_context(camp) if camp.get("player") else {}
    legal = list_legal_actions(camp) if camp.get("player") else []
    return build_view_from_scene(
        sc,
        legal=legal,
        campaign_id=str(camp.get("campaign_id") or ""),
        room_id=str(camp.get("room_id") or ""),
        status=str(camp.get("status") or ""),
    )


def handle_table_view(body: dict[str, Any] | None = None, params: dict[str, str] | None = None) -> dict[str, Any]:
    body = body or {}
    params = params or {}
    sid = str(body.get("session_id") or params.get("session_id") or "")
    cid = str(body.get("campaign_id") or params.get("campaign_id") or "")
    return build_view(session_id=sid, campaign_id=cid)
