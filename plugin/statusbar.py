"""The status bar: hidden by default, and its text trimmed when shown.

Hidden: GNOME apps have no status bar. Preferences -> Interface -> "Show status bar" (in the
main menu and calibre's Preferences button menu) shows it again (pref `show_status_bar`,
remembered). Running jobs, which calibre shows only in the status bar, then appear as a spinner
button in the header bar that opens calibre's Jobs list. The spinner is libadwaita's (spin.py),
not calibre's. (This replaces the separate Hide Statusbar plugin.)

Shown: only what GNOME apps show (the item count and selection), not calibre's
"calibre 9.18 created by Kovid Goyal" banner. A connected device stays visible. `_label` mirrors
calibre's StatusBar._set_label (calibre/gui2/init.py), minus the banner.
"""

SPINNER_SIZE = 16  # the header bar's icon size (main.GNOME_ICON_SIZE)
# The Hide Statusbar plugin's shortcut; calibre's keyboard manager owns it (Preferences -> Shortcuts).
SHORTCUT_ID = 'adwaita toggle status bar'
SHORTCUT_KEYS = ('Ctrl+Shift+S',)


def _label(self):
    from calibre.utils.localization import _, ngettext

    if self.total != self.current:
        base = _('%(num)d of %(total)d books') % dict(num=self.current, total=self.total)
    else:
        base = ngettext('one book', '{} books', self.total).format(self.total)
    if self.selected > 0:
        base = ngettext('%(num)s, %(sel)d selected', '%(num)s, %(sel)d selected', self.selected) % dict(
            num=base, sel=self.selected)
    if self.library_total != self.total:
        base = _('{0}, {1} total').format(base, self.library_total)
    if self.device_string:
        base = f'{self.device_string} \u00b7 {base}'
    self.defmsg.setText(base)
    self.clearMessage()


def install(gui):
    from calibre.gui2.init import StatusBar
    if not getattr(StatusBar, '_adwaita_patched', False):
        StatusBar._set_label = _label
        StatusBar._adwaita_patched = True
    sb = gui.statusBar()
    if isinstance(sb, StatusBar):
        sb.set_label()


def apply(gui, show):
    """Show or hide the status bar; the header-bar jobs button takes over while it is hidden."""
    sb = gui.statusBar()
    if sb is not None:
        sb.setVisible(show)
    b = getattr(gui, '_adwaita_jobs_button', None)
    if b is not None:
        b._adwaita_refresh()


def jobs_button(gui, parent):
    """A header-bar button with calibre's spinner, visible while jobs run and the status bar is
    hidden. calibre's own JobsButton (in the status bar) stays the source of the count and its
    Jobs list; this one follows the same JobManager signals and clicks through to it."""
    from qt.core import QHBoxLayout, QIcon, QPixmap, QSize, Qt, QToolButton

    jm = getattr(gui, 'job_manager', None)
    calibre_button = getattr(gui, 'jobs_button', None)
    if jm is None or calibre_button is None:
        return None
    b = QToolButton(parent)
    b.setObjectName('adwaita_jobs_button')
    b.setAutoRaise(True)
    # A blank icon gives the button the same size as its icon-only neighbours; the spinner
    # sits on top of it.
    blank = QPixmap(SPINNER_SIZE, SPINNER_SIZE)
    blank.fill(Qt.GlobalColor.transparent)
    b.setIcon(QIcon(blank))
    b.setIconSize(QSize(SPINNER_SIZE, SPINNER_SIZE))
    row = QHBoxLayout(b)
    row.setContentsMargins(0, 0, 0, 0)
    spinner = Spinner(b, SPINNER_SIZE)
    spinner.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    row.addWidget(spinner, 0, Qt.AlignmentFlag.AlignCenter)

    def refresh(*args):
        n = calibre_button.jobs()
        sb = gui.statusBar()
        show = n > 0 and (sb is None or sb.isHidden())
        b.setToolTip(f'{calibre_button.tray_tooltip(n)} (Jobs list: {calibre_button.shortcut})'
                     if calibre_button.shortcut else calibre_button.tray_tooltip(n))
        if show:
            spinner.start()
        else:
            spinner.stop()
        b.setVisible(show)

    # Connected after calibre's JobsButton, so its count is already updated when these run.
    jm.job_added.connect(refresh)
    jm.job_done.connect(refresh)
    b.clicked.connect(calibre_button.toggle)
    b._adwaita_refresh = refresh
    gui._adwaita_jobs_button = b
    refresh()
    return b


