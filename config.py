"""Paths and limits for local_sovereign_agent."""
from __future__ import annotations

from pathlib import Path

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


def bind_host(default: str = "127.0.0.1") -> str:
    """Listen address for dashboard/backend. Set MAG_BIND_HOST=0.0.0.0 in containers."""
    import os

    raw = (os.environ.get("MAG_BIND_HOST") or default).strip()
    return raw or default


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
