#!/usr/bin/env bash
# Build the calibre plugin zip into dist/. Everything under plugin/ ships, minus caches.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(sed -n "s/^ *version = (\([0-9]*\), *\([0-9]*\), *\([0-9]*\)).*/\1.\2.\3/p" "$ROOT/plugin/__init__.py")"
mkdir -p "$ROOT/dist"
OUT="$ROOT/dist/AdwaitaForCalibre-$VERSION.zip"
rm -f "$OUT"
cd "$ROOT/plugin"
zip -qr -X "$OUT" . -x '*__pycache__*' '*.pyc'
echo "$OUT"
