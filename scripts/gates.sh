#!/usr/bin/env bash
# Lint + tests. Check the exit code, not the output.
set -euo pipefail
cd "$(dirname "$0")/.."
RUFF="${RUFF:-$(command -v ruff || echo "$HOME/Claude/Apps/calibre/.venv/bin/ruff")}"
"$RUFF" check plugin scripts tests icons
python3 -m unittest discover -s tests
