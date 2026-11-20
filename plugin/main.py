"""Qt glue: install the Adwaita palette, stylesheet, popup shapes and font into calibre.

calibre owns the application palette and stylesheet (calibre/gui2/palette.py, PaletteManager).
It rebuilds both on every palette change: light/dark switch, Preferences, Qt's own palette events.
So instead of setting them once, this plugin replaces the two palette factories and wraps
`PaletteManager.on_palette_change`. Each rebuild then ends with the Adwaita layer on top.
"""

import os

from calibre.constants import config_dir
from calibre.gui2.actions import InterfaceAction
from calibre_plugins.adwaita_for_calibre import adwaita

PREFIX = 'adwaita-for-calibre:'
IMAGES = (
    'images/pan-down-symbolic.svg',
    'images/pan-up-symbolic.svg',
    'images/pan-end-symbolic.svg',
    'images/object-select-symbolic.svg',
    'images/window-close-symbolic.svg',
    'images/window-minimize-symbolic.svg',
    'images/window-maximize-symbolic.svg',
    'images/view-list-symbolic.svg',
    'images/view-grid-symbolic.svg',
    'images/accessories-dictionary-symbolic.svg',
    'images/sidebar-show-symbolic.svg',
    'images/sidebar-show-right-symbolic.svg',
    'images/cover-browser-symbolic.svg',
    'images/dialog-warning-symbolic.svg',
    'images/view-more-symbolic.svg',
)
RADIO_DOT = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">'
    '<circle cx="8" cy="8" r="3.5" fill="#222222"/></svg>'
)
MIXED = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">'
    '<rect x="3" y="7" width="10" height="2" rx="1" fill="#222222"/></svg>'
)
# Popups that need a translucent window so their rounded corners are not painted black.
ROUNDED_POPUPS = ('QMenu', 'QTipLabel', 'QComboBoxPrivateContainer')

PORTAL = (
    'org.freedesktop.portal.Desktop',
    '/org/freedesktop/portal/desktop',
    'org.freedesktop.portal.Settings',
)


def debug(*args):
    if os.environ.get('ADWAITA_CALIBRE_DEBUG'):
        import sys
        print(PREFIX, *args, file=sys.stderr)


def portal_read(namespace, key):
    """One value from the XDG Settings portal, or None. Works inside the Flatpak sandbox."""
    try:
        from qt.dbus import QDBusConnection, QDBusMessage
    except ImportError:
        return None
    msg = QDBusMessage.createMethodCall(*PORTAL, 'ReadOne')
    msg.setArguments([namespace, key])
    reply = QDBusConnection.sessionBus().call(msg, timeout=500)
    if reply.type() != QDBusMessage.MessageType.ReplyMessage or not reply.arguments():
        debug('portal read failed:', namespace, key, reply.errorMessage())
        return None
    return reply.arguments()[0]


