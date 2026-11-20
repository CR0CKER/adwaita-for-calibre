#!/usr/bin/env bash
# Build the calibre plugin zip into dist/. Everything under plugin/ ships, minus caches and hidden
# files (the gates' type check leaves plugin/.mypy_cache behind).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(sed -n "s/^ *version = (\([0-9]*\), *\([0-9]*\), *\([0-9]*\)).*/\1.\2.\3/p" "$ROOT/plugin/__init__.py")"
mkdir -p "$ROOT/dist"
OUT="$ROOT/dist/AdwaitaForCalibre-$VERSION.zip"
rm -f "$OUT"
cd "$ROOT/plugin"
zip -qr -X "$OUT" . -x '*__pycache__*' '*.pyc' '.*' '*/.*'
# Nothing hidden or cached may ship: tool caches (mypy, ruff) land in plugin/ during the gates.
if unzip -Z1 "$OUT" | grep -E '(^|/)\.|__pycache__|\.pyc$' >&2; then
  echo "build: the zip contains hidden or cache files (listed above)" >&2
  exit 1
fi
echo "$OUT"
