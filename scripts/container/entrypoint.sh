#!/bin/sh
set -eu

mkdir -p memory/biography memory/briefs memory/ingest logs state watch queue/handoff queue/results

echo "[mag-container] starting supervisor (backend :8000, dashboard :8765)"
echo "[mag-container] boundary: /app only; host mounts: memory watch logs state queue"
echo "[mag-container] drainer OFF by default (set MAG_DRAINER=1 to opt in)"

exec python mag_launch.py