class Theme:
    """The live state: accent, the rendered stylesheet per mode, the image folders."""

    def __init__(self, resources):
        self.qss_template = resources['adwaita.qss'].decode('utf-8')
        self.svgs = {
            os.path.basename(k): v.decode('utf-8') for k, v in resources.items() if k.endswith('.svg')
        }
        self.svgs['radio-dot.svg'] = RADIO_DOT
        self.svgs['mixed.svg'] = MIXED
        self.accent = adwaita.DEFAULT_ACCENT
        self.cache = {}
        self.read_accent()

    def read_accent(self):
        value = portal_read('org.freedesktop.appearance', 'accent-color')
        accent = adwaita.accent_from_portal(value) if value is not None else None
        changed = bool(accent) and accent != self.accent
        if accent:
            self.accent = accent
        debug('accent', self.accent)
        return changed

    def tokens(self, dark):
        return adwaita.tokens(dark, self.accent)

    def image_dir(self, dark, t):
        """Recoloured indicator SVGs for this mode+accent, written once to calibre's config dir."""
        name = f'{"dark" if dark else "light"}-{self.accent.lstrip("#")}'
        path = os.path.join(config_dir, 'plugins', 'adwaita_for_calibre', name)
        os.makedirs(path, exist_ok=True)
        files = {
            'pan-down.svg': ('pan-down-symbolic.svg', t['fg']),
            'pan-down-dim.svg': ('pan-down-symbolic.svg', t['fg_dim']),
            'pan-up.svg': ('pan-up-symbolic.svg', t['fg']),
            'pan-up-dim.svg': ('pan-up-symbolic.svg', t['fg_dim']),
            'pan-end.svg': ('pan-end-symbolic.svg', t['fg']),
            'pan-end-dim.svg': ('pan-end-symbolic.svg', t['fg_dim']),
            # libadwaita expander: pan-end-symbolic at currentColor 70 %
            'expander-closed.svg': ('pan-end-symbolic.svg', adwaita.mix(t['fg'], t['pane_bg'], 0.7)),
            'expander-open.svg': ('pan-down-symbolic.svg', adwaita.mix(t['fg'], t['pane_bg'], 0.7)),
            'check.svg': ('object-select-symbolic.svg', t['accent_fg']),
            'check-fg.svg': ('object-select-symbolic.svg', t['fg']),
            'radio-dot.svg': ('radio-dot.svg', t['accent_fg']),
            'mixed.svg': ('mixed.svg', t['accent_fg']),
            'window-close.svg': ('window-close-symbolic.svg', t['fg']),
            'window-minimize.svg': ('window-minimize-symbolic.svg', t['fg']),
            'window-maximize.svg': ('window-maximize-symbolic.svg', t['fg']),
            'view-list.svg': ('view-list-symbolic.svg', t['fg']),
            'view-grid.svg': ('view-grid-symbolic.svg', t['fg']),
            'view-bookshelf.svg': ('accessories-dictionary-symbolic.svg', t['fg']),
            'sidebar-left.svg': ('sidebar-show-symbolic.svg', t['fg']),
            'sidebar-right.svg': ('sidebar-show-right-symbolic.svg', t['fg']),
            'cover-browser.svg': ('cover-browser-symbolic.svg', t['fg']),
            'view-more.svg': ('view-more-symbolic.svg', t['fg']),
            # Sort-field status (metadata.py): libadwaita success / warning colours.
            'status-ok.svg': ('object-select-symbolic.svg', t['success_bg']),
            'status-warning.svg': ('dialog-warning-symbolic.svg', t['warning_bg']),
        }
        for out, (src, color) in files.items():
            data = adwaita.recolor_svg(self.svgs[src], color)
            dest = os.path.join(path, out)
            try:
                with open(dest, encoding='utf-8') as f:
                    if f.read() == data:
                        continue
            except OSError:
                pass
            with open(dest, 'w', encoding='utf-8') as f:
                f.write(data)
        return path.replace(os.sep, '/')

    def stylesheet(self, dark):
        key = (dark, self.accent)
        if key not in self.cache:
            t = dict(self.tokens(dark))
            t['img'] = self.image_dir(dark, t)
            self.cache[key] = adwaita.render(self.qss_template, t)
        return self.cache[key]

    def palette(self, dark):
        from qt.core import QColor, QPalette

        t = self.tokens(dark)
        p = QPalette()
        R, G = QPalette.ColorRole, QPalette.ColorGroup

        def s(role, c, group=None):
            if group is None:
                p.setColor(role, QColor(c))
            else:
                p.setColor(group, role, QColor(c))

        s(R.Window, t['window_bg'])
        s(R.WindowText, t['fg'])
        s(R.Base, t['view_bg'])
        s(R.AlternateBase, t['alternate_base'])
        s(R.Text, t['view_fg'])
        s(R.PlaceholderText, t['fg_dim'])
        s(R.Button, t['button_solid'])
        s(R.ButtonText, t['fg'])
        s(R.BrightText, t['destructive_bg'])
        s(R.ToolTipBase, t['popover_bg'])
        s(R.ToolTipText, t['fg'])
        s(R.Highlight, t['selection_bg'])
        s(R.HighlightedText, t['view_fg'])
        s(R.Link, t['accent'])
        s(R.LinkVisited, adwaita.mix(t['accent'], t['view_bg'], 0.8))
        s(R.Accent, t['accent_bg'])
        # Fusion draws frames and bevels from these.
        s(R.Light, adwaita.mix(t['fg'], t['window_bg'], 0.20))
        s(R.Midlight, adwaita.mix(t['fg'], t['window_bg'], 0.12))
        s(R.Mid, adwaita.mix(t['fg'], t['window_bg'], 0.15))
        s(R.Dark, adwaita.mix('#000006', t['window_bg'], 0.30))
        s(R.Shadow, adwaita.mix('#000006', t['window_bg'], 0.50))
        for role in (R.WindowText, R.Text, R.ButtonText, R.HighlightedText):
            s(role, t['fg_disabled'], G.Disabled)
        s(R.Highlight, adwaita.mix(t['fg'], t['view_bg'], 0.10), G.Disabled)
        return p

    def hover_style(self, dark):
        """Appended by calibre to the tag browser's own stylesheet (its only user in the main
        window): libadwaita's navigation sidebar. Sidebar background, 6 px rounded rows,
        hover at 7 %, selection at 10 %, GNOME expander arrows."""
        t = dict(self.tokens(dark))
        img = self.image_dir(dark, t)
        return f'''
            QTreeView {{
                background-color: {t['pane_bg']};
                color: {t['fg']};
                border: none;
                /* The panes' 12 px inset (panes.INSET) at the top and left, so the expander arrows
                 * line up with the Configure button below; 6 px on the right for the counts. */
                padding: 12px 6px 0 12px;
                selection-background-color: {t['button_bg']};
                selection-color: {t['fg']};
            }}
            QTreeView::item {{
                border: none;
                border-radius: 6px;
                padding-left: 2px;
            }}
            QTreeView::item:hover {{
                background: {t['hover']};
            }}
            QTreeView::item:selected,
            QTreeView::item:selected:active,
            QTreeView::item:selected:!active {{
                background: {t['button_bg']};
                color: {t['fg']};
            }}
            QTreeView::branch {{
                background: transparent;
                border: none;
            }}
            QTreeView::branch:has-children:closed {{
                image: url({img}/expander-closed.svg);
            }}
            QTreeView::branch:has-children:open {{
                image: url({img}/expander-open.svg);
            }}
        '''


