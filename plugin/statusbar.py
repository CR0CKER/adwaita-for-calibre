"""The status bar: hidden by default, and its text trimmed when shown.

Hidden: GNOME apps have no status bar. The main menu's "Status bar" entry shows it again
(pref `show_status_bar`, remembered). Running jobs, which calibre shows only in the status bar,
then appear as a spinner button in the header bar that opens calibre's Jobs list. (This replaces
the separate Hide Statusbar plugin.)

Shown: only what GNOME apps show (the item count and selection), not calibre's
"calibre 9.18 created by Kovid Goyal" banner. A connected device stays visible. `_label` mirrors
calibre's StatusBar._set_label (calibre/gui2/init.py), minus the banner.
"""

SPINNER_SIZE = 16  # the header bar's icon size (main.GNOME_ICON_SIZE)


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
    from calibre.gui2.progress_indicator import ProgressIndicator

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
    spinner = ProgressIndicator(b, SPINNER_SIZE)
    spinner.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    row.addWidget(spinner, 0, Qt.AlignmentFlag.AlignCenter)

    def refresh(*args):
        n = calibre_button.jobs()
        sb = gui.statusBar()
        show = n > 0 and (sb is None or sb.isHidden())
        b.setToolTip(f'{calibre_button.tray_tooltip(n)} (Jobs list: {calibre_button.shortcut})'
                     if calibre_button.shortcut else calibre_button.tray_tooltip(n))
        if show:
            spinner.startAnimation()
        else:
            spinner.stopAnimation()
        b.setVisible(show)

    # Connected after calibre's JobsButton, so its count is already updated when these run.
    jm.job_added.connect(refresh)
    jm.job_done.connect(refresh)
    b.clicked.connect(calibre_button.toggle)
    b._adwaita_refresh = refresh
    gui._adwaita_jobs_button = b
    refresh()
    return b
