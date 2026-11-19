# Changelog

## 0.1.0 (unreleased)

First release.

### Look

- libadwaita light and dark palettes, following GNOME's colour scheme and accent colour live;
  GNOME interface font when calibre has no font set.
- Adwaita stylesheet: buttons, entries, combo and spin boxes, check boxes, radio buttons, tabs,
  item views, headers, group boxes as cards, progress bars, sliders, tooltips.
- Menus and popovers with libadwaita's outline and shadow.
- Overlay scroll bars that fade out.
- Book covers as libadwaita cards (soft shadow and hairline) in the grid and the details pane.
- Bookshelf view in flat Adwaita colours instead of wood.

### Layout

- One header bar: toolbar and search row merged; centred search with Virtual library and saved
  searches; List / Grid / Bookshelf view switcher; ☰ main menu; split buttons as AdwSplitButton;
  16 px "Small" toolbar icons; Preferences can be removed from the toolbar.
- Sidebar | content | sidebar: tag browser and book details as GNOME sidebars, hairline dividers
  instead of splitter grips, hidden panes take no space.
- Tag browser: rounded rows, 16 px expanders, readable hover text, action-bar Configure / Find.
- Raised-bar shadows under the header bar and above the status bar while content is scrolled.
- Status bar with just the book count and selection.
- Layout popup as a popover.
- Edit metadata: 20 px format buttons, cover and formats list as cards, single-border comments
  editor, GNOME success/error colours on the sort fields, icon/label spacing.

### Optional

- Adwaita symbolic icon set (186 icons, light and dark), installed and restored from the plugin's
  Customize dialog. Nine symbols GNOME lacks are drawn in its style; the cog is GNOME Settings'.
- Integrated title bar on X11/XWayland: frameless window with cached painted shadow and
  anti-aliased corners, `_GTK_FRAME_EXTENTS`, GNOME window buttons per `button-layout`.
- E-book viewer: Adwaita palettes and its "System" reading colour scheme (on by default).
