"""Model registry — roles → Ollama model ids from lanes.yaml + live tags."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Literal

from config import ROOT

Role = Literal["router", "worker", "critic", "embed", "clerk", "biographer"]

# Fallback if YAML missing
_DEFAULTS: dict[str, str] = {
    "router": "gemma:2b",
    "clerk": "gemma:2b",
    "worker": "gemma4:latest",
    "critic": "gemma4:latest",
    "biographer": "gemma4:latest",
    "embed": "nomic-embed-text",
}

# Mag roles that map to the same physical models
_ALIASES: dict[str, str] = {
    "clerk": "router",  # small model
    "biographer": "worker",
}


def _load_local_models() -> dict[str, str]:
    path = ROOT / "configs" / "lanes.yaml"
    out = dict(_DEFAULTS)
    if not path.is_file():
        return out
    try:
        import yaml  # type: ignore

        raw = path.read_text(encoding="utf-8")
        # strip comments
        lines = []
        for line in raw.splitlines():
            if "#" in line:
                q = False
                buf = []
                for ch in line:
                    if ch == '"':
                        q = not q
                    if ch == "#" and not q:
                        break
                    buf.append(ch)
                line = "".join(buf).rstrip()
            if line.strip():
                lines.append(line)
        data = yaml.safe_load("\n".join(lines)) or {}
        lm = data.get("local_models") or {}
        if isinstance(lm, dict):
            for k, v in lm.items():
                if v:
                    out[str(k)] = str(v)
        # lanes.yaml uses clerk; registry accepts clerk
        if "clerk" in out and "router" not in lm:
            out["router"] = out["clerk"]
        if "router" in out and "clerk" not in lm:
            out["clerk"] = out["router"]
        if "worker" in out:
            out.setdefault("biographer", out["worker"])
            out.setdefault("critic", out["worker"])
    except Exception:
        pass
    return out


def ollama_base_url() -> str:
    try:
        from config import ollama_base

        return ollama_base()
    except Exception:
        return "http://127.0.0.1:11434"


def ollama_tags(timeout: float = 3.0) -> list[str]:
    try:
        base = ollama_base_url()
        with urllib.request.urlopen(f"{base}/api/tags", timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
        return [str(m.get("name") or "") for m in (data.get("models") or []) if m.get("name")]
    except Exception:
        return []


def model_present(name: str, tags: list[str] | None = None) -> bool:
    tags = tags if tags is not None else ollama_tags()
    if name in tags:
        return True
    # ollama sometimes lists with/without :latest
    base = name.split(":")[0]
    for t in tags:
        if t == name or t.startswith(base + ":"):
            return True
    return False


def model_for(role: str) -> str:
    """Resolve role → model id. Raises if role unknown."""
    models = _load_local_models()
    r = (role or "worker").lower()
    if r in _ALIASES and r not in models:
        r = _ALIASES[r]
    # direct
    if r in models:
        return models[r]
    # alias fallback
    if role.lower() in _ALIASES:
        key = _ALIASES[role.lower()]
        return models.get(key) or models.get("worker") or "gemma4:latest"
    if r == "router":
        return models.get("clerk") or models.get("router") or "gemma:2b"
    return models.get("worker") or "gemma4:latest"


def require_model(role: str, *, strict: bool = True) -> str:
    """Return model id; if strict and missing from Ollama, raise RuntimeError."""
    mid = model_for(role)
    tags = ollama_tags()
    if not tags:
        if strict:
            raise RuntimeError(f"Ollama not reachable at {ollama_base_url()}")
        return mid
    if not model_present(mid, tags):
        if strict:
            raise RuntimeError(
                f"Model '{mid}' for role '{role}' not in ollama list. "
                f"Pull it or fix configs/lanes.yaml local_models. Have: {tags}"
            )
    return mid


def inventory() -> dict[str, Any]:
    """Full map for CLI/Board — roles, models, present flags."""
    models = _load_local_models()
    tags = ollama_tags()
    roles = sorted(set(list(models.keys()) + ["router", "worker", "critic", "clerk", "biographer"]))
    rows = []
    for role in roles:
        mid = model_for(role)
        rows.append(
            {
                "role": role,
                "model": mid,
                "present": model_present(mid, tags) if tags else False,
            }
        )
    return {
        "ok": bool(tags),
        "ollama_up": bool(tags),
        "tags": tags,
        "roles": rows,
        "load_policy": "sequential",
        "note": "Dual-local: clerk/router=small, worker/critic/biographer=large. Sequential load.",
    }
