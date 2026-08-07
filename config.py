"""Paths and limits for local_sovereign_agent."""
from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent

MEMORY_DIR = ROOT / "memory"
STATE_DIR = ROOT / "state"
QUEUE_DIR = ROOT / "queue"
HANDOFF_DIR = QUEUE_DIR / "handoff"
RESULTS_DIR = QUEUE_DIR / "results"
LOGS_DIR = ROOT / "logs"
PROMPTS_DIR = ROOT / "prompts"
CONFIGS_DIR = ROOT / "configs"
CHECKPOINT_DB = STATE_DIR / "checkpoints.db"
ROUTER_LOG = LOGS_DIR / "router.jsonl"
CURRENT_MD = STATE_DIR / "CURRENT.md"
LOCUS_MD = MEMORY_DIR / "locus.md"
WORKING_MD = MEMORY_DIR / "working.md"

# Jail for filesystem tools (project root only by default)
FS_ROOTS = [ROOT]

# Sibling product (mycelial-republic) — read-allowed when present so dual-progress
# / BOOT_SOIL agents can open docs/MILESTONES without path-outside-jail failures.
# Still T2 discipline: agents must not send private raw exports to remote seats.
_REPUBLIC = (ROOT.parent / "mycelial-republic").resolve()
if _REPUBLIC.is_dir():
    FS_ROOTS.append(_REPUBLIC)

# Shell allowlist prefixes (first token)
SHELL_ALLOW = {
    "dir",
    "ls",
    "Get-ChildItem",
    "echo",
    "type",
    "cat",
    "python",
    "pytest",
    "git",
}

MAX_GRAPH_STEPS = 12
MAX_TOOL_OUTPUT = 8000


def ollama_base() -> str:
    """Ollama HTTP base. Env OLLAMA_HOST or OLLAMA_BASE overrides (Vast tunnel)."""
    import os

    raw = (os.environ.get("OLLAMA_HOST") or os.environ.get("OLLAMA_BASE") or "").strip()
    if not raw:
        return "http://127.0.0.1:11434"
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw.rstrip("/")
    # bare host:port
    return f"http://{raw}".rstrip("/")


# Resolved at import for simple callers; prefer ollama_base() when env may change
OLLAMA_BASE = ollama_base()

LAB_BIND_PATH = MEMORY_DIR / "working" / "lab_bind.json"
CAST_BIND_PATH = MEMORY_DIR / "working" / "cast_bind.json"

_BIND_PATHS = {"desk": LAB_BIND_PATH, "cast": CAST_BIND_PATH}


def _bind_path(service: str = "desk") -> Path:
    return _BIND_PATHS.get(service, LAB_BIND_PATH)


def read_bind(service: str = "desk") -> dict[str, Any]:
    """Persisted LAN opt-in from an explicit --lan start (not env drift)."""
    import json

    path = _bind_path(service)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def read_lab_bind() -> dict[str, Any]:
    return read_bind("desk")


def record_bind(*, service: str = "desk", lan: bool, host: str, port: int) -> None:
    import json
    from datetime import datetime, timezone

    path = _bind_path(service)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": "mag_bind.v1",
                "service": service,
                "lan": bool(lan),
                "host": host,
                "port": int(port),
                "ts": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def record_lab_bind(*, lan: bool, host: str, port: int) -> None:
    record_bind(service="desk", lan=lan, host=host, port=port)


def clear_bind(service: str = "desk") -> None:
    path = _bind_path(service)
    if path.is_file():
        try:
            path.unlink()
        except OSError:
            pass


def clear_lab_bind() -> None:
    clear_bind("desk")


def _lan_env_explicit() -> bool:
    import os

    return os.environ.get("MAG_LAN", "").strip().lower() in ("1", "true", "yes")


def bind_host(default: str = "127.0.0.1") -> str:
    """Listen address for dashboard/backend. Bare-metal default is localhost only."""
    import os

    if in_container():
        raw = (os.environ.get("MAG_BIND_HOST") or default).strip()
        return raw or default
    return default


