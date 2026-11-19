#!/usr/bin/env bash
# Screenshot calibre in a throwaway profile (.dev/config + .dev/library), never the real one.
#   scripts/dev/run.sh <tag> <dark|light> [plain]      plain = without the Adwaita plugin
# Shots land in .dev/shots/<tag>-<name>.png. USER is changed so this instance does not
# talk to a calibre that is already running. calibre's single-instance lock is an abstract
# socket keyed on the uid; abstract sockets are per network namespace, hence --unshare=network.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TAG="$1"; MODE="$2"; PLAIN="${3:-}"
DEV="$ROOT/.dev"; CFG="$DEV/config"
mkdir -p "$CFG" "$DEV/shots"
run() { flatpak run --unshare=network --env=USER=adwaitadev --env=CALIBRE_CONFIG_DIRECTORY="$CFG" "$@"; }

ZIP="$("$ROOT/scripts/build.sh")"
SHOTS="$DEV/AdwaitaDevShots.zip"; rm -f "$SHOTS"
(cd "$ROOT/scripts/dev/shots" && zip -qr -X "$SHOTS" . -x '*__pycache__*')
run --command=calibre-customize com.calibre_ebook.calibre -a "$SHOTS" >/dev/null
if [ -n "$PLAIN" ]; then
  run --command=calibre-customize com.calibre_ebook.calibre -r 'Adwaita for calibre' >/dev/null 2>&1 || true
else
  run --command=calibre-customize com.calibre_ebook.calibre -a "$ZIP" >/dev/null
fi
python3 - "$CFG/gui.json" "$MODE" "$DEV/library" <<'PY'
import json, sys, os
path, mode, lib = sys.argv[1:]
d = json.load(open(path)) if os.path.exists(path) else {}
d['color_palette'] = mode
d.setdefault('toolbar_text', 'never')
d.setdefault('toolbar_icon_size', 'small')
open(path, 'w').write(json.dumps(d, indent=2))
g = os.path.join(os.path.dirname(path), 'global.py.json')
gd = json.load(open(g)) if os.path.exists(g) else {}
gd['library_path'] = lib
open(g, 'w').write(json.dumps(gd, indent=2))
PY
[ -e "$CFG/dynamic.pickle.json" ] || run --command=calibre-debug com.calibre_ebook.calibre \
    -c "from calibre.utils.config import dynamic; dynamic.set('welcome_wizard_was_run', True)" >/dev/null
run --env=ADWAITA_SHOT_DIR="$DEV/shots" --env=ADWAITA_SHOT_TAG="$TAG" \
    --env=ADWAITA_SHOT_ONLY="${ONLY:-}" --env=ADWAITA_SHOT_WIDTH="${WIDTH:-0}" --env=ADWAITA_CALIBRE_DEBUG=1 \
    --env=ADWAITA_SMOKE="${ADWAITA_SMOKE:-}" \
    com.calibre_ebook.calibre --with-library "$DEV/library" --no-update-check 2>&1 \
  | grep -vE 'QRhi|Vulkan|GPU vendor|^$' | tail -n "${TAIL:-40}"
