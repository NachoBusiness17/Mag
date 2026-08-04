#!/usr/bin/env python3
"""Mag FastAPI backend — handles tool dispatch over HTTP.

The agent CLI (mag/agent_cli.py) makes HTTP requests to this server instead
of executing tools in-process. The backend owns the heavy lifting (filesystem,
shell, python sandbox) and returns a JSON Success/Failure envelope.

Run:
    python -m backend.server            # uvicorn on 127.0.0.1:8000
    python -m backend.server --port 9000
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

# Ensure project root on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from config import bind_host  # noqa: E402
from tools import TOOL_MAP, dispatch as tool_dispatch  # noqa: E402

DEFAULT_HOST = bind_host()
DEFAULT_PORT = 8000

app = FastAPI(
    title="Mag Tool Backend",
    description="HTTP tool dispatch for the Mag agent CLI.",
    version="1.0.0",
)


class RunTaskRequest(BaseModel):
    """Body for POST /run_task."""

    tool: str = Field(..., description="Tool name, e.g. read_file, run_shell")
    args: dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class RunTaskResponse(BaseModel):
    """Uniform Success/Failure envelope."""

    ok: bool
    tool: str
    result: dict[str, Any] | None = None
    error: str | None = None


@app.get("/health")
def health() -> dict[str, Any]:
    """Liveness probe."""
    return {
        "ok": True,
        "service": "mag-backend",
        "tools": sorted(TOOL_MAP),
        "version": "1.0.0",
    }


@app.post("/run_task", response_model=RunTaskResponse)
def run_task(req: RunTaskRequest) -> RunTaskResponse:
    """Dispatch a tool call. Returns Success/Failure JSON envelope."""
    if req.tool not in TOOL_MAP:
        return RunTaskResponse(
            ok=False,
            tool=req.tool,
            error=f"unknown tool: {req.tool}",
            result={"tools": sorted(TOOL_MAP)},
        )
    try:
        result = tool_dispatch(req.tool, req.args or {})
        ok = bool(result.get("ok", False))
        return RunTaskResponse(ok=ok, tool=req.tool, result=result)
    except Exception as e:  # noqa: BLE001
        return RunTaskResponse(
            ok=False,
            tool=req.tool,
            error=str(e),
            result={"exception": True},
        )


def main(argv: list[str] | None = None) -> int:
    # Windows detached spawn uses cp1252 stderr; startup print must not crash.
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    parser = argparse.ArgumentParser(description="Mag FastAPI tool backend")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--reload", action="store_true", help="uvicorn auto-reload")
    args = parser.parse_args(argv)

    import uvicorn

    print(f"Mag backend -> http://{args.host}:{args.port}/  (tools: {len(TOOL_MAP)})")
    uvicorn.run(
        "backend.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
