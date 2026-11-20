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
# '__layout__' is calibre's Layout popup (Quickview, search bar, wide/narrow, ...), whose status-bar
# button the header bar's toggles replace.
MAIN_MENU = ('Preferences', '__layout__', 'All GUI actions', None, 'Help', 'Restart')
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
    # GNOME's sidebar toggle at the start of the header bar: the tag browser.
    left = sidebar_toggle(gui, sb, 'tag_browser_button', 'sidebar-left.svg')
    first_bar = len(bm.main_bars) + 1  # index of the stretch inserted below
    if left is not None:
        lay.insertWidget(0, left)
        first_bar += 1

    # Overflow: actions that don't fit go into a visible ⋯ button right after each toolbar.
    for bar in bm.main_bars:
        slot = overflow_button(bar, sb)
        lay.insertWidget(lay.indexOf(bar) + 1, slot)
        first_bar += 1
    # calibre's bottom toolbar (optional): the header bar's side padding, clear of the corners.
    for bar in bm.child_bars:
        bar.setStyleSheet('QToolBar { border: 0px; padding: 6px 8px; }')

    # 2. Icon-only buttons in the row, like a header bar (tooltips keep the labels). calibre
    # rebuilds the search-row buttons (BarsManager.init_bars) with or without text as its own
    # "Show text in the buttons of the search bar" says; the first run turns that off
    # (toolbarprefs.py), so rebuilt buttons stay icon-only without help.
    icon_only(gui)
    disable_reveal_sweep()

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
    lay.insertStretch(first_bar, 1)  # after the toggle, the toolbars and the gap
    switcher = view_switcher(gui, sb, image_dir)
    if switcher is not None:
        lay.addSpacing(6)
        lay.addWidget(switcher)
    # The cover browser is a strip above any of the views, not a view itself: an on/off toggle
    # beside the switcher rather than a fourth segment.
    covers = sidebar_toggle(gui, sb, 'cover_browser_button', 'cover-browser.svg', 'adwaita_cover_toggle')
    if covers is not None:
        lay.addWidget(covers)
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
        if name == '__layout__':
            if getattr(gui, 'layout_button_menu', None) is not None:
                menu.addAction(QIcon.ic('layout.png'), 'Layout…', lambda: open_layout_popup(gui, btn))
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
    hide_status_layout_button(gui)
    # ... preceded by the toggle for the right-hand sidebar: book details, and before that the
    # running-jobs spinner while the status bar is hidden.
    from calibre_plugins.adwaita_for_calibre import statusbar
    jobs = statusbar.jobs_button(gui, sb)
    if jobs is not None:
        lay.addWidget(jobs)
    right = sidebar_toggle(gui, sb, 'book_details_button', 'sidebar-right.svg')
    if right is not None:
        lay.addWidget(right)
    lay.addWidget(btn)

    lay.setContentsMargins(8, 6, 8, 6)
    lay.setSpacing(6)
    sb._adwaita_merged = True
    allow_preferences_in_main_menu()
    bm.update_bars()
    debug('header bar merged')
    return True


def icon_only(gui):
    """Icon-only buttons in the header row (tooltips keep the labels), except the search-row
    buttons when calibre's own "Show text in the buttons of the search bar" setting is on."""
    from calibre.gui2 import gprefs
    sb, bm = gui.search_bar, gui.bars_manager
    keep_text = set()
    if gprefs['search_tool_bar_shows_text']:
        keep_text = set(getattr(bm.search_tool_bar, 'search_tool_bar_widgets', ()))
    for b in sb.findChildren(QToolButton):
        if b in keep_text or b.parent() in bm.main_bars:
            continue
        if b.toolButtonStyle() != Qt.ToolButtonStyle.ToolButtonIconOnly and not b.icon().isNull():
            if not b.toolTip():
                b.setToolTip(b.text().replace('&', ''))
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)


def disable_reveal_sweep():
    """calibre sweeps a grey band over the toolbar when a device connects (bars.RevealBar). It
    places the band with the toolbar's parent-relative geometry, which is off once the toolbar
    sits inside the header bar; header bars don't animate their content that way anyway."""
    from calibre.gui2.bars import RevealBar
    if not getattr(RevealBar, '_adwaita_off', False):
        RevealBar.start = lambda self, bar: None
        RevealBar._adwaita_off = True