# Buttons whose icons the plugin renders itself (view switcher, window buttons). Their SVGs are
# recoloured per light/dark mode, so they must be re-set when the scheme changes live.
_TRACKED_ICONS = []
_THEME = None


def tracked_icon(button, filename):
    """Set `button`'s icon to one of the plugin's recoloured images and keep it in sync."""
    _TRACKED_ICONS.append((button, filename))
    _apply_icon(button, filename)


def _current_image_dir():
    from qt.core import QApplication
    dark = QApplication.instance().palette_manager.is_dark_theme
    return _THEME.image_dir(dark, _THEME.tokens(dark))


def _apply_icon(button, filename):
    from qt.core import QIcon
    if _THEME is not None:
        button.setIcon(QIcon(f'{_current_image_dir()}/{filename}'))


def refresh_tracked_icons():
    alive = []
    for button, filename in _TRACKED_ICONS:
        try:
            _apply_icon(button, filename)
        except RuntimeError:
            continue  # widget deleted
        alive.append((button, filename))
    _TRACKED_ICONS[:] = alive


# libadwaita popover: border 1px rgb(0 0 0 / 14%), box-shadow 0 1px 5px 1px rgb(0 0 0 / 9%),
# 0 2px 14px 3px rgb(0 0 0 / 5%). QSS has no box-shadow: menus get a transparent margin and the
# shadow is painted into it before Qt draws the menu itself.
MENU_SHADOW = 14


