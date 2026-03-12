#!/usr/bin/env bash
# ─────────────────────────────────────────
#  Serendib Dome – launch helper
#  Creates .venv on first run, then starts.
# ─────────────────────────────────────────
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Bootstrap venv if missing
if [ ! -f ".venv/bin/python3" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip -q
    .venv/bin/pip install -r requirements.txt -q
    echo "Dependencies installed."
fi

exec .venv/bin/python3 main.py "$@"
