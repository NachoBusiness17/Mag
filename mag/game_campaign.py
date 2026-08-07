"""Campaign engine — state/legal actions first; LLM narrates after.

Schema: mag_game_campaign.v1
Law: engine owns truth; character ask + save check; traits fire tables (CK-lite).
"""
from __future__ import annotations

import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from config import ROOT

SCHEMA = "mag_game_campaign.v1"
CAMP_DIR = ROOT / "memory" / "working" / "game_campaigns"
MODULES_DIR = ROOT / "memory" / "game_modules"
CHAR_DIR = ROOT / "memory" / "working" / "game_characters"

_ARCHETYPES = {
    "fighter": {"hp": 12, "hp_max": 12, "ac": 14, "attack_bonus": 4, "damage": "1d8+2"},
    "rogue": {"hp": 10, "hp_max": 10, "ac": 13, "attack_bonus": 5, "damage": "1d6+3"},
    "wizard": {"hp": 8, "hp_max": 8, "ac": 12, "attack_bonus": 3, "damage": "1d10"},
    "cleric": {"hp": 10, "hp_max": 10, "ac": 14, "attack_bonus": 3, "damage": "1d6+1"},
}
_TRAITS = ["greedy", "brave", "craven", "curious", "hotheaded", "cautious", "kind", "cynical"]


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cid() -> str:
    return "gc-" + uuid4().hex[:10]


def list_modules() -> list[dict[str, Any]]:
    out = []
    if not MODULES_DIR.is_dir():
        return out
    for p in MODULES_DIR.glob("*.json"):
        try:
            m = json.loads(p.read_text(encoding="utf-8"))
            out.append(
                {
                    "module_id": m.get("module_id") or p.stem,
                    "title": m.get("title"),
                    "aliases": m.get("aliases") or [],
                    "path": str(p.relative_to(ROOT)).replace("\\", "/"),
                }
            )
        except Exception:
            continue
    return out


def resolve_module(name: str) -> dict[str, Any] | None:
    q = (name or "classic").strip().lower()
    for p in MODULES_DIR.glob("*.json"):
        try:
            m = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        mid = str(m.get("module_id") or "").lower()
        aliases = [str(a).lower() for a in (m.get("aliases") or [])]
        title = str(m.get("title") or "").lower()
        if q == mid or q in aliases or any(q in a or a in q for a in aliases) or q in title:
            return m
    classic = MODULES_DIR / "dnd_classic_stub.v1.json"
    if classic.is_file():
        return json.loads(classic.read_text(encoding="utf-8"))
    return None


def _path(campaign_id: str) -> Path:
    return CAMP_DIR / f"{campaign_id}.json"


def load_campaign(campaign_id: str) -> dict[str, Any] | None:
    p = _path(campaign_id)
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_campaign(camp: dict[str, Any]) -> Path:
    CAMP_DIR.mkdir(parents=True, exist_ok=True)
    camp["updated"] = _utc()
    p = _path(str(camp["campaign_id"]))
    p.write_text(json.dumps(camp, indent=2, default=str), encoding="utf-8")
    return p


def latest_for_session(session_id: str) -> dict[str, Any] | None:
    if not CAMP_DIR.is_dir() or not session_id:
        return None
    best, best_ts = None, ""
    for p in CAMP_DIR.glob("gc-*.json"):
        try:
            c = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if str(c.get("voice_session_id") or "") != session_id:
            continue
        if c.get("status") not in ("active", "awaiting_character", "paused"):
            continue
        ts = str(c.get("updated") or c.get("ts") or "")
        if ts >= best_ts:
            best_ts, best = ts, c
    return best


