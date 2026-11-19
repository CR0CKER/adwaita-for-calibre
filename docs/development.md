# Development

## Layout

| Path | What |
|---|---|
| `plugin/adwaita.py` | Pure Python: libadwaita colour tokens, OKLab accent maths, template rendering, portal value parsing. Unit-tested |
| `plugin/adwaita.qss` | The stylesheet template. Tokens are names between two `@`; `img` is the indicator image folder |
| `plugin/main.py` | Qt glue: palette, stylesheet hook, popup translucency, font, accent watcher |
| `plugin/config.py` | The *Customize plugin* dialog: install / restore the icon set |
| `plugin/images/` | Adwaita SVGs recoloured at runtime for arrows and check marks |
| `plugin/icons/` | **Generated** by `scripts/build_icons.py` (committed so the zip builds without calibre) |
| `icons/mapping.py` | calibre icon name → Adwaita symbolic icon, plus what deliberately stays |
| `scripts/dev/` | Screenshot harness (dev-only plugin + `run.sh`), headless icon install test |

## How calibre is hooked

- `calibre.gui2.palette.dark_palette` / `light_palette` are module functions that
  `PaletteManager` calls each time the palette is (re)built, so replacing them is enough. The
  initial palette is built before plugins load, so `install()` ends with `refresh_palette()`.
- `PaletteManager.on_palette_change` calls `app.setStyleSheet()` with calibre's own rules every
  time, wiping anything set earlier. The plugin wraps it and appends its stylesheet. The wrapper
  catches exceptions, so a broken stylesheet leaves calibre's look instead of crashing.
- `PaletteManager.tree_view_hover_style` (the tag browser's gradient hover) is replaced.
- Rounded popups need `WA_TranslucentBackground` before their first show; an application event
  filter sets it on `QMenu`, `QTipLabel` and `QComboBoxPrivateContainer` at `Polish`.
- Accent and font come from `org.freedesktop.portal.Settings` over QtDBus (works in the Flatpak
  sandbox). The `SettingChanged` signal re-applies the accent live.
- Icons: calibre loads user themes from `<config>/icons-{any,dark,light}.rcc`, built with
  `calibre.utils.rcc.compile_icon_dir_as_themes`. The theme inherits `calibre-default`, so
  unmapped names fall through to calibre's icons. Dark/light-only user themes would shadow the
  `any` slot, so install moves all three aside (`*.pre-adwaita`).

Dead ends: `CALIBRE_USE_SYSTEM_THEME=1` gives plain Fusion (`PaletteManager.initialize` then
switches straight back to calibre's style), and `org.kde.KStyle.Adwaita` cannot load into the
Flathub build, which bundles its own Qt 6.10 on the freedesktop runtime.

## Dev loop

```bash
scripts/gates.sh                    # ruff + unit tests; check the exit code
scripts/dev/run.sh v5 dark          # screenshots -> .dev/shots/v5-*.png, then quits
scripts/dev/run.sh v5 light
scripts/dev/run.sh before dark plain   # same, without the plugin
ONLY=main,menu scripts/dev/run.sh x dark
```

`run.sh` uses a throwaway profile (`.dev/config`, `.dev/library`) and never touches the real
calibre profile. The dev library is built with `calibre-debug -e scripts/dev/mklib.py -- .dev/library`.
calibre's single-instance lock is an abstract Unix socket keyed on the uid, which would hand
the launch to an already-running calibre. Abstract sockets are per network namespace, so the dev
instance runs with `flatpak run --unshare=network`. A fresh profile also needs
`welcome_wizard_was_run`, which `run.sh` sets.

Screenshots are taken in-process with `QWidget.grab()` by the dev plugin in
`scripts/dev/shots/`, which works on Wayland without the screenshot portal. Its `flip` step
exercises the live light/dark switch.

## Icons

```bash
flatpak run --command=calibre-debug com.calibre_ebook.calibre \
    -e "$PWD/scripts/build_icons.py" -- "$PWD/plugin/icons"
```

Renders through calibre's Qt (the bundle has the SVG image plugin but no `qt.svg` module). The
SVGs are recoloured the way GTK does it, by compositing with `SourceIn`: Adwaita sources mix
`fill="#2e3436"`, other greys and paths without any fill, so string replacement misses parts.
Sources with filters, masks or embedded images render as a solid square;
`tests/test_icons.py` rejects them.

## Release

1. Bump `version` in `plugin/__init__.py`, update `CHANGELOG.md`.
2. `scripts/gates.sh`, rebuild the icons if the mapping changed, `scripts/dev/run.sh` in both modes.
3. `scripts/build.sh` → `dist/AdwaitaForCalibre-<version>.zip`, attach to a GitHub release.
