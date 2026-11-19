"""Merge calibre's toolbar and search row into one GNOME-style header bar.

calibre stacks its main toolbar (a QToolBar on the QMainWindow) above a separate search row
(`gui.search_bar`, a QFrame with an HBox layout). GNOME apps use a single header bar: actions on
the left, search in the middle, a main menu on the right.

The toolbars (library and device variants; calibre shows one at a time) are moved *into* the
search row rather than the other way round. calibre still owns them: `BarsManager.update_bars`
keeps toggling which one is visible, and `init_bars` refills them in place.
"""

from calibre_plugins.adwaita_for_calibre.main import debug, tracked_icon
from qt.core import QFrame, QIcon, QMenu, QSizePolicy, Qt, QToolButton

# Main menu entries (calibre action names), in order; None is a separator.
MAIN_MENU = ('Preferences', 'All GUI actions', None, 'Help', 'Restart')
SEARCH_MAX_WIDTH = 880
SEARCH_STRETCH = 4  # logical px; GNOME header-bar search entries are roughly this wide


def merge(gui, image_dir):
    sb = getattr(gui, 'search_bar', None)
    bm = getattr(gui, 'bars_manager', None)
    lay = getattr(sb, '_layout', None)
    if sb is None or bm is None or lay is None or getattr(sb, '_adwaita_merged', False):
        return False

    # 1. Toolbars into the start of the search row.
    for i, bar in enumerate(bm.main_bars):
        gui.removeToolBar(bar)
        bar.setParent(sb)
        bar.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        lay.insertWidget(i, bar)
    sep = QFrame(sb)
    sep.setObjectName('adwaita_headerbar_gap')
    sep.setFixedWidth(12)
    lay.insertWidget(len(bm.main_bars), sep)

    # 2. Icon-only buttons in the row, like a header bar (tooltips keep the labels).
    for b in sb.findChildren(QToolButton):
        if b.parent() is sb or b.parent() not in bm.main_bars:
            if b.toolButtonStyle() != Qt.ToolButtonStyle.ToolButtonIconOnly and not b.icon().isNull():
                if not b.toolTip():
                    b.setToolTip(b.text().replace('&', ''))
                b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

    # GNOME searches on Enter / as you type; the separate Search button is redundant there.
    search_button = getattr(sb, 'search_button', None)
    if search_button is not None:
        search_button.setVisible(False)

    # Everything search-related (Virtual library, the field, Highlight, the configurable
    # search-bar buttons) forms one centred cluster with empty space on both sides, as in GNOME
    # header bars. The empty space is also where the window can be dragged (frameless.py).
    search = getattr(gui, 'search', None)
    if search is not None:
        search.setMaximumWidth(SEARCH_MAX_WIDTH)
        le = getattr(search, 'line_edit', None) or search.lineEdit()
        if le is not None:
            le.setPlaceholderText('')  # calibre sets it once, in its init
        # calibre puts Virtual library (and Sort / Group by) left of the field and the
        # configurable buttons right of it; GNOME keeps such controls together after the field.
        after = lay.indexOf(search) + 1
        for w in (getattr(gui, 'virtual_library', None), getattr(gui, 'clear_vl', None)):
            if w is not None and lay.indexOf(w) >= 0:
                lay.removeWidget(w)
                after = lay.indexOf(search) + 1 + _moved(sb)
                lay.insertWidget(after, w)
                sb._adwaita_moved = _moved(sb) + 1
    lay.insertStretch(len(bm.main_bars) + 1, 1)  # after the toolbars and the gap
    switcher = view_switcher(gui, sb, image_dir)
    if switcher is not None:
        lay.addSpacing(6)
        lay.addWidget(switcher)
    # Sort and Group by only show in the grid/bookshelf views. Next to the switcher, keeping
    # their space while hidden: the empty slot merges with the free space before the main menu,
    # so switching views never resizes the search field or moves other buttons.
    for w in (getattr(sb, 'sort_button', None), getattr(sb, 'group_by_button', None)):
        if w is not None and lay.indexOf(w) >= 0:
            lay.removeWidget(w)
            sp = w.sizePolicy()
            sp.setRetainSizeWhenHidden(True)
            w.setSizePolicy(sp)
            lay.addWidget(w)
    lay.addStretch(1)                             # before the main menu, added below
    if search is not None:
        # Spacers have stretch 1; the field gets SEARCH_STRETCH so it takes most of the free
        # width (up to SEARCH_MAX_WIDTH) instead of staying at its size hint.
        lay.setStretchFactor(search, SEARCH_STRETCH)

    # 3. Main menu at the end.
    btn = QToolButton(sb)
    btn.setObjectName('adwaita_main_menu')
    btn.setIcon(QIcon.ic('context_menu.png'))
    btn.setToolTip('Main menu')
    btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    btn.setAutoRaise(True)
    menu = QMenu(btn)
    for name in MAIN_MENU:
        if name is None:
            menu.addSeparator()
            continue
        ia = gui.iactions.get(name)
        if ia is None:
            continue
        qa = ia.qaction
        if name == 'All GUI actions' and qa.menu() is not None:
            sub = menu.addMenu(qa.icon(), 'All actions')
            src = qa.menu()
            sub.aboutToShow.connect(lambda src=src, sub=sub: _mirror(src, sub))
        else:
            menu.addAction(qa)
    btn.setMenu(menu)
    btn.setStyleSheet('QToolButton::menu-indicator { image: none; width: 0; }')
    lay.addWidget(btn)

    lay.setContentsMargins(8, 6, 8, 6)
    lay.setSpacing(6)
    sb._adwaita_merged = True
    allow_preferences_in_main_menu()
    bm.update_bars()
    debug('header bar merged')
    return True


