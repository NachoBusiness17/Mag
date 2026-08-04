#!/usr/bin/env bash
# Create Mag .env from example for local API keys (never commit .env).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EXAMPLE="$ROOT/.env.example"
ENVFILE="$ROOT/.env"

if [[ ! -f "$EXAMPLE" ]]; then
  echo "Missing $EXAMPLE" >&2
  exit 1
fi

if [[ ! -f "$ENVFILE" ]]; then
  cp "$EXAMPLE" "$ENVFILE"
  echo "Created $ENVFILE from .env.example"
else
  echo "Using existing $ENVFILE"
fi

echo ""
echo "Paste DEEPSEEK_API_KEY=sk-... into .env (local only — not GitHub)."
echo "Then: .venv/bin/python main.py providers"
echo ""

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  "$ROOT/.venv/bin/python" -c "
from models.env_load import load_dotenv
from pathlib import Path
import os
load_dotenv(Path('$ENVFILE'), override=True)
for k in ('DEEPSEEK_API_KEY','DEEPSEEK_OVERMIND_API_KEY','MAG_REMOTE_TOKEN'):
    v = os.environ.get(k,'').strip()
    print(f'{k}:', 'configured' if v else 'empty')
"
fi
