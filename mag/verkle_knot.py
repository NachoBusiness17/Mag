"""Living Verkle-knot record of session dossiers (topic evolution).

Filename is the address. Chain tip is a succinct root (Merkle–Verkle hybrid,
same spirit as sovereign_mirror.core.verkle — IPA/KZG upgrade-compatible).

Leaf filename pattern (living record):
  {date}_{HHmmUTC}_{dominantTheme}_{session8}_{commit8}.knot.json

Example:
  2026-07-20_1109_mag-hands_019f7f37_6a4ffbee.knot.json

Directory:
  memory/biography/knots/           # one leaf file per session commit
  memory/biography/verkle_chain.jsonl
  memory/biography/verkle_tip.json   # current root + n_leaves + last filename
  memory/biography/topic_evolution.json  # theme basis series for charts
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import ROOT

BIO = ROOT / "memory" / "biography"
KNOTS = BIO / "knots"
CHAIN = BIO / "verkle_chain.jsonl"
TIP = BIO / "verkle_tip.json"
EVOLUTION = BIO / "topic_evolution.json"

THEME_BASIS = [
    "mirror_meta",
    "mag_hands",
    "scrum_plan",
    "constitution",
    "dashboard",
    "harness",
    "biography",
    "data_r0",
]


def _h(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _leaf_hash(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, default=str).encode("utf-8")
    return _h(b"leaf:" + raw)


def _merkle_root(leaf_hashes: list[str]) -> str:
    if not leaf_hashes:
        return _h(b"empty")
    layer = leaf_hashes[:]
    while len(layer) > 1:
        nxt = []
        for i in range(0, len(layer), 2):
            left = layer[i]
            right = layer[i + 1] if i + 1 < len(layer) else left
            nxt.append(_h(b"node:" + left.encode() + b":" + right.encode()))
        layer = nxt
    return layer[0]


def _slug_theme(name: str | None) -> str:
    if not name:
        return "untagged"
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return (s or "untagged")[:24]


def knot_filename(
    *,
    start_minute_iso: str | None,
    dominant_theme: str | None,
    session_id: str,
    commit_hex: str,
    chord_slug: str | None = None,
) -> str:
    """Build living-record filename from time + topic + identity + commit.

    Optional chord_slug (from strike commitment) replaces theme when present:
      {date}_{HHmm}_{chord-slug}_{session8}_{commit8}.knot.json
    """
    if start_minute_iso:
        m = re.match(
            r"(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2})",
            start_minute_iso.replace("Z", ""),
        )
        if m:
            date, hh, mm = m.group(1), m.group(2), m.group(3)
        else:
            now = datetime.now(timezone.utc)
            date, hh, mm = now.strftime("%Y-%m-%d"), now.strftime("%H"), now.strftime("%M")
    else:
        now = datetime.now(timezone.utc)
        date, hh, mm = now.strftime("%Y-%m-%d"), now.strftime("%H"), now.strftime("%M")

    if chord_slug and str(chord_slug).startswith("chord-"):
        # chord-biography-abc123def → biography
        parts = str(chord_slug).split("-")
        theme = _slug_theme(parts[1] if len(parts) > 1 else dominant_theme)
    else:
        theme = _slug_theme(dominant_theme)
    sid = (session_id or "unknown")[:8]
    c8 = (commit_hex or "0" * 8)[:8]
    return f"{date}_{hh}{mm}_{theme}_{sid}_{c8}.knot.json"


def build_leaf_from_dossier(dossier: dict[str, Any]) -> dict[str, Any]:
    """Canonical leaf payload for Verkle commit (topic evolution unit)."""
    time = dossier.get("time") or {}
    sk = dossier.get("scalar_knot") or {}
    tv = sk.get("theme_vector") or {}
    created = time.get("created_at") or {}
    updated = time.get("updated_at") or time.get("last_active_at") or {}
    commit = dossier.get("content_commit") or {}

    # pad theme vector to fixed basis
    basis = tv.get("basis") or THEME_BASIS
    raw = tv.get("raw") or [0.0] * len(THEME_BASIS)
    norm = tv.get("normalized") or [0.0] * len(THEME_BASIS)
    if len(norm) < len(THEME_BASIS):
        norm = list(norm) + [0.0] * (len(THEME_BASIS) - len(norm))

    leaf = {
        "type": "session_scalar_knot_leaf",
        "schema": "verkle_knot_leaf.v1",
        "session_id": dossier.get("session_id"),
        "start_minute": created.get("iso_minute"),
        "end_minute": updated.get("iso_minute"),
        "start_unix_minute": created.get("unix_minute"),
        "end_unix_minute": updated.get("unix_minute"),
        "date": created.get("date"),
        "duration_minutes": sk.get("duration_minutes"),
        "dominant_theme": tv.get("dominant"),
        "theme_basis": basis if basis else THEME_BASIS,
        "theme_vector_raw": raw,
        "theme_vector_normalized": norm[: len(THEME_BASIS)],
        "tension_index": sk.get("tension_index"),
        "residual_weight": sk.get("residual_weight"),
        "Q_proxy": sk.get("Q_proxy"),
        "gap_proxy": sk.get("gap_proxy"),
        "lambda2_proxy": sk.get("lambda2_proxy"),
        "dirichlet_energy_proxy": sk.get("dirichlet_energy_proxy"),
        "dossier_commit": commit.get("hex"),
        "chord_commitment": (dossier.get("chord") or {}).get("commitment_hash"),
        "chord_root": (dossier.get("chord") or {}).get("framework_root"),
        "observer_chart_scores": {
            c.get("id"): c.get("score")
            for c in ((dossier.get("chord") or {}).get("observer_charts") or [])
        },
        "loops_audited": [
            L.get("id") for L in ((dossier.get("chord") or {}).get("loops_audited") or [])
        ],
        "engine": "untangling+strike_chord",
        "inspiration": "steiniger_proxies+strike_chord+verkle_history",
    }
    leaf["leaf_hash"] = _leaf_hash(leaf)
    return leaf


def _load_chain_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not CHAIN.is_file():
        return rows
    for line in CHAIN.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def consolidate_chain_one_leaf_per_session() -> dict[str, Any]:
    """Drop duplicate chain rows (keep last per session_id). Safe to run anytime."""
    rows = _load_chain_rows()
    by_sid: dict[str, dict[str, Any]] = {}
    orphan: list[dict[str, Any]] = []
    for r in rows:
        sid = str(r.get("session_id") or "")
        if not sid:
            orphan.append(r)
            continue
        # keep last occurrence (most recent amend)
        old = by_sid.get(sid)
        if old and old.get("filename") and old.get("filename") != r.get("filename"):
            old_path = KNOTS / str(old["filename"])
            if old_path.is_file():
                try:
                    old_path.unlink()
                except OSError:
                    pass
        by_sid[sid] = r
    # preserve first-seen order of sessions
    order: list[str] = []
    for r in rows:
        sid = str(r.get("session_id") or "")
        if sid and sid not in order:
            order.append(sid)
    kept = [by_sid[s] for s in order if s in by_sid] + orphan
    hashes = _rewrite_chain(kept)
    root = _merkle_root(hashes) if hashes else _h(b"empty")
    tip = {
        "schema": "verkle_tip.v1",
        "root": root,
        "n_leaves": len(hashes),
        "last_filename": (kept[-1].get("filename") if kept else None),
        "last_leaf_hash": hashes[-1] if hashes else None,
        "last_session_id": (kept[-1].get("session_id") if kept else None),
        "note": "Consolidated: one leaf per session.",
    }
    TIP.write_text(json.dumps(tip, indent=2), encoding="utf-8")
    # evolution series unique by session
    if EVOLUTION.is_file():
        try:
            evo = json.loads(EVOLUTION.read_text(encoding="utf-8"))
            series = evo.get("series") or []
            seen: dict[str, dict] = {}
            ord_s: list[str] = []
            for s in series:
                sid = str(s.get("session_id") or "")
                if not sid:
                    continue
                if sid not in ord_s:
                    ord_s.append(sid)
                seen[sid] = s
            evo["series"] = [{**seen[s], "index": i} for i, s in enumerate(ord_s)]
            evo["n_leaves"] = len(evo["series"])
            evo["verkle_root"] = root
            EVOLUTION.write_text(json.dumps(evo, indent=2), encoding="utf-8")
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "ok": True,
        "before": len(rows),
        "after": len(kept),
        "removed": len(rows) - len(kept),
        "root": root,
    }


def _rewrite_chain(rows: list[dict[str, Any]]) -> list[str]:
    """Rewrite chain file with stable indices; return leaf_hashes in order."""
    hashes: list[str] = []
    lines: list[str] = []
    for i, row in enumerate(rows):
        h = row.get("leaf_hash")
        if not h:
            continue
        prior = hashes[:]
        hashes.append(h)
        root = _merkle_root(hashes)
        parent = _merkle_root(prior) if prior else _h(b"empty")
        row = dict(row)
        row["index"] = i
        row["n_leaves"] = len(hashes)
        row["parent_verkle_root"] = parent
        row["verkle_root"] = root
        lines.append(json.dumps(row))
    CHAIN.parent.mkdir(parents=True, exist_ok=True)
    CHAIN.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return hashes


def append_verkle_knot(dossier: dict[str, Any], pdf_path: str | None = None) -> dict[str, Any]:
    """
    Write/update one leaf per session (amend in place).

    Same session_id → replace existing chain row + knot file (no bloat).
    New session_id → append. Same leaf_hash → skip.
    """
    KNOTS.mkdir(parents=True, exist_ok=True)
    leaf = build_leaf_from_dossier(dossier)
    fname = knot_filename(
        start_minute_iso=leaf.get("start_minute"),
        dominant_theme=leaf.get("dominant_theme"),
        session_id=str(leaf.get("session_id") or ""),
        commit_hex=str(leaf.get("dossier_commit") or leaf.get("leaf_hash") or ""),
        chord_slug=leaf.get("chord_commitment"),
    )
    leaf["filename"] = fname
    if pdf_path:
        leaf["pdf_path"] = pdf_path

    sid = str(leaf.get("session_id") or "unknown")
    rows = _load_chain_rows()
    existing_i = next(
        (i for i, r in enumerate(rows) if str(r.get("session_id") or "") == sid),
        None,
    )

    # identical content already recorded for this session
    if existing_i is not None and rows[existing_i].get("leaf_hash") == leaf["leaf_hash"]:
        tip = json.loads(TIP.read_text(encoding="utf-8")) if TIP.is_file() else {}
        return {
            "ok": True,
            "skipped": True,
            "amended": False,
            "filename": fname,
            "leaf_hash": leaf["leaf_hash"],
            "verkle_root": tip.get("root"),
            "path": str(KNOTS / fname),
            "n_leaves": tip.get("n_leaves") or len(rows),
        }

    # drop old knot file for this session if filename changed
    if existing_i is not None:
        old_name = rows[existing_i].get("filename")
        if old_name and old_name != fname:
            old_path = KNOTS / str(old_name)
            if old_path.is_file():
                try:
                    old_path.unlink()
                except OSError:
                    pass

    path = KNOTS / fname
    path.write_text(json.dumps(leaf, indent=2), encoding="utf-8")
    (KNOTS / f"by-session_{sid[:12]}.json").write_text(
        json.dumps({"filename": fname, "leaf_hash": leaf["leaf_hash"]}, indent=2),
        encoding="utf-8",
    )

    chain_row = {
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "filename": fname,
        "leaf_hash": leaf["leaf_hash"],
        "session_id": leaf.get("session_id"),
        "start_minute": leaf.get("start_minute"),
        "end_minute": leaf.get("end_minute"),
        "dominant_theme": leaf.get("dominant_theme"),
        "theme_vector_normalized": leaf.get("theme_vector_normalized"),
        "tension_index": leaf.get("tension_index"),
        "dossier_commit": leaf.get("dossier_commit"),
        "amended": existing_i is not None,
    }
    if existing_i is not None:
        rows[existing_i] = chain_row
        amended = True
    else:
        rows.append(chain_row)
        amended = False

    all_hashes = _rewrite_chain(rows)
    root = _merkle_root(all_hashes) if all_hashes else _h(b"empty")
    parent_root = (
        _merkle_root(all_hashes[:-1]) if len(all_hashes) > 1 else _h(b"empty")
    )

    tip = {
        "schema": "verkle_tip.v1",
        "root": root,
        "n_leaves": len(all_hashes),
        "last_filename": fname,
        "last_leaf_hash": leaf["leaf_hash"],
        "last_session_id": leaf.get("session_id"),
        "updated_minute": leaf.get("end_minute") or leaf.get("start_minute"),
        "note": "One leaf per session; amend in place on re-summarize. Merkle–Verkle hybrid tip.",
    }
    TIP.write_text(json.dumps(tip, indent=2), encoding="utf-8")
    (BIO / "latest.knot.json").write_text(json.dumps(leaf, indent=2), encoding="utf-8")

    _update_topic_evolution(leaf, root, len(all_hashes), amend_session=sid)

    return {
        "ok": True,
        "amended": amended,
        "filename": fname,
        "path": str(path),
        "leaf_hash": leaf["leaf_hash"],
        "verkle_root": root,
        "parent_verkle_root": parent_root,
        "n_leaves": len(all_hashes),
        "chain": str(CHAIN),
        "tip": str(TIP),
        "evolution": str(EVOLUTION),
    }


def _update_topic_evolution(
    leaf: dict[str, Any],
    root: str,
    n: int,
    *,
    amend_session: str | None = None,
) -> None:
    """Maintain series of theme vectors — one row per session (amend if present)."""
    data: dict[str, Any]
    if EVOLUTION.is_file():
        try:
            data = json.loads(EVOLUTION.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    else:
        data = {}

    data["schema"] = "topic_evolution.v1"
    data["theme_basis"] = THEME_BASIS
    data["verkle_root"] = root
    data["n_leaves"] = n
    series: list[dict[str, Any]] = list(data.get("series") or [])
    point = {
        "filename": leaf.get("filename"),
        "session_id": leaf.get("session_id"),
        "start_minute": leaf.get("start_minute"),
        "end_minute": leaf.get("end_minute"),
        "start_unix_minute": leaf.get("start_unix_minute"),
        "end_unix_minute": leaf.get("end_unix_minute"),
        "dominant_theme": leaf.get("dominant_theme"),
        "theme_vector_normalized": leaf.get("theme_vector_normalized"),
        "tension_index": leaf.get("tension_index"),
        "residual_weight": leaf.get("residual_weight"),
        "Q_proxy": leaf.get("Q_proxy"),
        "dirichlet_energy_proxy": leaf.get("dirichlet_energy_proxy"),
        "leaf_hash": leaf.get("leaf_hash"),
    }
    sid = amend_session or str(leaf.get("session_id") or "")
    replaced = False
    if sid:
        for i, s in enumerate(series):
            if str(s.get("session_id") or "") == sid:
                series[i] = {**point, "index": i}
                replaced = True
                break
    if not replaced:
        point["index"] = len(series)
        series.append(point)
    # reindex
    for i, s in enumerate(series):
        s["index"] = i
    data["series"] = series[-500:]
    data["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    EVOLUTION.write_text(json.dumps(data, indent=2), encoding="utf-8")


def evolution_summary() -> dict[str, Any]:
    """Human-readable summary of topic drift across the living record."""
    if not EVOLUTION.is_file():
        return {"ok": False, "error": "no topic_evolution.json yet"}
    data = json.loads(EVOLUTION.read_text(encoding="utf-8"))
    series = data.get("series") or []
    if not series:
        return {"ok": True, "n": 0, "message": "empty series"}

    # dominant theme counts
    from collections import Counter

    dom = Counter(s.get("dominant_theme") or "untagged" for s in series)
    # mean theme vector
    basis = data.get("theme_basis") or THEME_BASIS
    acc = [0.0] * len(basis)
    for s in series:
        v = s.get("theme_vector_normalized") or []
        for i in range(len(basis)):
            acc[i] += float(v[i]) if i < len(v) else 0.0
    n = len(series)
    mean = [round(x / n, 6) for x in acc]
    first, last = series[0], series[-1]
    return {
        "ok": True,
        "n_leaves": n,
        "verkle_root": data.get("verkle_root"),
        "first_minute": first.get("start_minute"),
        "last_minute": last.get("end_minute") or last.get("start_minute"),
        "dominant_theme_counts": dict(dom),
        "mean_theme_vector": dict(zip(basis, mean)),
        "latest_filename": last.get("filename"),
        "latest_dominant": last.get("dominant_theme"),
        "tip": str(TIP),
        "knots_dir": str(KNOTS),
    }
