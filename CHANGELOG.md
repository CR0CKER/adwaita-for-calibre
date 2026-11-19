# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

- Edit metadata: one surface (calibre's scroll area no longer paints a darker panel inside a
  lighter frame); the fields start right under the cover actions instead of floating to the
  middle; *Languages* ends where the other fields do; the per-row buttons (clear, list, swap,
  copy) are dimmed until hovered or focused; the sort fields lose their green/red outline and
  show their state as a green check or amber warning icon.
- The status bar's Layout button is hidden: the header bar's toggles replace it, and its popup
  (Quickview, search bar, wide/narrow layout) opens from the ☰ main menu, *Layout…*, dropping
  from the top right.
- Edit metadata: no lines between the cover, form and comments columns (the splitters stay
  draggable).

## [0.1.0] - 2026-11-19

First release.

### Added

- libadwaita light and dark palettes that follow GNOME's colour scheme and accent colour live;
  the GNOME interface font when calibre has no font set.
- Adwaita stylesheet: buttons, entries, combo and spin boxes, check boxes, radio buttons, tabs,
  item views, headers, group boxes as cards, progress bars, sliders, tooltips; menus and popovers
  with libadwaita's outline and shadow; overlay scroll bars that fade out.
- One header bar: toolbar and search row merged; centred search with Virtual library and saved
  searches; List / Grid / Bookshelf view switcher; ☰ main menu; split buttons as AdwSplitButton;
  16 px "Small" toolbar icons; Preferences can be removed from the toolbar; sidebar toggles at
  both ends of the header bar for the tag browser and book details, which slide in and out; a
  cover-browser toggle beside the view switcher; the cover browser has 12 px of padding at the top.
- Pane | content | pane layout: tag browser and book details in the book area's colour, set off by
  hairline dividers instead of splitter grips; hidden panes take no space.
- Tag browser: rounded rows, 16 px expanders, readable hover text, action-bar Configure / Find.
- Raised-bar shadows under the header bar and above the status bar while content is scrolled; the
  book description in the details pane scrolls under a shade below the cover.
- Status bar with just the book count and selection; Layout popup as a popover.
- Book covers as libadwaita cards in the grid and the details pane (the details cover always
  keeps room for its shadow); flat Adwaita bookshelf view.
- Edit metadata: 20 px format buttons, cover and formats list as cards, single-border comments
  editor, GNOME success/error colours on the sort fields, icon/label spacing.
- Optional Adwaita symbolic icon set (186 icons, light and dark), installed and restored from the
  plugin's Customize dialog; nine symbols GNOME lacks are drawn in its style.
- Optional integrated title bar on X11/XWayland (frameless window, cached painted shadow,
  anti-aliased corners, `_GTK_FRAME_EXTENTS`, GNOME window buttons per `button-layout`).
- E-book viewer: Adwaita palettes and its "System" reading colour scheme (on by default).
- Dependabot configuration for the CI actions and the dev tooling (audit M2).
- **Restore calibre's look** button in the plugin's Customize dialog: puts back the previous icons,
  calibre's own colours and the viewer's colour scheme before an uninstall (audit M4).
- `scripts/smoke.sh`: a local behavioural smoke gate for the Qt layer (audit M3).
- A startup warning when calibre is newer than the release the plugin was tested with (audit L5).
- Release workflow: a version tag builds the zip, attests its provenance and drafts the release
  (audit L9).

### Changed

- Minimum calibre version is 9.0: the plugin uses calibre 9 internals (audit L1).
- Ruff now also runs its security (`S`) and blind-except (`BLE`) rules; the deliberate safety-net
  handlers are marked, the one silent handler logs (audit L2, L3).
- The pure modules are fully typed and checked with `mypy --strict`; ruff and mypy are hash-locked
  (audit L8).

### Fixed

- `LICENSE` was a short stub naming another project; it is now the full GPL-3.0 text, which
  GitHub also recognises (audit L10).
- The e-book viewer's settings are only changed while no viewer is open; an open viewer used to
  write its old settings back on exit (audit L4).
- The integrated title bar's X11 connection is closed when calibre quits, and X11 calls after
  that are skipped instead of reaching libX11 with a null display (audit L6).

[Unreleased]: https://github.com/CR0CKER/adwaita-for-calibre/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/CR0CKER/adwaita-for-calibre/releases/tag/v0.1.0