# (calibre view key, calibre button attribute, icon file, tooltip)
VIEWS = (
    (None, None, 'view-list.svg', 'Book list'),
    ('grid', 'grid_view_button', 'view-grid.svg', 'Cover grid (Alt+Shift+G)'),
    ('bookshelf', 'bookshelf_view_button', 'view-bookshelf.svg', 'Bookshelf (Alt+Shift+H)'),
)


def view_switcher(gui, parent, image_dir):
    """libadwaita's AdwToggleGroup for List / Grid / Bookshelf.

    Switching goes through calibre's own grid and bookshelf toggle buttons, so the sort and
    group-by buttons and the remembered view behave exactly as with calibre's Layout button.
    The group follows the view stack, so the keyboard shortcuts update it too."""
    from qt.core import QButtonGroup, QHBoxLayout

    av = getattr(gui.library_view, 'alternate_views', None)
    if av is None or av.stack is None:
        return None
    box = QFrame(parent)
    box.setObjectName('adwaita_view_switcher')
    row = QHBoxLayout(box)
    row.setContentsMargins(3, 3, 3, 3)
    row.setSpacing(0)
    group = QButtonGroup(box)
    group.setExclusive(True)
    buttons = {}
    for key, attr, icon, tip in VIEWS:
        if key is not None and (key not in av.views or getattr(gui, attr, None) is None):
            continue
        b = QToolButton(box)
        b.setObjectName('adwaita_view_toggle')
        b.setCheckable(True)
        b.setAutoRaise(True)
        tracked_icon(b, icon)  # recoloured on live light/dark switches
        b.setToolTip(tip)
        group.addButton(b)
        row.addWidget(b)
        buttons[key] = b
        b.clicked.connect(lambda checked=False, key=key: switch_view(gui, key))

    def sync(*args):
        # calibre switches the stack page *before* updating av.current_view, so read the
        # stack index (currentChanged fires in between) and map it back to the view key.
        index = av.stack.currentIndex()
        current = next((k for k, pos in av.stack_positions.items() if pos == index), None)
        b = buttons.get(current)
        if b is not None and not b.isChecked():
            b.setChecked(True)

    av.stack.currentChanged.connect(sync)
    sync()
    box._adwaita_buttons = buttons
    return box


def switch_view(gui, key):
    av = gui.library_view.alternate_views
    toggles = {k: getattr(gui, attr, None) for k, attr, _i, _t in VIEWS if attr}
    if key is None:
        for b in toggles.values():
            if b is not None and b.isChecked():
                b.setChecked(False)  # calibre: toggled(False) -> show the book list
        return
    b = toggles.get(key)
    if b is None or av.current_view is av.views.get(key):
        return
    if b.isChecked():
        # calibre leaves a button checked when another view replaced it; reset it first.
        b.setChecked(False)
    b.setChecked(True)


def allow_preferences_in_main_menu():
    """calibre's Toolbars & menus page refuses to save unless Preferences is in the toolbar or
    the classic menu bar. With the header bar merged, Preferences is always in the main menu, so
    the check may also pass when it is in neither."""
    from calibre.gui2.preferences.toolbar import ConfigWidget

    if getattr(ConfigWidget, '_adwaita_patched', False):
        return
    original = ConfigWidget.commit

    def commit(self, *args):
        model = self.models['menubar'][1]
        has_action = model.has_action
        model.has_action = lambda name: True if name == 'Preferences' else has_action(name)
        try:
            return original(self, *args)
        finally:
            model.has_action = has_action

    ConfigWidget.commit = commit
    ConfigWidget._adwaita_patched = True


def _moved(sb):
    return getattr(sb, '_adwaita_moved', 0)


def _mirror(src, dest):
    """'All GUI actions' builds its menu lazily on aboutToShow; fill ours from it."""
    src.aboutToShow.emit()
    dest.clear()
    for a in src.actions():
        dest.addAction(a)
