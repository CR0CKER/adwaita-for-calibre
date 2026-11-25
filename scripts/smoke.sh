#!/usr/bin/env bash
# Behavioural smoke gate for the Qt layer (audit M3). CI cannot run calibre, so this runs locally
# before every release: it starts calibre with the plugin in the throwaway dev profile, runs the
# harness steps that assert behaviour, and exits non-zero on any failed check.
#   scripts/smoke.sh            # dark mode
#   scripts/smoke.sh light
# Two passes: the default window (most steps), then the integrated title bar with a folder
# connected as a device for `configs` (calibre's other toolbar / menu bar / device setups).
# Frame budget for the grid repaint: SMOKE_FRAME_BUDGET_MS (default 30).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODE="${1:-dark}"
OUT="$(mktemp)"
trap 'rm -f "$OUT"' EXIT
export ADWAITA_SMOKE=1

smoke_pass() {  # smoke_pass <name> [VAR=value ...]: one calibre run; fails unless it ends OK
    local name="$1"; shift
    env "$@" TAIL=100000 WIDTH="${WIDTH:-1450}" \
        timeout 600 "$ROOT/scripts/dev/run.sh" smoke "$MODE" > "$OUT" 2>&1 || true
    grep -E '^SMOKE ' "$OUT" | sed "s/^SMOKE /SMOKE [$name] /" || true
    if ! grep -q '^SMOKE OK' "$OUT"; then
        echo "smoke: $name pass failed (or did not finish); log tail follows" >&2
        tail -40 "$OUT" >&2
        return 1
    fi
}

# Both passes with the Adwaita icon set installed, as users see it (ICONS=1 in the first pass
# installs it into the dev profile; it stays for the second).
smoke_pass window ICONS=1 \
    ONLY=main,jobsbutton,layoutmenu,views,toggles,sidetoggle,covertoggle,slide,coverroom,coverzoom,mdcheck,prefcheck,edges,perf,sidebar,details
smoke_pass configs INTEGRATED=1 CONFIGS_DEVICE=1 ONLY=main,configs