def resolve_bind_host(
    *,
    lan: bool = False,
    local_only: bool = False,
    host_override: str | None = None,
    port: int = 8765,
    service: str = "desk",
) -> str:
    """Safe bind resolver — LAN never accidental on bare metal."""
    import os
    import sys

    cmd = f"python main.py {service if service == 'cast' else 'lab'}"
    if local_only:
        clear_bind(service)
        return "127.0.0.1"

    if lan:
        record_bind(service=service, lan=True, host="0.0.0.0", port=port)
        return "0.0.0.0"

    if host_override and host_override.strip():
        host = host_override.strip()
        if host == "0.0.0.0" and not (in_container() or _lan_env_explicit()):
            sys.stdout.write(
                f"  [bind] refused 0.0.0.0 without --lan -- staying on 127.0.0.1 "
                f"(use: {cmd} --lan)\n"
            )
            return "127.0.0.1"
        if host == "0.0.0.0":
            record_bind(service=service, lan=True, host=host, port=port)
        return host

    if in_container():
        raw = (os.environ.get("MAG_BIND_HOST") or "127.0.0.1").strip()
        return raw or "127.0.0.1"

    pref = read_bind(service)
    if pref.get("lan"):
        return "0.0.0.0"

    raw = (os.environ.get("MAG_BIND_HOST") or "").strip()
    if raw and raw not in ("127.0.0.1", "localhost") and _lan_env_explicit():
        if raw == "0.0.0.0":
            record_bind(service=service, lan=True, host=raw, port=port)
        return raw
    if raw and raw not in ("127.0.0.1", "localhost") and not _lan_env_explicit():
        sys.stdout.write(
            f"  [bind] ignoring MAG_BIND_HOST without MAG_LAN=1 -- staying on 127.0.0.1 "
            f"(use: {cmd} --lan)\n"
        )
    return "127.0.0.1"


def lan_ipv4_addresses() -> list[str]:
    """Private LAN addresses for operator hints (no secrets)."""
    import socket

    found: set[str] = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip.startswith("127."):
                continue
            found.add(ip)
    except Exception:
        pass
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        ip = probe.getsockname()[0]
        probe.close()
        if not ip.startswith("127."):
            found.add(ip)
    except Exception:
        pass
    return sorted(found)


def bind_exposure(*, host: str, port: int, service: str = "desk") -> dict[str, Any]:
    """Describe how a service is reachable — for logs and nervous glance."""
    local_url = f"http://127.0.0.1:{port}/"
    lan = host in ("0.0.0.0", "::")
    pref = read_bind(service)
    ips = lan_ipv4_addresses() if lan else []
    lan_urls = [f"http://{ip}:{port}/" for ip in ips]
    if service == "cast":
        warning = (
            "Cast LAN: read-only pulse for TV/phone. No desk control, no shell. "
            "Do not port-forward."
            if lan
            else None
        )
    else:
        warning = (
            "Desk LAN: full interactive dashboard (no login). Do not port-forward."
            if lan
            else None
        )
    return {
        "service": service,
        "host": host,
        "port": port,
        "mode": "lan" if lan else "localhost",
        "local_url": local_url,
        "lan_urls": lan_urls,
        "lan_opt_in": bool(pref.get("lan")) if lan else False,
        "read_only": service == "cast",
        "warning": warning,
    }


def print_bind_banner(*, host: str, port: int, service: str = "desk") -> None:
    info = bind_exposure(host=host, port=port, service=service)
    label = "Mag cast receiver" if service == "cast" else "Mag dashboard"
    print(f"{label} → {info['local_url']}")
    if info["mode"] == "lan":
        if service == "cast":
            print("  Cast LAN — read-only pulse (no desk/shell/API keys)")
        else:
            print("  ⚠ Desk LAN — full interactive UI (no auth)")
        print("  Do NOT port-forward this port to the internet")
        if info["lan_urls"]:
            for url in info["lan_urls"]:
                print(f"  receiver → {url}")
        else:
            print(f"  receiver → http://<your-pc-lan-ip>:{port}/  (check ipconfig)")


def in_container() -> bool:
    import os

    return os.environ.get("MAG_CONTAINER", "").strip().lower() in ("1", "true", "yes")

def republic_constitution() -> Path:
    """Resolve the Republic constitution path lazily.

    Never call Path.home() at import time: HOME can be unresolvable in
    service/daemon/sandbox contexts, and config is imported by the backend,
    the tool sandbox, and the mag daemon alike. One fragile import must not
    take every process down.
    """
    try:
        home = Path.home()
    except (RuntimeError, OSError):
        home = ROOT.parent
    return home / "Documents" / "projects" / "mycelial-republic" / "docs" / "CONSTITUTION.md"
