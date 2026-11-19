# Changelog

## 0.1.0 (unreleased)

- libadwaita light and dark palettes, following GNOME's colour scheme and accent colour live.
- Adwaita stylesheet: headerbar toolbar, buttons, entries, combo and spin boxes, check boxes,
  radio buttons, menus, tooltips, tabs, item views, headers, scroll bars, group boxes,
  progress bars, sliders, status bar.
- GNOME interface font when calibre has no font set.
- One header bar: the toolbar moves into the search row; icon-only buttons, a main menu
  (Preferences, All actions, Help, Restart), no separate Search button. "Small" toolbar icons
  are GNOME's 16 px.
- Experimental, opt-in: integrated title bar on X11/XWayland (frameless window with painted
  rounded corners and shadow, `_GTK_FRAME_EXTENTS`, GNOME window buttons).
- Optional Adwaita symbolic icon set (186 icons, light and dark), installed and restored from the
  plugin's Customize dialog. Nine symbols GNOME lacks are drawn in its style (books, tag, ++/−−,
  text colour, superscript, subscript, heading, horizontal rule); the cog is GNOME Settings'.
- View switcher (List / Grid / Bookshelf) as an AdwToggleGroup; Sort and Group by keep their space
  so switching never moves the header bar.
- Split buttons as AdwSplitButton; search field without placeholder, centred cluster with drag space;
  Preferences can be removed from the toolbar (it is in the main menu).
- Bookshelf view in flat Adwaita colours instead of wood.
- Tag browser as a navigation sidebar: sidebar colour, rounded rows, 16 px expanders, readable hover
  text, action-bar Configure/Find.
- Overlay scroll bars that fade out (calibre's style with SH_ScrollBar_Transient).
- Raised-bar shadows under the header bar and above the status bar while content is scrolled.
- Status bar: only the book count and selection, libadwaita padding.
- Layout popup as a libadwaita popover.
- Integrated title bar: anti-aliased corner overlay instead of masks, cursor fix, double-click
  detection, Wayland skipped.
- Book covers as libadwaita cards (soft shadow + hairline) in the grid and details panel.
- E-book viewer: Adwaita palettes and its "System" reading colour scheme (opt-out in Customize).