def paint_menu_shadow(menu):
    from qt.core import QColor, QPainter, QPainterPath, QRectF
    p = QPainter(menu)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    inner = QRectF(menu.rect()).adjusted(MENU_SHADOW, MENU_SHADOW, -MENU_SHADOW, -MENU_SHADOW)
    for spread, dy, blur, alpha in ((1, 1, 5, 0.09), (3, 2, 14, 0.05)):
        steps = max(1, blur // 2)
        for i in range(steps):
            grow = spread + blur * (i + 1) / steps
            c = QColor(0, 0, 0)
            c.setAlphaF(alpha / steps)  # rings overlap at the edge: total there = alpha
            path = QPainterPath()
            r = inner.adjusted(-grow, -grow + dy, grow, grow + dy)
            path.addRoundedRect(r, 12 + grow, 12 + grow)
            hole = QPainterPath()
            hole.addRoundedRect(inner, 12, 12)
            p.fillPath(path.subtracted(hole), c)
    p.end()


class EventFilter:
    """Gives popups a translucent window before they first show, so QSS corner radii work."""

    @staticmethod
    def create():
        from qt.core import QEvent, QObject, Qt

        class Filter(QObject):
            def eventFilter(self, obj, ev):
                t = ev.type()
                if t == QEvent.Type.Polish and obj.isWidgetType() and obj.isWindow():
                    if obj.metaObject().className() in ROUNDED_POPUPS:
                        obj.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
                elif obj.isWidgetType() and obj.metaObject().className() == 'QMenu':
                    if t == QEvent.Type.Show:
                        # The shadow margin (QSS) would push the menu's visible edge away from
                        # where Qt placed it; move it back.
                        obj.move(obj.x() - MENU_SHADOW, obj.y() - MENU_SHADOW + 1)
                    elif t == QEvent.Type.Paint:
                        paint_menu_shadow(obj)
                return False

        return Filter()


# The calibre release the plugin was last tested against. It patches calibre internals, so a newer
# calibre may have moved something; say so once instead of failing obscurely (audit L5).
TESTED_WITH = (9, 18)


def check_calibre_version():
    from calibre.constants import numeric_version
    debug('calibre', '.'.join(map(str, numeric_version)))
    if tuple(numeric_version[:2]) > TESTED_WITH:
        import sys
        print(f'{PREFIX} tested with calibre {TESTED_WITH[0]}.{TESTED_WITH[1]}; running '
              f'{".".join(map(str, numeric_version))}. If something looks wrong, disable the plugin '
              'and report it.', file=sys.stderr)


def install(theme):
    import calibre.gui2.palette as calibre_palette
    from calibre.gui2 import gprefs
    from qt.core import QApplication, QFont

    global _THEME
    _THEME = theme
    check_calibre_version()
    app = QApplication.instance()
    pm = app.palette_manager
    if not pm.using_calibre_style:
        debug('calibre is not using its own style; leaving the system theme alone')
        return False

    use_overlay_scrollbars(app, pm)

    calibre_palette.dark_palette = lambda: theme.palette(True)
    calibre_palette.light_palette = lambda: theme.palette(False)

    cls = type(pm)
    if not getattr(cls, '_adwaita_patched', False):
        original = cls.on_palette_change

        def on_palette_change(self):
            original(self)
            try:
                a = QApplication.instance()
                a.setStyleSheet(a.styleSheet() + '\n' + theme.stylesheet(self.is_dark_theme))
                refresh_tracked_icons()
            except Exception:  # noqa: BLE001 -- never take calibre down: fall back to its own look
                import traceback
                traceback.print_exc()

        cls.on_palette_change = on_palette_change
        cls.tree_view_hover_style = lambda self: theme.hover_style(self.is_dark_theme)
        cls._adwaita_patched = True

    app._adwaita_filter = EventFilter.create()
    app.installEventFilter(app._adwaita_filter)

    if not gprefs['font']:
        spec = adwaita.parse_font(portal_read('org.gnome.desktop.interface', 'font-name'))
        if spec:
            f = QFont(app.font())
            f.setFamily(spec[0])
            f.setPointSizeF(spec[1])
            app.setFont(f)
            debug('font', spec)

    watch_portal(app, theme, pm)
    pm.refresh_palette()
    return True


SIDEBAR_INDENT = 24


def style_sidebar(gui):
    """Plain QWidgets ignore stylesheet backgrounds unless WA_StyledBackground is set; the tag
    browser's bottom bar (Configure / Find) is one."""
    from qt.core import Qt, QTreeView, QWidget
    for w in gui.findChildren(QWidget):
        name = type(w).__name__
        if name in ('TagBrowserBar', 'TagBrowserWidget'):
            w.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        if name == 'TagBrowserBar' and w.layout() is not None:
            # libadwaita action bar: 6 px around and between the controls.
            w.layout().setContentsMargins(6, 6, 6, 6)
            w.layout().setSpacing(6)
            # Qt puts a fixed 4 px between a tool button's icon and label (no stylesheet
            # control); GNOME uses about 8. A leading space gives about the same gap.
            from qt.core import QToolButton
            for b in w.findChildren(QToolButton):
                text = b.text()
                if (text and not text.startswith(' ') and not b.icon().isNull()
                        and b.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonTextBesideIcon):
                    b.setText(' ' + text)
    # calibre paints hovered tag-browser text black in dark mode, to sit on its light gradient
    # hover. On libadwaita's subtle hover that is unreadable; keep the normal text colour.
    try:
        from calibre.gui2.tag_browser.view import TagDelegate
        from qt.core import QPalette
        TagDelegate.text_color = lambda self, hover, palette: palette.color(QPalette.ColorRole.WindowText)
    except Exception as e:  # noqa: BLE001 -- calibre internals may change; cosmetic patch only
        debug('tag browser hover colour not patched', e)
    for tv in gui.findChildren(QTreeView):
        if type(tv).__name__ == 'TagsView':
            # calibre's style narrows the expander column to 12 px, which squeezes the arrow.
            # libadwaita's expander is a 16 px icon; give it a 24 px column.
            tv.setIndentation(SIDEBAR_INDENT)


def use_overlay_scrollbars(app, pm):
    """GNOME's scroll bars are overlays that fade out. calibre's own style (a Fusion proxy)
    supports that through SH_ScrollBar_Transient, but calibre only enables it on macOS.
    Replace the style with one created with the flag set."""
    try:
        from calibre_extensions.progress_indicator import CalibreStyle
    except ImportError:
        return
    pm.calibre_style = style = CalibreStyle(1)
    app.setStyle(style)
    debug('overlay scroll bars on')


# GNOME headerbar icons are 16 px. calibre's smallest toolbar size ("Small") is 24 px, so the
# plugin redefines "Small" as 16 px; the larger sizes keep calibre's values.
GNOME_ICON_SIZE = 16


def install_toolbar_size(gui):
    from calibre.gui2 import gprefs
    from calibre.gui2.bars import BarsManager
    from qt.core import QSize

    if not getattr(BarsManager, '_adwaita_patched', False):
        original = BarsManager.apply_settings

        def apply_settings(self):
            original(self)
            if gprefs['toolbar_icon_size'] == 'small':
                for bar in self.bars:
                    bar.setIconSize(QSize(GNOME_ICON_SIZE, GNOME_ICON_SIZE))
                    if bar.donate_button:
                        bar.donate_button.setIconSize(bar.iconSize())

        BarsManager.apply_settings = apply_settings
        BarsManager._adwaita_patched = True
    bm = getattr(gui, 'bars_manager', None)
    if bm is not None:
        bm.apply_settings()


def watch_portal(app, theme, pm):
    """Follow accent changes live (GNOME Settings -> Appearance)."""
    try:
        from qt.core import QObject, pyqtSlot
        from qt.dbus import QDBusConnection, QDBusMessage
    except ImportError:
        return

    class Watcher(QObject):
        @pyqtSlot(QDBusMessage)
        def changed(self, msg):
            args = msg.arguments()
            if len(args) >= 2 and args[0] == 'org.freedesktop.appearance' and args[1] == 'accent-color':
                if theme.read_accent():
                    pm.refresh_palette()
                    hook = getattr(theme, 'on_accent_change', None)
                    if hook is not None:
                        hook()

    app._adwaita_watcher = w = Watcher(app)
    ok = QDBusConnection.sessionBus().connect(PORTAL[0], PORTAL[1], PORTAL[2], 'SettingChanged', w.changed)
    debug('portal watch', ok)


def prefs():
    from calibre.utils.config import JSONConfig
    p = JSONConfig('plugins/adwaita_for_calibre')
    p.defaults['integrated_titlebar'] = False
    p.defaults['theme_viewer'] = True
    p.defaults['show_status_bar'] = False  # statusbar.py: GNOME apps have none
    p.defaults['toolbar_adopted'] = False  # toolbarprefs.py: calibre's toolbar set to Small once
    p.defaults['previous_toolbar'] = {}
    p.defaults['viewer_scheme_set'] = False
    p.defaults['viewer_previous_scheme'] = ''
    return p


class AdwaitaAction(InterfaceAction):
    name = 'Adwaita for calibre'
    # Invisible action. It must be excluded from *every* location, the search bar included:
    # calibre's Toolbars & menus preferences list the remaining ones and call .replace() on
    # the name.
    action_spec = ('Adwaita for calibre', None, None, None)
    dont_add_to = frozenset((
        'context-menu', 'context-menu-device', 'context-menu-split', 'context-menu-cover-browser',
        'toolbar', 'toolbar-device', 'toolbar-child', 'menubar', 'menubar-device', 'searchbar',
    ))
    action_type = 'current'

    def genesis(self):
        resources = self.load_resources(('adwaita.qss',) + IMAGES)
        try:
            self.theme = Theme(resources)
            self.active = install(self.theme)
            if self.active:
                from calibre_plugins.adwaita_for_calibre import bookshelf, covers, layoutmenu
                bookshelf.install(self.theme)
                layoutmenu.install()
                covers.install()
                from calibre_plugins.adwaita_for_calibre import metadata
                metadata.install()
            if self.active and prefs()['integrated_titlebar']:
                from calibre_plugins.adwaita_for_calibre import frameless
                frameless.prepare(self.gui)
        except Exception:  # noqa: BLE001 -- plugin must not break calibre's startup; traceback printed
            self.active = False
            import traceback
            traceback.print_exc()

    def initialization_complete(self):
        # The toolbars and the search row only exist once the main window is built.
        if not getattr(self, 'active', False):
            return
        try:
            from calibre.gui2 import gprefs
            from calibre_plugins.adwaita_for_calibre import toolbarprefs
            if toolbarprefs.adopt(gprefs, prefs()):
                debug('toolbar set to Small icons without text (first run)')
            install_toolbar_size(self.gui)  # applies calibre's toolbar settings
            from calibre_plugins.adwaita_for_calibre import panes, shade, slide, statusbar
            panes.install(self.gui)
            slide.install()
            shade.install(self.gui)
            shade.install_sidebar(self.gui)
            statusbar.install(self.gui)
            from calibre_plugins.adwaita_for_calibre import viewer
            if prefs()['theme_viewer']:
                viewer.sync(self.theme, prefs())
                self.theme.on_accent_change = lambda: viewer.sync(self.theme, prefs())
            else:
                viewer.unsync(prefs())
            style_sidebar(self.gui)
            from calibre_plugins.adwaita_for_calibre import bookshelf
            bookshelf.refresh(self.gui)
            from calibre_plugins.adwaita_for_calibre import headerbar
            from qt.core import QApplication
            dark = QApplication.instance().palette_manager.is_dark_theme
            image_dir = self.theme.image_dir(dark, self.theme.tokens(dark))
            merged = headerbar.merge(self.gui, image_dir)
            statusbar.apply(self.gui, prefs()['show_status_bar'] or not merged)
            statusbar.menu_entry(self.gui)
            if merged and prefs()['integrated_titlebar']:
                from calibre_plugins.adwaita_for_calibre import frameless
                frameless.install(self.gui, image_dir)
        except Exception:  # noqa: BLE001 -- plugin must not break calibre's startup; traceback printed
            import traceback
            traceback.print_exc()