def parse_character(text: str) -> dict[str, Any] | None:
    """Parse 'I'm Ash a greedy fighter' or 'random classic'."""
    t = (text or "").strip()
    if not t:
        return None
    low = t.lower()
    if re.search(r"\b(random|classic character|surprise me)\b", low):
        arch = random.choice(list(_ARCHETYPES.keys()))
        traits = random.sample(_TRAITS, 2)
        name = random.choice(["Ash", "Brynn", "Corin", "Dax", "Elra", "Fenn"])
        base = dict(_ARCHETYPES[arch])
        return {
            "name": name,
            "archetype": arch,
            **base,
            "traits": traits,
            "inventory": ["torch", "rations"],
        }
    # name patterns
    name = None
    m = re.search(
        r"\b(?:i(?:'m| am)|call me|name(?:'s| is)|play as)\s+([A-Za-z][A-Za-z'-]{1,20})",
        t,
        re.I,
    )
    if m:
        name = m.group(1)
    # Tavern Brawler (5e feat kit) — preferred for brawl dogfood
    # Do not treat leading word "tavern" as character name.
    if re.search(r"\btavern\s*brawler\b", low):
        from mag.game_brawl import tavern_brawler_sheet

        bad_names = {
            "tavern",
            "brawler",
            "the",
            "a",
            "an",
            "with",
            "fighter",
            "adventurer",
        }
        nm = name if name and name.lower() not in bad_names else "Ash"
        # "I'm Brynn a tavern brawler"
        m_nm = re.search(
            r"\b(?:i(?:'m| am)|call me|name(?:'s| is)|play as)\s+([A-Za-z][A-Za-z'-]{1,20})",
            t,
            re.I,
        )
        if m_nm and m_nm.group(1).lower() not in bad_names:
            nm = m_nm.group(1)
        traits_tb = [tr for tr in _TRAITS if tr in low] or ["hotheaded", "brave"]
        sheet = tavern_brawler_sheet(nm, traits=traits_tb[:3])
        # pick up gear words into inventory
        inv = list(sheet.get("inventory") or [])
        if re.search(r"\b(axe|hatchet)\b", low) and "axe" not in inv:
            inv.append("axe")
        if re.search(r"\b(mug|ale|tankard)\b", low) and "mug" not in inv:
            inv.append("mug of ale")
        sheet["inventory"] = inv
        return {k: v for k, v in sheet.items() if k not in ("id", "is_player", "faction", "ai")}
    if not name:
        m2 = re.match(r"^([A-Za-z][A-Za-z'-]{1,20})\b", t)
        if m2 and m2.group(1).lower() not in (
            "the",
            "go",
            "i",
            "a",
            "an",
            "tavern",
            "play",
        ):
            name = m2.group(1)

    arch = "fighter"
    for a in _ARCHETYPES:
        if a in low:
            arch = a
            break
    if "rogue" in low or "thief" in low:
        arch = "rogue"
    if "mage" in low or "wizard" in low:
        arch = "wizard"
    if "cleric" in low or "priest" in low:
        arch = "cleric"
    traits = [tr for tr in _TRAITS if tr in low]
    if not traits:
        traits = ["brave"]
    if not name and not re.search(r"\b(fighter|rogue|wizard|cleric|greedy|brave|tavern)\b", low):
        return None
    if not name:
        name = "Adventurer"
    base = dict(_ARCHETYPES[arch])
    return {
        "name": name[:40],
        "archetype": arch,
        **base,
        "traits": traits[:3],
        "inventory": ["torch", "rations"],
    }


def begin_play(
    *,
    module_id: str = "classic",
    voice_session_id: str = "",
    force_new: bool = False,
) -> dict[str, Any]:
    """Save check → resume or await character / start."""
    if not force_new and voice_session_id:
        existing = latest_for_session(voice_session_id)
        if existing and existing.get("status") in ("active", "paused"):
            if existing.get("status") == "paused":
                existing["status"] = "active"
                save_campaign(existing)
            return {
                "ok": True,
                "resumed": True,
                "campaign": existing,
                "speak": (
                    f"Resuming {existing.get('module_title')}: "
                    f"{(existing.get('player') or {}).get('name')} "
                    f"in {_room(existing).get('name')}. "
                    f"HP {(existing.get('player') or {}).get('hp')}/"
                    f"{(existing.get('player') or {}).get('hp_max')}. "
                    f"Say an action: go north, attack, look, help…"
                ),
                "legal": list_legal_actions(existing),
                "scene_context": scene_context(existing),
            }
        if existing and existing.get("status") == "awaiting_character":
            return {
                "ok": True,
                "need_character": True,
                "campaign_id": existing.get("campaign_id"),
                "speak": (
                    "Campaign ready. Who are you? "
                    "Say e.g. I'm Ash a greedy fighter — or random classic."
                ),
            }

    mod = resolve_module(module_id)
    if not mod:
        return {"ok": False, "error": "no module", "modules": list_modules()}

    cid = _cid()
    camp = {
        "schema": SCHEMA,
        "campaign_id": cid,
        "ts": _utc(),
        "voice_session_id": voice_session_id or "",
        "module_id": mod.get("module_id"),
        "module_title": mod.get("title"),
        "status": "awaiting_character",
        "room_id": mod.get("start_room"),
        "player": None,
        "encounter": None,
        "flags": [],
        "storyteller": {"threat_budget": 2, "days_since_crisis": 0},
        "log": [{"ts": _utc(), "type": "init", "text": f"Module {mod.get('title')} loaded"}],
        "module_snapshot": {
            "rooms": mod.get("rooms") or {},
            "event_tables": mod.get("event_tables") or {},
            "license_note": mod.get("license_note"),
            "player_start": mod.get("player_start") or {},
        },
    }
    save_campaign(camp)
    return {
        "ok": True,
        "resumed": False,
        "need_character": True,
        "campaign_id": cid,
        "campaign": camp,
        "speak": (
            f"Starting {mod.get('title')}. Who are you playing? "
            "Name and class/vibe — or say random classic."
        ),
    }


