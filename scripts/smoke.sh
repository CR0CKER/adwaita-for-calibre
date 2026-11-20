#!/usr/bin/env bash
# Behavioural smoke gate for the Qt layer (audit M3). CI cannot run calibre, so this runs locally
# before every release: it starts calibre with the plugin in the throwaway dev profile, runs the
# harness steps that assert behaviour, and exits non-zero on any failed check.
#   scripts/smoke.sh            # dark mode
#   scripts/smoke.sh light
# Frame budget for the grid repaint: SMOKE_FRAME_BUDGET_MS (default 30).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODE="${1:-dark}"
OUT="$(mktemp)"
trap 'rm -f "$OUT"' EXIT
export ADWAITA_SMOKE=1
TAIL=100000 ONLY=main,jobsbutton,layoutmenu,views,toggles,sidetoggle,covertoggle,slide,coverroom,mdcheck,prefcheck,edges,perf,sidebar,details WIDTH="${WIDTH:-1450}" \
    timeout 300 "$ROOT/scripts/dev/run.sh" smoke "$MODE" > "$OUT" 2>&1 || true
grep -E '^SMOKE ' "$OUT" || true
if grep -q '^SMOKE OK' "$OUT"; then
    exit 0
fi
echo "smoke: failed (or did not finish); full log follows" >&2
tail -40 "$OUT" >&2
exit 1