def overflow_button(bar, parent):
    """A ⋯ header button listing the toolbar's actions that don't fit, shown only while some
    don't. Qt's own overflow button is fixed at calibre's 12 px extension size and draws no
    icon under this style, so it is shrunk to nothing.

    The toolbar keeps the width the header gives it even when its last buttons don't fit, so a
    button laid out after it would sit behind a gap. Instead the ⋯ floats right after the last
    visible button, and an empty slot of its width (returned, for the header's layout) reserves
    the room; the gap ends up after the ⋯, in the header's free space."""
    from qt.core import QEvent, QObject, QTimer, QWidget
    b = QToolButton(parent)
    b.setObjectName('adwaita_overflow')
    b.setAutoRaise(True)
    b.setToolTip('More actions')
    tracked_icon(b, 'view-more.svg')
    b.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    b.setStyleSheet('QToolButton::menu-indicator { image: none; width: 0; }')
    menu = QMenu(b)
    b.setMenu(menu)

    def hidden_actions():
        out = []
        for a in bar.actions():
            if a.isSeparator() or not a.isVisible():
                continue
            w = bar.widgetForAction(a)
            if w is None or not w.isVisible():
                if w is not None and w is getattr(bar, 'donate_button', None):
                    # Donate sits in the toolbar as a widget; a menu would take the widget
                    # itself, so list calibre's Donate action instead.
                    a = bar.donate_action
                out.append(a)
        return out

    def fill():
        menu.clear()  # the actions belong to calibre; clear() only detaches them
        for a in hidden_actions():
            menu.addAction(a)

    slot = QWidget(parent)
    slot.setObjectName('adwaita_overflow_slot')
    slot.setFixedWidth(b.sizeHint().width())
    slot.hide()
    pending = [False]

    def place():
        right = max((w.geometry().right() for a in bar.actions()
                     if (w := bar.widgetForAction(a)) is not None and w.isVisible()), default=0)
        x = bar.x() + right + 1 + bar.layout().spacing()
        b.move(x, bar.y() + (bar.height() - b.height()) // 2)
        b.raise_()

    def refresh():
        pending[0] = False
        try:
            show = bar.isVisible() and bool(hidden_actions())
            slot.setVisible(show)
            b.setVisible(show)
            if show:
                b.resize(b.sizeHint())
                place()
        except RuntimeError:
            pass  # shutting down

    def schedule():
        # After the toolbar's own layout pass, which decides what overflows.
        if not pending[0]:
            pending[0] = True
            QTimer.singleShot(0, refresh)

    watched = {QEvent.Type.Resize, QEvent.Type.Move, QEvent.Type.Show, QEvent.Type.Hide,
               QEvent.Type.LayoutRequest, QEvent.Type.ActionAdded, QEvent.Type.ActionRemoved,
               QEvent.Type.ActionChanged}

    class Watch(QObject):
        def eventFilter(self, obj, ev):
            if ev.type() in watched:
                schedule()
            return False

    b._adwaita_watch = w = Watch(b)
    bar.installEventFilter(w)
    menu.aboutToShow.connect(fill)
    ext = bar.findChild(QToolButton, 'qt_toolbar_ext_button')
    if ext is not None:
        ext.setMaximumWidth(0)
    bar._adwaita_overflow = b
    b._adwaita_refresh = schedule
    b.hide()
    schedule()
    return slot


def hide_status_layout_button(gui):
    """The status bar's Layout button: the header bar's toggles cover its common uses and the main
    menu opens its popup. calibre re-shows it when its layout preferences change (it calls
    setVisible from Python), so pin it hidden on the instance."""
    b = getattr(gui, 'layout_button', None)
    if b is None:
        return
    b.setVisible = lambda visible: QToolButton.setVisible(b, False)
    QToolButton.setVisible(b, False)


def open_layout_popup(gui, anchor):
    """calibre's Layout popup, dropped from the top right under the header bar instead of
    above the (hidden) status-bar button."""
    m = gui.layout_button_menu
    m.show()
    inner = m.inner
    bar = gui.search_bar
    y = bar.mapTo(gui, bar.rect().bottomLeft()).y() + 6  # 6 px below the header bar, like a popover
    right = anchor.mapTo(gui, anchor.rect().topRight()).x()
    inner.move(max(0, min(gui.width() - inner.width() - 8, right - inner.width())), y)


def sidebar_toggle(gui, parent, attr, icon, name='adwaita_sidebar_toggle'):
    """A header-bar toggle for one side pane (libadwaita: a flat toggle button with
    sidebar-show-symbolic). It clicks calibre's own layout button, so the pane state, its saved
    visibility, the Layout popup and the Shift+Alt shortcuts all stay the single source of truth;
    the toggle follows that button."""
    container = getattr(gui, 'layout_container', None)
    target = getattr(container, attr, None)
    if target is None:
        debug('no layout button', attr)
        return None
    b = QToolButton(parent)
    b.setObjectName(name)
    b._adwaita_target = target
    b.setCheckable(True)
    b.setAutoRaise(True)
    tracked_icon(b, icon)

    def sync(*args):
        b.blockSignals(True)
        b.setChecked(target.isChecked())
        b.blockSignals(False)
        tip = f'{"Hide" if target.isChecked() else "Show"} {target.label}'
        sc = getattr(target, 'shortcut', None)
        b.setToolTip(f'{tip} ({sc})' if sc else tip)

    def clicked(checked):
        if target.isChecked() != checked:
            target.click()
        sync()

    b.clicked.connect(clicked)
    target.toggled.connect(sync)
    sync()
    return b


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