def menu_entry(gui):
    """Checkable "Show status bar" in calibre's Preferences menu, Interface section (the ☰ main
    menu shows the same menu), also on Ctrl+Shift+S. Saves the pref and shows or hides the bar.

    Call from initialization_complete: calibre assigns registered shortcuts right after every
    plugin's initialization_complete (keyboard.finalize)."""
    ia = gui.iactions.get('Preferences')
    pm = getattr(ia, 'preferences_menu', None) if ia is not None else None
    if pm is None or gui.statusBar() is None:
        return None
    from calibre_plugins.adwaita_for_calibre.main import prefs
    from qt.core import QAction

    a = QAction('Show status bar', pm)
    a.setObjectName('adwaita_show_status_bar')
    a.setCheckable(True)

    def toggled(*args):
        # From the bar itself, not the check mark: with the menu closed (the shortcut) the mark
        # may be stale.
        show = gui.statusBar().isHidden()
        prefs()['show_status_bar'] = show
        apply(gui, show)
        sync()

    def sync():
        # Follow the bar itself (also when something else toggles it) without saving the pref.
        a.blockSignals(True)
        a.setChecked(not gui.statusBar().isHidden())
        a.blockSignals(False)

    def place():
        # calibre builds the per-category submenus in its own initialization_complete, which
        # may run after ours: place the entry when the menu first opens, next to Look & feel.
        look = getattr(ia, 'action_map', {}).get('Look & Feel')
        for entry in pm.actions():
            sub = entry.menu()
            if sub is None or look not in sub.actions():
                continue
            if a not in sub.actions():
                sub.addSeparator()
                sub.addAction(a)
                sub.aboutToShow.connect(sync)
            return

    a.triggered.connect(toggled)
    gui.addAction(a)  # the shortcut works while the menu is closed
    keyboard = getattr(gui, 'keyboard', None)
    if keyboard is not None:
        keyboard.register_shortcut(SHORTCUT_ID, 'Show or hide the status bar',
                                   default_keys=SHORTCUT_KEYS, action=a, group='Adwaita for calibre')
    pm.aboutToShow.connect(place)
    place()
    sync()
    gui._adwaita_status_bar_action = a
    return a


def Spinner(parent, size):
    """libadwaita's spinner (AdwSpinner) as a QWidget: a faint track and an arc whose ends ease
    continuously (spin.py), drawn in the button's text colour. Driven by a QVariantAnimation on
    Qt's animation timer (one frame per display refresh), with float angles."""
    from calibre_plugins.adwaita_for_calibre import spin
    from qt.core import (
        QAbstractAnimation,
        QColor,
        QPainter,
        QPalette,
        QPen,
        QRectF,
        Qt,
        QVariantAnimation,
        QWidget,
    )

    class _Spinner(QWidget):
        def __init__(self):
            super().__init__(parent)
            self.setFixedSize(size, size)
            self.anim = a = QVariantAnimation(self)
            a.setStartValue(0.0)
            a.setEndValue(spin.LOOP_END)
            a.setDuration(spin.LOOP_MS)
            a.setLoopCount(-1)
            a.valueChanged.connect(self.update)

        def running(self):
            return self.anim.state() == QAbstractAnimation.State.Running

        def start(self):
            if not self.running():
                self.anim.start()

        def stop(self):
            self.anim.stop()
            self.update()

        def paintEvent(self, ev):
            w, h = self.width(), self.height()
            r = spin.radius(w, h)
            lw = spin.line_width(2 * r)
            if r < lw / 2:
                return
            progress = float(self.anim.currentValue()) if self.running() else spin.STILL
            tail, span = spin.arc(progress)
            colour = self.palette().color(QPalette.ColorRole.ButtonText)
            track = QColor(colour)
            track.setAlphaF(colour.alphaF() * spin.CIRCLE_OPACITY)
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.translate(round(w / 2), round(h / 2))
            rr = r - lw / 2
            rect = QRectF(-rr, -rr, 2 * rr, 2 * rr)
            pen = QPen(track, lw)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawEllipse(rect)
            pen.setColor(colour)
            p.setPen(pen)
            # Qt measures angles counter-clockwise in 1/16 degree; libadwaita's run clockwise.
            p.drawArc(rect, round(-tail * 16), round(-span * 16))
            p.end()

    return _Spinner()
