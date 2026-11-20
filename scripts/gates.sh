#!/usr/bin/env bash
# Lint + tests. Check the exit code, not the output.
set -euo pipefail
cd "$(dirname "$0")/.."
RUFF="${RUFF:-$(command -v ruff || echo "$HOME/Claude/Apps/calibre/.venv/bin/ruff")}"
"$RUFF" check plugin scripts tests icons
# Type-check the modules that run without calibre (the rest imports calibre/Qt, absent in CI).
# Run from their own directories so mypy doesn't pull in the calibre-dependent package __init__.
PY="${PYTHON:-python3}"
(cd plugin && "$PY" -m mypy --strict --follow-imports=silent adwaita.py spin.py)
(cd icons && "$PY" -m mypy --strict mapping.py)
python3 -m unittest discover -s tests
