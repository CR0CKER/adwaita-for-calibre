# Development

## Layout

| Path | What |
|---|---|
| `plugin/adwaita.py` | Pure Python: libadwaita colour tokens, OKLab accent maths, template rendering, portal value parsing. Unit-tested |
| `plugin/adwaita.qss` | The stylesheet template. Tokens are names between two `@`; `img` is the indicator image folder |
| `plugin/main.py` | Entry point and Qt glue: palette, stylesheet hook, popup translucency and shadows, font, accent watcher, plugin-rendered icons, toolbar icon size, sidebar styling, plugin prefs |
| `plugin/headerbar.py` | Merges toolbar and search row into one header bar; view switcher; main menu; Preferences check |
| `plugin/frameless.py` | Optional integrated title bar (X11/XWayland) |
| `plugin/panes.py` | Pane \| content \| pane in one surface (`pane_bg`), hairline splitters, hidden panes 0 px |
| `plugin/slide.py` | Side panes slide in and out (snapshot overlay over calibre's final layout) |
| `plugin/shade.py` | Raised-bar shadows over the book area and the tag browser |
| `plugin/covers.py` | Cover card shadow (grid, details pane), cached |
| `plugin/bookshelf.py` | Flat Adwaita colours for the bookshelf view |
| `plugin/layoutmenu.py` | Layout popup as a popover |
| `plugin/metadata.py` | Edit metadata: one surface, top-aligned form, dimmed row buttons, sort-state icons, format icon size, cover card |
| `plugin/statusbar.py` | Status bar hidden by default (pref `show_status_bar`, Preferences → Interface entry), header-bar jobs spinner while hidden, status text without the version banner |
| `plugin/toolbarprefs.py` | First run: calibre's toolbar to Small / no text and the search-bar text off, once; restore. Qt-free and unit-tested |
| `plugin/spin.py` | libadwaita's spinner geometry (ported from `adw-spinner-paintable.c`), Qt-free and unit-tested |
| `plugin/viewer.py` | Palettes and "System" colour scheme for the e-book viewer |
| `plugin/config.py` | The *Customize plugin* dialog: icon set install/restore, integrated title bar, viewer |
| `plugin/images/` | Adwaita SVGs recoloured at runtime (arrows, check marks, window buttons, view switcher, sidebar toggles); `cover-browser-symbolic.svg` is drawn for this plugin |
| `plugin/icons/` | **Generated** by `scripts/build_icons.py`; committed so the zip builds without calibre |
| `icons/mapping.py` | calibre icon name → Adwaita symbolic icon (or `hicolor:` / `local:`), plus what stays |
| `icons/extra/` | The nine symbols drawn for this plugin, plus GNOME Settings' cog (CC0, vendored so builds and CI need only adwaita-icon-theme) |
| `scripts/dev/` | Screenshot/measurement harness (dev-only plugin + `run.sh`), dev library builders, headless icon install |

## How calibre is hooked

- **Palette and stylesheet.** `calibre.gui2.palette.dark_palette` / `light_palette` are module
  functions `PaletteManager` calls each time the palette is (re)built, so replacing them is
  enough. The initial palette is built before plugins load, so `install()` ends with
  `refresh_palette()`. `PaletteManager.on_palette_change` calls `app.setStyleSheet()` with
  calibre's own rules every time; the plugin wraps it, appends its stylesheet and re-applies the
  icons it renders itself (they are recoloured per light/dark). The wrapper catches exceptions,
  so a broken stylesheet leaves calibre's look instead of crashing.
- **Overlay scroll bars.** calibre's style (a Fusion proxy) supports `SH_ScrollBar_Transient` but
  only enables it on macOS; the plugin creates `CalibreStyle(1)`. The stylesheet must not style
  `QScrollBar`, or Qt's stylesheet engine draws them, permanently visible.
- **Popups.** Rounded popups need `WA_TranslucentBackground` before their first show (an event
  filter sets it at `Polish`). Menus get a transparent margin (QSS) into which the filter paints
  libadwaita's popover shadow, and are moved back by that margin when shown.
- **Accent and font** come from `org.freedesktop.portal.Settings` over QtDBus (works in the
  Flatpak sandbox); `SettingChanged` re-applies the accent live.
- **Plugin lifecycle.** `genesis()` runs before the main window exists (palette, style, frameless
  flags); `initialization_complete()` after it is shown (header bar, panes, shadows, status bar).
  The search row does not exist yet at `genesis()`.
- **Toolbar overflow and first run.** The header has no spare width for calibre's default
  toolbar (`headerdump`: the spacers are already 0 px). Qt's own overflow button is fixed at the
  style's 12 px `PM_ToolBarExtensionExtent` and draws no icon here, so it is shrunk to 0 px
  (`setMaximumWidth`) and `headerbar.overflow_button` adds a ⋯ that floats right after the last
  visible button, with an empty slot of its width in the layout. Its menu lists the hidden
  actions on `aboutToShow`; calibre's Donate is a widget in the toolbar, so its action is listed
  instead. `toolbarprefs.adopt` switches calibre's toolbar to Small / no text and the search-bar
  text off once (`toolbar_adopted`), remembering unset values as `None`; `restore` is part of
  "Restore calibre's look". calibre's device `RevealBar.start` is a no-op under the plugin
  (it used parent-relative geometry). The frame filter also drags on the menu bar's empty parts
  (`QMenuBar.actionAt` is `None`), and the bottom toolbar gets `padding: 6px 8px`.
- **Header bar.** The main toolbars (library and device; calibre shows one at a time) are moved
  into calibre's search row (`gui.search_bar`), which becomes the header bar. Sort and Group by
  keep their space when hidden (`setRetainSizeWhenHidden`), so switching views never moves
  anything. The view switcher drives calibre's own grid/bookshelf toggle buttons and follows
  `alternate_views.stack.currentChanged`; calibre switches the stack page *before* updating
  `current_view`, so map the stack index through `stack_positions`. The sidebar toggles click
  calibre's own layout buttons (`layout_container.tag_browser_button` / `book_details_button`)
  and follow their `toggled` signal, so calibre's saved visibility stays the only state. The
  cover browser gets the same kind of toggle beside the view switcher: in calibre it is a strip
  above any view, not a view, so it is on/off rather than a fourth segment. The status bar's
  Layout button is pinned hidden (`setVisible` overridden on the instance, since calibre
  re-shows it from Python when layout prefs change); ☰ → *Layout…* opens calibre's
  `LayoutMenu` and moves its inner card under the header bar at the right.
- **Status bar.** Hidden after the header bar merges (`statusbar.apply`, pref `show_status_bar`,
  default off; kept visible if the merge fails). *Show status bar* is a checkable entry in
  calibre's Preferences menu (`iactions['Preferences'].preferences_menu`, which ☰ shows), in the
  submenu holding `action_map['Look & Feel']` (Interface). calibre builds those submenus in its
  own `initialization_complete`, possibly after ours, so the entry is placed on the menu's first
  `aboutToShow`. It saves the pref and re-reads the bar on the submenu's `aboutToShow`. Its
  shortcut (Ctrl+Shift+S, `statusbar.SHORTCUT_ID`) is registered with `gui.keyboard` in our
  `initialization_complete`; calibre assigns keys in `keyboard.finalize()` right after all
  plugins' `initialization_complete`. The action is added to the main window so the key works
  with the menu closed, and it toggles from the bar's own state, not the (then stale) check mark. The jobs
  button (`adwaita_jobs_button`) follows `job_manager.job_added` / `job_done`, connected after
  calibre's `JobsButton`, whose `jobs()` count and `toggle()` (the Jobs list) it reuses; it shows
  only while jobs run and the bar is hidden.
- **Spinner.** calibre's `ProgressIndicator` looked choppy: frames arrive every 16 ms, but its
  motion holds the arc for half of each cycle, then swings it 315° in a quarter cycle (~20° a
  frame at the peak) in whole-degree steps. `statusbar.Spinner` draws libadwaita's instead
  (`spin.py`: float angles, both ends easing continuously, at most ~9.6° a frame, a 15 % track)
  from a `QVariantAnimation`. The `spinner` harness step (dev only) logs paint gaps and the cost
  of a repaint (about 2 ms with the header bar behind it).
- **Toolbars & menus preferences.** Invisible actions (this plugin's, any plugin's) must list
  `searchbar` in `dont_add_to`, or that page crashes on `None.replace`. Its Preferences check
  accepts the main menu while the header bar is merged.
- **Integrated title bar** (`frameless.py`, X11 only). Frameless + translucent must be set
  before the native window exists (an existing X11 window keeps its opaque visual: the margin
  renders black). `_GTK_FRAME_EXTENTS` is set through libX11 via ctypes; **every** ctypes call
  needs `argtypes` or the 64-bit `Display*` is truncated and libX11 segfaults. The window
  background and shadow are a cached pixmap drawn clipped to the dirty region; a click-through
  overlay erases the four corners anti-aliased (masks cannot be) and only paints when a corner
  is dirty. The window manager takes the pointer after `startSystemMove`, so a double-click is
  not delivered.
- **Pane slide** (`slide.py`). Re-running calibre's layout per animation frame costs 70-80 ms a
  frame here (the book grid or list re-lays out and the whole window repaints), so the slide is
  played on two grabs of the central container (before; after one event-loop turn) composed by an
  overlay, at 10-15 ms a frame, while the real widgets are already in their final place. A pane
  that was just shown lays its cover out lazily, so `BookDetails.do_layout` runs before the second
  grab; that re-enters `relayout`, which `_adwaita_starting` lets through. Any failure finishes
  the overlay, so it can never stay up. Wide layout only; respects calibre's *Disable animations*.
  `ADWAITA_SLIDE_TIMING=1` prints per-frame timings.
- **Details cover.** The cover view sits in calibre's `QSplitter`, which resizes it without
  calling `do_layout`, so a size computed for an earlier, larger view survives. `covers.py`
  therefore clamps the cover to the view minus `SHADOW_ROOM` in `paintEvent` too, or the card
  shadow is clipped at the view's edges (visible in light mode).
- **Pane scroll shades** (`shade.ScrollAreaShades`). They take the viewport's top and bottom but
  snap to the pane's edges (sides, top under the header bar, bottom on the bottom bar), so the
  tree's frame and the details insets do not leave them short or low; a gap wider than
  `EDGE_SNAP` (a cover beside or above the text) is left alone. The
  details shades are children of the pane's *parent*: `BookDetails` is a `QSplitter`, which
  adopts every child widget as a new section (an overlay parented to it ends up as a 0-px pane).
  The harness steps `sidebar` and `details` check the span and the top/bottom edges.
- **Cover browser.** calibre's PictureFlow (C++) sizes its covers from its own height and draws
  the front cover flush with its top edge, with no padding setting. `panes.py` moves it down by
  `COVER_BROWSER_GAP` after each wide or narrow layout and fills the strip above with a black
  pad, so the black area still starts under the header bar with the covers inset. The black is
  hard-coded in that C++ (reflections and side covers fade to black), so it cannot follow the
  theme.
- **Edit metadata** (`metadata.py`, wrapped `MetadataSingleDialogBase.__init__`). calibre's
  `ScrollArea` viewport and content auto-fill the window colour over the dialog colour: both
  stop auto-filling. In the default layout (`MetadataSingleDialog`) the middle grid has two
  expanding spacers (above Rating, above Download metadata); the upper one becomes fixed 12 px.
  *Languages* spans the clear-button column; its span is reduced by one. Icon-only tool buttons
  directly in the form widgets get a `QGraphicsOpacityEffect` at 0.55, full on Enter/FocusIn.
  Sort fields: `widgets.stylesheet_for_lineedit` returns no border and
  `widgets.update_status_actions` (looked up at call time by `LineEditIndicators`) recolours
  the check / warning actions to `status-ok.svg` / `status-warning.svg`.
- **Panes.** `SplitterHandle.COLLAPSED_SIZE = 0`: calibre's 2 px stub for a hidden pane is a strip
  the content cannot scroll under; above the book area it read as a line under the header bar.
- **Icons.** calibre loads user themes from `<config>/icons-{any,dark,light}.rcc`, built with
  `calibre.utils.rcc.compile_icon_dir_as_themes`. The theme inherits `calibre-default`, so
  unmapped names fall through. Dark/light-only user themes would shadow the `any` slot, so
  install moves all three aside (`*.pre-adwaita`).
- **Version drift.** `main.TESTED_WITH` is the calibre release last tested; a newer calibre logs a
  one-line warning at startup.
- **Viewer.** It loads no interface plugins and its `viewer.html`/`viewer.js` are
  `allow_user_override=False`. Two shared settings reach it: the custom palettes in `gprefs`
  (stored under the key `adwaita`, so a user's `__current__` palette is untouched) and the
  viewer's built-in "System" colour scheme, which reads Base/Text/Link from that palette. The
  viewer writes its whole session back when it closes, so its settings are only changed while its
  single-instance lock (`calibre_viewer`) is free. Customize → *Restore calibre's look* undoes
  everything (icons, palettes, viewer scheme) before an uninstall.

Dead ends: `CALIBRE_USE_SYSTEM_THEME=1` gives plain Fusion; `org.kde.KStyle.Adwaita` cannot load
into the Flathub build (bundled Qt 6.10 on the freedesktop runtime). Qt's Wayland Adwaita
decoration hard-codes Cantarell 10 for the title (theme `TitleBarFont` is unset), which is why
the README recommends XWayland.

## Dev loop

```bash
scripts/gates.sh                          # ruff, mypy --strict, unit tests; check the exit code
scripts/smoke.sh [dark|light]             # behavioural smoke gate (local, needs calibre)
scripts/dev/run.sh v5 dark                # screenshots -> .dev/shots/v5-*.png, then quits
scripts/dev/run.sh v5 light
scripts/dev/run.sh before dark plain      # same, without the plugin
ONLY=main,menu WIDTH=1450 scripts/dev/run.sh x dark
```

Steps in `scripts/dev/shots/main.py`: `main`, `jobsbutton` (hidden status bar, Preferences → Interface entry, Ctrl+Shift+S, jobs spinner; `run.sh` clears `show_status_bar` before each run so the default is what is tested), `spinner` (paint gaps and cost), `focus`, `statusbar`, `hover`, `layoutmenu`,
`scrolled`, `sidebar`, `perf` (times grid and window repaints), `edges` (lists widgets at the
header's edge), `toggles` (hides/shows panes), `menu`, `menus` (every menu), `grid`, `prefs`,
`metadata`, `news`, `details` (scrolled book description), `sidetoggle` (header-bar sidebar
toggles), `covertoggle` (cover-browser toggle), `slide` (pane slide; `SLIDE_MID_MS`, `SLIDE_LIST`), `coverroom` (details cover shadow
not clipped), `mdcheck` (Edit metadata tidy-up; needs a selected book, so run after `main`), `flip` (live light/dark switch), `views`, `closebtn`, `prefcheck`.

**Other calibre setups** (`configs` step, the second pass of `smoke.sh`). It switches calibre live, the
way its preferences do (`gprefs` + `bars_manager.init_bars()` / `update_bars()` /
`apply_settings()`), through a classic menu bar, a bottom toolbar (`action-layout-toolbar-child`,
with and without the status bar), every `toolbar_icon_size` × `toolbar_text`, window widths
1200/1000/800, Donate in the toolbar, extra search-row actions, narrow layout, Quickview, and a
connected device (default and a long device toolbar). Each setup prints a `CFG {json}` line
(header, menu bar, toolbars with hidden actions and the overflow button, RevealBar, search width,
labelled header buttons), saves `cfg-<setup>.png`, and checks:

- the toolbars stay in the header; actions that don't fit are listed by the ⋯ button, which
  shows exactly then, right after the last visible button, and Qt's own overflow button takes
  no space;
- header buttons are icon-only, unless calibre's search-bar text setting is on (`searchtext-on`),
  when exactly the search-row buttons keep their text;
- no device reveal band;
- integrated title bar: the rounded corners stay transparent, an empty part of the menu bar
  drags the window (`frame.start_move` is intercepted) and a menu title doesn't;
- the bottom toolbar's buttons are inset at least 8 px.

It then restores every pref it changed (unset ones are unset again). `headerdump` (dev only)
prints every item of the header's layout with its width, size hints and policy.

    ADWAITA_SMOKE=1 INTEGRATED=1 CONFIGS_DEVICE=1 TAIL=100000 ONLY=main,configs \
        scripts/dev/run.sh cfg dark          # add `plain` for stock calibre, for comparison

`INTEGRATED=1` turns the integrated title bar on for that run (otherwise off). `CONFIGS_DEVICE=1`
makes `.dev/device/` (a copy of one dev-library EPUB) and connects to it as a device with calibre's
*Connect to folder*; no real device is involved. `FIRSTRUN=1` starts as a fresh calibre (its own
toolbar and search-bar text defaults, the plugin's first-run flag cleared); the `firstrun` step
checks the switch to Small / no text and that `toolbarprefs.restore` unsets them again.
`ICONS=1` installs the Adwaita icon set into the dev profile (as Customize plugin → *Use Adwaita
icons* does), `ICONS=0` restores calibre's; unset leaves the profile as it is. `smoke.sh` runs
with `ICONS=1`, so its screenshots show the icons users see.

`run.sh` uses a throwaway profile (`.dev/config`, `.dev/library`) and never touches the real
calibre profile. Build the library with `calibre-debug -e scripts/dev/mklib.py -- .dev/library`
and, for scrolling tests, add more with `scripts/dev/more_books.py`. calibre's single-instance
lock is an abstract Unix socket keyed on the uid; abstract sockets are per network namespace, so
the dev instance runs with `flatpak run --unshare=network`. A fresh profile also needs
`welcome_wizard_was_run`, which `run.sh` sets. Install the current icons into the dev profile with
`calibre-debug -e scripts/dev/icons_test.py -- <zip> $PWD install`.

**Smoke gate** (`scripts/smoke.sh`). CI cannot run calibre, so the Qt layer is checked locally:
the harness steps `jobsbutton`, `views`, `toggles`, `prefcheck`, `edges` and `perf` assert behaviour (`SMOKE ok`
/ `SMOKE FAIL` lines; the run exits non-zero on any failure): the view switcher follows clicks and
shortcuts and the header bar does not move, the status bar starts hidden and Preferences → Interface → *Show status bar*
toggles and saves it, the jobs spinner shows exactly while a job runs with the bar hidden, hidden panes free their space and come back (also
through the header bar's sidebar toggles, which must follow the panes), the
toolbar saves without Preferences, the book area starts right under the header bar with no strip
in between, and a grid repaint stays within `SMOKE_FRAME_BUDGET_MS` (default 30). A second pass
runs `configs` with the integrated title bar and a folder device (see *Other calibre setups*).
The first-run switch is checked separately: `FIRSTRUN=1 ONLY=main,firstrun scripts/dev/run.sh`.
Run it before every release and after touching the Qt modules.

**Type checking.** `mypy --strict` covers the modules that import neither calibre nor Qt
(`plugin/adwaita.py`, `plugin/spin.py`, `plugin/toolbarprefs.py`, `icons/mapping.py`); the rest cannot be imported in CI. ruff and mypy are
hash-locked in `requirements-dev.txt`, compiled from `requirements-dev.in` with
`uv pip compile --generate-hashes`.

Screenshots are taken in-process with `QWidget.grab()`, which works on Wayland without the
screenshot portal. Programmatic scrolling of the book *list* does not render in grabs; the tag
browser and grid do. Measure user-reported artefacts in their screenshots' pixels
(`magick … txt:-`) before changing code.

## Icons

```bash
flatpak run --command=calibre-debug com.calibre_ebook.calibre \
    -e "$PWD/scripts/build_icons.py" -- "$PWD/plugin/icons"
```

Renders through calibre's Qt (the bundle has the SVG image plugin but no `qt.svg` module). SVGs
are recoloured the way GTK does it, by compositing with `SourceIn`: Adwaita sources mix
`fill="#2e3436"`, other greys and paths without any fill. Sources with filters, masks or embedded
images render as a solid square; `tests/test_icons.py` rejects them. Off-centre glyphs listed in
`RECENTRE` are re-centred.

## Release

1. Bump `version` in `plugin/__init__.py` and `TESTED_WITH` in `plugin/main.py` if a newer calibre
   was tested; move the CHANGELOG's *Unreleased* entries under the new version.
2. `scripts/gates.sh`, `scripts/smoke.sh dark` and `scripts/smoke.sh light`; rebuild the icons if
   the mapping changed.
3. Merge through a PR, then push the tag `vX.Y.Z` on `main`. `.github/workflows/release.yml`
   checks the tag against the plugin version, builds the zip, attests its build provenance and
   creates a **draft** release. Write the notes from the CHANGELOG, then publish.
4. Once the plugin is in calibre's plugin index: replace the zip on the first post of the MobileRead
   thread with the release zip (exactly one zip there). calibre's *Get new plugins* downloads from
   that post, not from GitHub.

No SBOM: the zip bundles no third-party code; the bundled GNOME icons are credited in the README.