def set_character(campaign_id: str, player: dict[str, Any]) -> dict[str, Any]:
    camp = load_campaign(campaign_id)
    if not camp:
        return {"ok": False, "error": "missing campaign"}
    camp["player"] = player
    camp["status"] = "active"
    start = camp.get("room_id")
    rooms = (camp.get("module_snapshot") or {}).get("rooms") or {}
    room = rooms.get(start) or {}
    enc = room.get("encounter")
    if enc:
        camp["encounter"] = dict(enc)
    camp["log"] = list(camp.get("log") or []) + [
        {
            "ts": _utc(),
            "type": "character",
            "text": f"{player.get('name')} the {player.get('archetype')} "
            f"({', '.join(player.get('traits') or [])}) enters the road.",
        }
    ]
    # persist character sheet
    try:
        CHAR_DIR.mkdir(parents=True, exist_ok=True)
        cp = CHAR_DIR / f"{re.sub(r'[^a-z0-9]+', '-', str(player.get('name') or 'x').lower())}.json"
        cp.write_text(
            json.dumps({"player": player, "campaign_id": campaign_id, "ts": _utc()}, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass
    save_campaign(camp)
    sc = scene_context(camp)
    speak = f"Playing {player.get('name')} the {player.get('archetype')}. " + _narrate_room(camp)
    try:
        from mag.game_passage import narrate_passage, room_meta_from_camp

        pas = narrate_passage(
            sc,
            room_meta=room_meta_from_camp(camp),
            full=True,
            use_llm=True,
            last_action="arrive",
        )
        if pas.get("text"):
            speak = f"Playing {player.get('name')} the {player.get('archetype')}.\n\n" + str(
                pas["text"]
            )
    except Exception:
        pass
    return {
        "ok": True,
        "campaign": camp,
        "speak": speak,
        "legal": list_legal_actions(camp),
        "scene_context": sc,
    }


def _room(camp: dict[str, Any]) -> dict[str, Any]:
    rid = camp.get("room_id")
    return (camp.get("module_snapshot") or {}).get("rooms", {}).get(rid) or {}


def _narrate_room(camp: dict[str, Any]) -> str:
    room = _room(camp)
    parts = [f"You are in {room.get('name') or '?'}.", str(room.get("desc") or "")]
    hooks = room.get("hooks") or []
    if hooks:
        parts.append("Hook: " + str(hooks[0]))
    enc = camp.get("encounter")
    if enc and int(enc.get("hp") or 0) > 0:
        parts.append(f"Threat: {enc.get('name')} HP {enc.get('hp')}/{enc.get('hp_max')}.")
    exits = room.get("exits") or {}
    if exits:
        parts.append("Exits: " + ", ".join(exits.keys()) + ".")
    pl = camp.get("player") or {}
    if pl:
        parts.append(
            f"{pl.get('name')}: HP {pl.get('hp')}/{pl.get('hp_max')} "
            f"traits {', '.join(pl.get('traits') or [])}."
        )
    return " ".join(p for p in parts if p)


def scene_context(camp: dict[str, Any]) -> dict[str, Any]:
    """TinyStories-regime input for narrator — no dig/desk sludge."""
    room = _room(camp)
    pl = camp.get("player") or {}
    return {
        "room_name": room.get("name"),
        "room_desc": room.get("desc"),
        "hook": (room.get("hooks") or [None])[0],
        "exits": list((room.get("exits") or {}).keys()),
        "encounter": camp.get("encounter"),
        "player": {
            "name": pl.get("name"),
            "archetype": pl.get("archetype"),
            "hp": pl.get("hp"),
            "hp_max": pl.get("hp_max"),
            "traits": pl.get("traits"),
        },
        "flags": (camp.get("flags") or [])[-8:],
        "log_tail": [e.get("text") for e in (camp.get("log") or [])[-3:]],
        "legal": list_legal_actions(camp),
    }


def list_legal_actions(camp: dict[str, Any]) -> list[dict[str, Any]]:
    room = _room(camp)
    acts: list[dict[str, Any]] = []
    for direction in room.get("exits") or {}:
        acts.append({"type": "move", "direction": direction})
    enc = camp.get("encounter")
    if enc and int(enc.get("hp") or 0) > 0:
        acts.append({"type": "attack"})
        acts.append({"type": "flee"})
    acts.extend(
        [
            {"type": "look"},
            {"type": "rest"},
            {"type": "status"},
            {"type": "inventory"},
            {"type": "help"},
        ]
    )
    room = _room(camp)
    tags = [str(t).lower() for t in (room.get("tags") or [])]
    if "tavern" in tags or "hub" in tags or room.get("area_tag") == "hub":
        acts.extend([{"type": "rumor"}, {"type": "drink"}])
    if room.get("area_tag") in ("road", "woods") or "road" in str(room.get("id") or ""):
        acts.append({"type": "seek_fight"})
    return acts


def _pick_weighted(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    total = sum(int(r.get("w") or 1) for r in rows)
    x = random.randint(1, max(1, total))
    acc = 0
    for r in rows:
        acc += int(r.get("w") or 1)
        if x <= acc:
            return r
    return rows[-1]


def _fire_rest_events(camp: dict[str, Any]) -> list[str]:
    """CK/Rim-lite: tables + traits produce comedy."""
    events: list[str] = []
    tables = (camp.get("module_snapshot") or {}).get("event_tables") or {}
    pl = camp.get("player") or {}
    traits = [str(t).lower() for t in (pl.get("traits") or [])]
    st = camp.get("storyteller") or {}
    st["days_since_crisis"] = int(st.get("days_since_crisis") or 0) + 1

    row = _pick_weighted(list(tables.get("rest_safe") or []))
    if row:
        events.append(str(row.get("text") or ""))
        if row.get("lose") and row["lose"] in (pl.get("inventory") or []):
            pl["inventory"] = [i for i in pl.get("inventory") or [] if i != row["lose"]]
            events.append(f"(Lost {row['lose']}.)")
        if row.get("id") == "omen" and "craven" in traits:
            events.append("Your craven streak whispers: turn back.")
        if row.get("id") == "thief" and "greedy" in traits:
            events.append("As a greedy soul, the missing ration stings extra.")

    # merchant debt comedy if flag pending
    if "freed_merchant_opportunity" in (camp.get("flags") or []) and "greedy" in traits:
        row2 = _pick_weighted(list(tables.get("greedy_merchant") or []))
        if row2:
            events.append(str(row2.get("text") or ""))
            if row2.get("flag"):
                camp["flags"] = list(camp.get("flags") or []) + [str(row2["flag"])]
            camp["flags"] = [f for f in camp["flags"] if f != "freed_merchant_opportunity"]

    # storyteller crisis if budget and long calm
    budget = int(st.get("threat_budget") or 0)
    if budget > 0 and int(st.get("days_since_crisis") or 0) >= 2 and random.random() < 0.35:
        events.append("Distant horns — the keep's troubles don't sleep when you do.")
        st["days_since_crisis"] = 0
        st["threat_budget"] = budget - 1

    camp["storyteller"] = st
    camp["player"] = pl
    return [e for e in events if e]


def apply_action(campaign_id: str, action: dict[str, Any] | None) -> dict[str, Any]:
    from mag.game_dice import roll_dice

    camp = load_campaign(campaign_id)
    if not camp:
        return {"ok": False, "error": "missing campaign"}
    if camp.get("status") == "awaiting_character":
        return {"ok": False, "error": "need character first", "need_character": True}
    if camp.get("status") != "active":
        return {"ok": False, "error": f"campaign {camp.get('status')}"}

    action = action or {}
    atype = str(action.get("type") or "").lower().strip()
    legal = list_legal_actions(camp)
    events: list[str] = []
    pl = camp.get("player") or {}

    if atype in ("look", "status"):
        events.append(_narrate_room(camp))
    elif atype == "talk":
        # Freestyle IC speech → stay in room; engine hooks + barkeep color (no curveball)
        raw = str(action.get("raw") or "").strip()
        room = _room(camp)
        hooks = list(room.get("hooks") or [])
        tags = [str(x).lower() for x in (room.get("tags") or [])]
        events.append(f'You say: "{raw[:180]}"' if raw else "You speak into the room.")
        if "tavern" in tags or "hub" in tags or "barkeep" in (room.get("desc") or "").lower():
            if re.search(r"\b(polish|mug|tankard|glass|why)\b", raw, re.I):
                events.append(
                    "Mira the barkeep does not look up. "
                    "'Because if I stop, I start counting chairs I do not own and debts I do. "
                    "Mug is honest work. Keep smoke is not my department.'"
                )
            elif re.search(r"\b(hunt|mark|bad guy|failed|party|adventur)\b", raw, re.I):
                events.append(
                    "A regular snorts. 'Party came back empty-handed. "
                    "Heat like that finds a stranger's stool real quick.'"
                )
                camp["flags"] = list(
                    dict.fromkeys(list(camp.get("flags") or []) + ["failed_hunt_rumor"])
                )
            elif hooks:
                events.append("Hook surfaces: " + str(hooks[0]))
            else:
                events.append(
                    "The barkeep polishes. The fire argues with the damp. "
                    "No one answers cleanly — but the room heard you."
                )
        elif hooks:
            events.append(str(hooks[0]))
        else:
            events.append("Your words hang. The place does not invent a new room for them.")
        events.append(
            f"{pl.get('name') or 'You'}: HP {pl.get('hp')}/{pl.get('hp_max')}."
        )
    elif atype == "rumor":
        tables = (camp.get("module_snapshot") or {}).get("event_tables") or {}
        rows = list(tables.get("tavern_rumor") or [])
        if not rows:
            events.append("No one is talking. The fire pops once, unhelpfully.")
        else:
            row = _pick_weighted(rows) or {}
            events.append(str(row.get("text") or "A rumor dissolves before it lands."))
            if row.get("flag"):
                camp["flags"] = list(dict.fromkeys(list(camp.get("flags") or []) + [str(row["flag"])]))
    elif atype == "drink":
        tables = (camp.get("module_snapshot") or {}).get("event_tables") or {}
        rows = list(tables.get("tavern_drink") or [])
        row = _pick_weighted(rows) if rows else {}
        events.append(str((row or {}).get("text") or "You drink. It is a liquid."))
        # tiny heal in hub
        pl["hp"] = min(int(pl.get("hp_max") or 10), int(pl.get("hp") or 0) + 1)
        events.append(f"HP {pl['hp']}/{pl.get('hp_max')}.")
    elif atype == "seek_fight":
        tables = (camp.get("module_snapshot") or {}).get("event_tables") or {}
        room = _room(camp)
        tag = str(room.get("area_tag") or "road")
        key = "random_woods" if tag == "woods" else "random_road"
        if tag == "hub":
            events.append(
                "The barkeep clears their throat: 'Not in the Lantern.' "
                "Take the road if you want a fair fight."
            )
        else:
            rows = list(tables.get(key) or tables.get("random_road") or [])
            row = _pick_weighted(rows) if rows else {}
            events.append(str((row or {}).get("text") or "Nothing answers your bloodlust."))
            enc = (row or {}).get("encounter")
            if enc:
                camp["encounter"] = dict(enc)
    elif atype == "freeze":
        try:
            from mag.game_freeze import freeze_campaign

            fr = freeze_campaign(str(campaign_id))
            if fr.get("ok"):
                events.append(fr.get("speak") or f"Frozen `{fr.get('freeze_id')}`.")
            else:
                events.append(str(fr.get("error") or "freeze failed"))
        except Exception as exc:
            events.append(f"Freeze failed: {exc}"[:200])
    elif atype == "help":
        tips = ", ".join(
            a.get("type", "")
            + (f" {a['direction']}" if a.get("direction") else "")
            for a in legal[:10]
        )
        # Socratic: try freeze L0/L1 help if available
        try:
            from mag.game_freeze import freeze_campaign, format_socratic_help, load_freeze

            st = camp.get("storyteller") or {}
            fid = st.get("freeze_id")
            frz = load_freeze(str(fid)) if fid else None
            if not frz:
                fr = freeze_campaign(str(campaign_id))
                frz = fr.get("freeze") if fr.get("ok") else None
            if frz:
                events.append(format_socratic_help(frz))
            else:
                events.append(f"You can: {tips}. Or say inventory, rest, freeze state.")
        except Exception:
            events.append(f"You can: {tips}. Or say inventory, rest, freeze state.")
    elif atype == "inventory":
        inv = pl.get("inventory") or []
        events.append(
            f"{pl.get('name') or 'You'} carries: {', '.join(inv) if inv else 'nothing much'}."
        )
        events.append(f"HP {pl.get('hp')}/{pl.get('hp_max')}.")
    elif atype == "move":
        direction = str(action.get("direction") or "").lower()
        exits = _room(camp).get("exits") or {}
        if direction not in exits:
            # fuzzy
            for k in exits:
                if k.startswith(direction) or direction in k:
                    direction = k
                    break
        if direction not in exits:
            return {"ok": False, "error": f"can't go {direction}", "legal": legal}
        if camp.get("encounter") and int((camp["encounter"] or {}).get("hp") or 0) > 0:
            dmg = roll_dice("1d4")
            pl["hp"] = max(0, int(pl.get("hp") or 0) - int(dmg["total"]))
            events.append(f"Leaving under fire — take {dmg['total']}! HP {pl['hp']}.")
            if pl["hp"] <= 0:
                camp["status"] = "defeated"
                camp["player"] = pl
                events.append("You fall. Say start classic for a new run.")
                save_campaign(camp)
                return {"ok": True, "events": events, "narrate": " ".join(events), "status": "defeated"}
        camp["room_id"] = exits[direction]
        camp["encounter"] = None
        room = _room(camp)
        for fl in room.get("flags_on_enter") or []:
            camp["flags"] = list(dict.fromkeys(list(camp.get("flags") or []) + [fl]))
        enc = room.get("encounter")
        if enc:
            camp["encounter"] = dict(enc)
            events.append(f"You enter {room.get('name')}. {enc.get('name')}!")
        else:
            events.append(f"You go {direction} into {room.get('name')}.")
        # loot
        for item in room.get("loot") or []:
            inv = list(pl.get("inventory") or [])
            if item not in inv:
                inv.append(item)
                pl["inventory"] = inv
                events.append(f"You pick up {item}.")
        events.append(_narrate_room(camp))
    elif atype == "attack":
        enc = camp.get("encounter")
        if not enc or int(enc.get("hp") or 0) <= 0:
            return {"ok": False, "error": "nothing to attack", "legal": legal}
        traits = [str(t).lower() for t in (pl.get("traits") or [])]
        bonus = int(pl.get("attack_bonus") or 0)
        if "hotheaded" in traits:
            bonus += 1
        if "craven" in traits:
            events.append("Fear nags — you strike anyway.")
        hit = roll_dice(f"1d20+{bonus}")
        ac = int(enc.get("ac") or 10)
        if hit["total"] >= ac:
            dmg = roll_dice(str(pl.get("damage") or "1d6"))
            enc["hp"] = max(0, int(enc.get("hp") or 0) - int(dmg["total"]))
            events.append(
                f"Hit ({hit['total']} vs AC {ac}) for {dmg['total']}. "
                f"{enc.get('name')} HP {enc['hp']}/{enc.get('hp_max')}."
            )
            if enc["hp"] <= 0:
                events.append(f"{enc.get('name')} drops!")
                for fl in _room(camp).get("flags_on_clear") or []:
                    camp["flags"] = list(dict.fromkeys(list(camp.get("flags") or []) + [fl]))
                camp["encounter"] = None
                if "greedy" in traits and "freed_merchant_opportunity" in (camp.get("flags") or []):
                    events.append("The captive merchant eyes your purse already…")
        else:
            events.append(f"Miss ({hit['total']} vs AC {ac}).")
        enc = camp.get("encounter")
        if enc and int(enc.get("hp") or 0) > 0:
            fhit = roll_dice(f"1d20+{int(enc.get('attack_bonus') or 0)}")
            if fhit["total"] >= int(pl.get("ac") or 10):
                fdmg = roll_dice(str(enc.get("damage") or "1d6"))
                pl["hp"] = max(0, int(pl.get("hp") or 0) - int(fdmg["total"]))
                events.append(f"{enc.get('name')} hits for {fdmg['total']}! HP {pl['hp']}.")
                if pl["hp"] <= 0:
                    camp["status"] = "defeated"
                    events.append("You fall.")
            else:
                events.append(f"{enc.get('name')} misses.")
    elif atype == "flee":
        exits = list((_room(camp).get("exits") or {}).keys())
        if not exits:
            return {"ok": False, "error": "nowhere to flee"}
        return apply_action(campaign_id, {"type": "move", "direction": exits[0]})
    elif atype == "rest":
        if camp.get("encounter") and int((camp["encounter"] or {}).get("hp") or 0) > 0:
            return {"ok": False, "error": "can't rest in combat", "legal": legal}
        pl["hp"] = int(pl.get("hp_max") or 10)
        events.append(f"You rest. HP {pl['hp']}.")
        events.extend(_fire_rest_events(camp))
    else:
        return {"ok": False, "error": f"illegal action {atype}", "legal": legal}

    camp["player"] = pl
    camp["log"] = list(camp.get("log") or []) + [
        {"ts": _utc(), "type": atype, "text": e} for e in events
    ]
    save_campaign(camp)

    # session stats for DM dogfood / Fast-Slow metrics
    st = dict(camp.get("storyteller") or {})
    st["turn_n"] = int(st.get("turn_n") or 0) + 1
    st["fast_turns"] = int(st.get("fast_turns") or 0) + 1  # engine apply = fast path
    camp["storyteller"] = st
    save_campaign(camp)

    try:
        from mag.training_events import emit

        emit(
            "game_turn",
            join={
                "campaign_id": campaign_id,
                "module_id": str(camp.get("module_id") or ""),
                "world_family": "tabletop-dnd",
                "voice_session_id": str(camp.get("voice_session_id") or ""),
            },
            input_data={"action": atype, "direction": action.get("direction") or ""},
            action={
                "room": camp.get("room_id"),
                "fast_path": True,
                "ds_called": False,
            },
            outcome={
                "status": camp.get("status"),
                "events_n": len(events),
                "turn_n": st.get("turn_n"),
                "has_encounter": bool(
                    camp.get("encounter") and int((camp.get("encounter") or {}).get("hp") or 0) > 0
                ),
            },
            pattern_tags=["game", "tabletop-dnd", atype, "fast_path", "dogfood_dm"],
            tier_max="T2",
            exportable=False,
        )
    except Exception:
        pass

    return {
        "ok": True,
        "schema": SCHEMA,
        "campaign_id": campaign_id,
        "events": events,
        "narrate": " ".join(events),
        "legal": list_legal_actions(camp),
        "scene_context": scene_context(camp),
        "status": camp.get("status"),
        "player": camp.get("player"),
        "fast_path": True,
        "ds_called": False,
        "metrics": {
            "turn_n": st.get("turn_n"),
            "fast_turns": st.get("fast_turns"),
            "slow_turns": st.get("slow_turns") or 0,
        },
    }


def parse_player_speech(text: str) -> dict[str, Any] | None:
    t = (text or "").strip().lower()
    if not t:
        return None
    # single-letter exits (voice-friendly)
    if t in ("n", "north"):
        return {"type": "move", "direction": "north"}
    if t in ("s", "south"):
        return {"type": "move", "direction": "south"}
    if t in ("e", "east"):
        return {"type": "move", "direction": "east"}
    if t in ("w", "west"):
        return {"type": "move", "direction": "west"}
    if t in ("u", "up"):
        return {"type": "move", "direction": "up"}
    if t in ("d", "down"):
        return {"type": "move", "direction": "down"}
    if re.search(r"\b(freeze state|freeze game|game freeze|dump state|save freeze)\b", t):
        return {"type": "freeze"}
    if re.search(r"\b(help|what can i do|options|commands|legal)\b", t):
        return {"type": "help"}
    if re.search(r"\b(inventory|inv|what do i (have|carry)|gear|pack)\b", t):
        return {"type": "inventory"}
    if re.search(
        r"\b(rumor|rumours|rumors|gossip|news|what('s| is) the (word|news)|ask (the )?barkeep)\b",
        t,
    ):
        return {"type": "rumor"}
    if re.search(r"\b(drink|ale|beer|broth|buy a drink|order a)\b", t):
        return {"type": "drink"}
    if re.search(
        r"\b(leave (the )?(tavern|inn|bar)|go (outside|out)|hit the road|leave for the road)\b",
        t,
    ):
        return {"type": "move", "direction": "out"}
    if re.search(r"\b(look|where am i|describe|status|what do i see|examine|search|peer)\b", t):
        return {"type": "look"}
    # In-world talk / ask NPC (must not fall through to curveball bathroom fails)
    if re.search(
        r"\b("
        r"why (are|is|do|does)|what (are|is|do|does)|who (are|is)|"
        r"how (are|is|do|does|come)|tell me|ask |talk to|speak to|say to|"
        r"polishing|barkeep|mira|hey |hello|good (eve|day|night)|"
        r"what('s| is) (that|this|the)"
        r")\b",
        t,
    ):
        return {"type": "talk", "raw": (text or "").strip()[:240]}
    if re.search(r"\b(rest|heal|camp|sleep)\b", t):
        return {"type": "rest"}
    if re.search(r"\b(attack|hit|fight|strike|kill|swing|stab|slash)\b", t):
        return {"type": "attack"}
    if re.search(r"\b(flee|run away|retreat)\b", t) and not re.search(r"\brun into\b", t):
        return {"type": "flee"}
    for d in (
        "north",
        "south",
        "east",
        "west",
        "up",
        "down",
        "left",
        "right",
        "deeper",
        "back",
        "out",
        "tavern",
    ):
        if re.search(rf"\b(go |move |head |walk |run )?(to )?{d}\b", t) or t.strip() == d:
            return {"type": "move", "direction": d}
    if re.search(r"\b(enter|gate|to the keep|inside|through the (gate|door))\b", t):
        return {"type": "move", "direction": "north"}
    if re.search(r"\b(fight (a |some )?|go (fight|hunt)|find (a )?monster|random fight)\b", t):
        return {"type": "seek_fight"}
    return None


def seal_session(
    *,
    session_id: str = "",
    campaign_id: str = "",
    tldr: str = "",
) -> dict[str, Any]:
    """DM post-game notes — FILE session card for train/exploit review."""
    camp = load_campaign(campaign_id) if campaign_id else None
    if not camp and session_id:
        camp = latest_for_session(session_id)
    if not camp:
        return {"ok": False, "error": "no campaign to seal"}
    st = camp.get("storyteller") or {}
    turn_n = int(st.get("turn_n") or len(camp.get("log") or []))
    fast_n = int(st.get("fast_turns") or turn_n)
    slow_n = int(st.get("slow_turns") or 0)
    card = {
        "schema": "mag_game_session_seal.v1",
        "ts": _utc(),
        "campaign_id": camp.get("campaign_id"),
        "voice_session_id": camp.get("voice_session_id") or session_id,
        "module_id": camp.get("module_id"),
        "module_title": camp.get("module_title"),
        "room_id": camp.get("room_id"),
        "status": camp.get("status"),
        "player": camp.get("player"),
        "flags": camp.get("flags"),
        "metrics": {
            "turn_n": turn_n,
            "fast_turns": fast_n,
            "slow_turns": slow_n,
            "local_only_pct": round(100.0 * fast_n / max(1, fast_n + slow_n), 1),
        },
        "log_tail": (camp.get("log") or [])[-12:],
        "tldr": (tldr or "")[:500]
        or f"Sealed at {camp.get('room_id')} after ~{turn_n} turns.",
        "dogfood_dm": True,
        "transfer_checklist": [
            "default_local_engine",
            "pack_then_guest",
            "confirm_before_write",
            "file_outcomes",
            "hub_return",
        ],
    }
    out_dir = ROOT / "memory" / "working" / "game_sessions"
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = f"seal_{camp.get('campaign_id')}_{_utc()[:19].replace(':', '')}.json"
    path = out_dir / fname
    path.write_text(json.dumps(card, indent=2, default=str), encoding="utf-8")
    rel = str(path.relative_to(ROOT)).replace("\\", "/")
    try:
        from mag.training_events import emit

        emit(
            "game_turn",
            join={"campaign_id": str(camp.get("campaign_id")), "kind": "seal"},
            action={"seal": True, "path": rel},
            outcome=card["metrics"],
            pattern_tags=["game", "seal", "dogfood_dm", "dm_transfer"],
            tier_max="T1",
            exportable=False,
        )
    except Exception:
        pass
    speak = (
        f"Session sealed ({rel}). "
        f"Turns {turn_n}; fast {fast_n}; slow/guest {slow_n}; "
        f"local-only ~{card['metrics']['local_only_pct']}%. "
        f"DM drill: name which Mag seat fired. See docs/ref/DM_MAG_TRANSFER.md"
    )
    return {"ok": True, "path": rel, "card": card, "speak": speak, "narrate": speak}


def handle_game(body: dict[str, Any] | None = None) -> dict[str, Any]:
    body = body or {}
    action = str(body.get("action") or "status").strip().lower()
    sid = str(body.get("session_id") or "")
    if action in ("modules", "list_modules"):
        return {"ok": True, "modules": list_modules()}
    if action in ("seal", "seal_session", "end_session"):
        return seal_session(
            session_id=sid,
            campaign_id=str(body.get("campaign_id") or ""),
            tldr=str(body.get("tldr") or body.get("text") or ""),
        )
    if action in ("start", "new", "classic", "play"):
        return begin_play(
            module_id=str(body.get("module") or body.get("module_id") or "classic"),
            voice_session_id=sid,
            force_new=bool(body.get("force_new") or action == "new"),
        )
    if action in ("character", "set_character"):
        cid = str(body.get("campaign_id") or "")
        if not cid:
            c = latest_for_session(sid)
            cid = str((c or {}).get("campaign_id") or "")
        player = body.get("player") if isinstance(body.get("player"), dict) else parse_character(
            str(body.get("text") or "")
        )
        if not player:
            return {"ok": False, "error": "could not parse character", "need_character": True}
        return set_character(cid, player)
    if action in ("state", "status"):
        c = load_campaign(str(body.get("campaign_id") or "")) or latest_for_session(sid)
        if not c:
            return {"ok": False, "error": "no campaign"}
        return {
            "ok": True,
            "campaign_id": c.get("campaign_id"),
            "status": c.get("status"),
            "scene_context": scene_context(c) if c.get("player") else None,
            "speak": _narrate_room(c) if c.get("player") else "Need character.",
            "legal": list_legal_actions(c) if c.get("player") else [],
        }
    if action in ("act", "apply", "do"):
        c = load_campaign(str(body.get("campaign_id") or "")) or latest_for_session(sid)
        if not c:
            return {"ok": False, "error": "no campaign"}
        act = body.get("move") or body.get("act")
        if isinstance(act, str):
            act = parse_player_speech(act) or {"type": act}
        if not act and body.get("text"):
            act = parse_player_speech(str(body.get("text")))
        return apply_action(str(c["campaign_id"]), act if isinstance(act, dict) else {})
    return {"ok": False, "error": f"unknown action {action}"}
