"""Load Mag project .env into process env (does not override existing)."""
from __future__ import annotations

from pathlib import Path

from config import ROOT


def load_dotenv(path: Path | None = None, *, override: bool = False) -> dict[str, str]:
    import os

    path = path or (ROOT / ".env")
    loaded: dict[str, str] = {}
    if not path.is_file():
        return loaded
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if not k:
            continue
        if not override and os.environ.get(k):
            continue
        if v:
            os.environ[k] = v
            loaded[k] = "(set)"
    return loaded
