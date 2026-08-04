"""Home-side cloud steering verification — prints Cursor Cloud secrets block."""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from config import ROOT

DEFAULT_PORT = 8765


def _tailscale_ipv4() -> str | None:
    exe = shutil.which("tailscale")
    if not exe:
        return None
    try:
        out = subprocess.check_output([exe, "ip", "-4"], text=True, timeout=5).strip()
        return out.splitlines()[0].strip() if out else None
    except (subprocess.SubprocessError, OSError, ValueError):
        return None


def _lan_ipv4_candidates() -> list[str]:
    """Non-loopback IPv4 addresses on this machine."""
    found: set[str] = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127."):
                found.add(ip)
    except OSError:
        pass
    # UDP connect trick — does not send packets; reveals preferred outbound iface IP
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            if not ip.startswith("127."):
                found.add(ip)
    except OSError:
        pass
    return sorted(found)


def suggest_public_urls(port: int = DEFAULT_PORT) -> list[str]:
    urls: list[str] = []
    ts = _tailscale_ipv4()
    if ts:
        urls.append(f"http://{ts}:{port}")
    for ip in _lan_ipv4_candidates():
        url = f"http://{ip}:{port}"
        if url not in urls:
            urls.append(url)
    return urls


def _probe_url(base: str, token: str = "", timeout: float = 4.0) -> dict[str, Any]:
    base = base.rstrip("/")
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    out: dict[str, Any] = {"mag_url": base, "reachable": False}
    try:
        req = urllib.request.Request(f"{base}/api/v1/health", headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            health = json.loads(r.read().decode("utf-8", errors="replace") or "{}")
        out["health"] = health
        out["reachable"] = r.status == 200 and bool(health) and health.get("status") != "down"
        req2 = urllib.request.Request(f"{base}/api/v1/surface", headers=headers)
        with urllib.request.urlopen(req2, timeout=timeout) as r2:
            out["surface"] = json.loads(r2.read().decode("utf-8", errors="replace") or "{}")
    except urllib.error.HTTPError as e:
        try:
            out["error"] = json.loads(e.read().decode("utf-8", errors="replace") or "{}")
        except json.JSONDecodeError:
            out["error"] = str(e)
    except Exception as e:
        out["error"] = str(e)
    return out


def cursor_secrets_block(public_url: str, token: str) -> str:
    lines = [
        "# Paste into Cursor Cloud → Environment secrets",
        f"MAG_PUBLIC_URL={public_url}",
        f"MAG_REMOTE_TOKEN={token}",
        "MAG_BRIDGE_TIMEOUT=300",
        "",
        "# Cloud agent first commands:",
        "python watch/cursor_bridge.py status",
        'python watch/cursor_bridge.py steer "<goal>" --mode delegate --provider deepseek --seat cursor-cloud --pack',
    ]
    return "\n".join(lines)


def verify_home(*, port: int = DEFAULT_PORT, probe_remote: bool = True) -> dict[str, Any]:
    """Run on Mag HQ — health, auth, suggested URLs, Cursor secrets snippet."""
    from mag.distributed_surface import auth_status, is_remote_bind, remote_token, surface_status

    token = remote_token()
    local = f"http://127.0.0.1:{port}"
    suggested = suggest_public_urls(port)
    preferred = (
        os.environ.get("MAG_PUBLIC_URL", "").strip()
        or (suggested[0] if suggested else local)
    )

    report: dict[str, Any] = {
        "ok": True,
        "schema": "cloud_steering_verify.v1",
        "local_probe": _probe_url(local),
        "auth": auth_status(),
        "remote_bind": is_remote_bind(),
        "surface": surface_status(),
        "suggested_public_urls": suggested,
        "preferred_public_url": preferred,
        "token_configured": bool(token),
        "checks": [],
    }

    if not report["local_probe"].get("reachable"):
        report["ok"] = False
        report["checks"].append(
            "FAIL: dashboard not reachable on 127.0.0.1 — run mag.cmd lab or launch_dashboard_lan.cmd"
        )
    else:
        report["checks"].append("OK: local dashboard health")

    if is_remote_bind() and not token:
        report["ok"] = False
        report["checks"].append(
            "FAIL: remote bind active but MAG_REMOTE_TOKEN unset — tablet/cloud writes will 401"
        )
    elif token:
        report["checks"].append("OK: MAG_REMOTE_TOKEN set")

    if not is_remote_bind():
        report["checks"].append(
            "WARN: dashboard loopback-only — cloud cannot reach home until MAG_BIND_HOST=0.0.0.0 "
            "(launch_dashboard_lan.cmd) or Tailscale"
        )

    if probe_remote and preferred and preferred != local:
        report["public_probe"] = _probe_url(preferred, token=token)
        if report["public_probe"].get("reachable"):
            report["checks"].append(f"OK: public URL reachable ({preferred})")
        else:
            report["checks"].append(
                f"WARN: public URL not reachable from this machine ({preferred}) — "
                "firewall/Tailscale may block; cloud may still work from outside"
            )

    if token and preferred:
        report["cursor_secrets"] = cursor_secrets_block(preferred, token)
    else:
        report["cursor_secrets"] = (
            "# Set MAG_REMOTE_TOKEN on home, re-run verify, then paste secrets block"
        )

    report["next_steps"] = [
        "1. git pull && mag.cmd doctor",
        "2. set MAG_REMOTE_TOKEN & launch_dashboard_lan.cmd (or Tailscale + mag.cmd lab)",
        "3. powershell -File scripts\\verify_cloud_steering.ps1",
        "4. Paste cursor_secrets into Cursor Cloud environment",
        "5. set MAG_DRAINER=1 && enable Drainer on dashboard for zero-check-in queue",
    ]
    return report


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Verify home Mag is ready for cloud steering")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--json", action="store_true", help="machine-readable only")
    ap.add_argument("--no-public-probe", action="store_true")
    ap.add_argument(
        "--write",
        default="",
        help="write report JSON to path (default state/cloud_steering_report.json if flag alone)",
    )
    args = ap.parse_args(argv)

    report = verify_home(port=args.port, probe_remote=not args.no_public_probe)

    out_path = args.write
    if out_path == "state/cloud_steering_report.json" or args.write == "1":
        out_path = str(ROOT / "state" / "cloud_steering_report.json")
    elif args.write:
        out_path = args.write

    if out_path:
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print("=== Mag cloud steering verify ===\n")
        for line in report.get("checks", []):
            print(f"  {line}")
        print(f"\nPreferred MAG_PUBLIC_URL: {report.get('preferred_public_url')}")
        print("\n--- Cursor Cloud secrets (copy below) ---\n")
        print(report.get("cursor_secrets", ""))
        if out_path:
            print(f"\n(report written to {out_path})")

    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
