#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
#  Serendib Dome – local web build helper
#  Produces a static WebAssembly bundle in web-build/
#  that can be deployed on Vercel (or any static host).
#
#  Usage:
#    ./build_web.sh          – build to web-build/ and exit
#    ./build_web.sh --serve  – build then open a local preview
# ─────────────────────────────────────────────────────────
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

SERVE=false
[[ "$1" == "--serve" ]] && SERVE=true

# ── Ensure venv exists with all deps ─────────────────────
if [ ! -f ".venv/bin/python3" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q pygame numpy pygbag

# ── Build ─────────────────────────────────────────────────
echo ""
echo "▶  Building WebAssembly bundle..."
.venv/bin/python3 -m pygbag --build --width 1440 --height 840 .

echo ""
echo "✔  Build complete → web-build/"
echo "   Deploy the web-build/ directory to Vercel / any static host."

# ── Optional local preview ─────────────────────────────────
if $SERVE; then
    echo ""
    echo "▶  Starting local preview on http://localhost:8000 ..."
    echo "   Press Ctrl-C to stop."
    .venv/bin/python3 -m http.server 8000 --directory web-build
fi
