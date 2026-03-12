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

# ── Patch pygbag to ignore .venv during archive scan ─────
# pygbag 0.9.x ignores /venv but not /.venv; patch in-place.
FILTER_PY="$(.venv/bin/python3 -c "import pygbag; import os; print(os.path.dirname(pygbag.__file__))")/filtering.py"
if [ -f "$FILTER_PY" ] && ! grep -q '/\.venv' "$FILTER_PY"; then
    echo "Patching pygbag filtering to ignore .venv ..."
    sed -i 's|/venv|/venv\n/.venv\n/env\n/.env|' "$FILTER_PY"
fi

# ── Stage only game source (keeps venv out of archive) ───
STAGE="$(mktemp -d)/serendib-dome"
mkdir -p "$STAGE"
echo "Staging source to $STAGE ..."
cp    "$SCRIPT_DIR/main.py"  "$STAGE/"
cp -r "$SCRIPT_DIR/game"     "$STAGE/"
cp -r "$SCRIPT_DIR/renderer" "$STAGE/"

# ── Build ─────────────────────────────────────────────────
echo ""
echo "▶  Building WebAssembly bundle..."
.venv/bin/python3 -m pygbag --build --width 1440 --height 840 "$STAGE"

# pygbag writes output to <stage>/build/web
if [ -d "$STAGE/build/web" ]; then
    rm -rf "$SCRIPT_DIR/web-build"
    cp -r "$STAGE/build/web" "$SCRIPT_DIR/web-build"
    echo "Copied build output to web-build/"
else
    echo "ERROR: Expected build output at $STAGE/build/web — check pygbag output above."
    exit 1
fi
rm -rf "$(dirname "$STAGE")"

echo ""
echo "✔  Build complete → web-build/"
echo "   Commit web-build/ and push – Vercel will serve it automatically."
echo "   (web-build/ is tracked in git; no Vercel build step needed.)"

# ── Optional local preview ─────────────────────────────────
if $SERVE; then
    echo ""
    echo "▶  Starting local preview on http://localhost:8000 ..."
    echo "   Press Ctrl-C to stop."
    .venv/bin/python3 -m http.server 8000 --directory web-build
fi

