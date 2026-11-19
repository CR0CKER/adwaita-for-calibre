import os
import traceback

from calibre.gui2.actions import InterfaceAction
from qt.core import QApplication, QPoint, QTimer


class Shots(InterfaceAction):
    name = 'Adwaita Dev Shots'
    # Invisible action. It must be excluded from *every* location, the search bar included:
    # calibre's Toolbars & menus preferences list the remaining ones and call .replace() on
    # the name.
    action_spec = ('Adwaita Dev Shots', None, None, None)
    dont_add_to = frozenset((
        'context-menu', 'context-menu-device', 'context-menu-split', 'context-menu-cover-browser',
        'toolbar', 'toolbar-device', 'toolbar-child', 'menubar', 'menubar-device', 'searchbar',
    ))

    def genesis(self):
        self.dir = os.environ.get('ADWAITA_SHOT_DIR')
        if not self.dir:
            return
        os.makedirs(self.dir, exist_ok=True)
        self.tag = os.environ.get('ADWAITA_SHOT_TAG', 'shot')
        self.only = set(filter(None, os.environ.get('ADWAITA_SHOT_ONLY', '').split(',')))
        self.steps = [
            ('main', self.main), ('focus', self.focus), ('statusbar', self.statusbar), ('hover', self.hover),
            ('layoutmenu', self.layoutmenu), ('scrolled', self.scrolled),
            ('sidebar', self.sidebar), ('perf', self.perf),
            ('menu', self.menu),
            ('menus', self.menus), ('grid', self.grid),
            ('prefs', self.prefs), ('metadata', self.metadata), ('news', self.news),
            ('flip', self.flip), ('views', self.views), ('closebtn', self.closebtn),
            ('prefcheck', self.prefcheck), ('quit', self.quit),
        ]
        QTimer.singleShot(int(os.environ.get('ADWAITA_SHOT_DELAY', '5000')), self.next)

    def next(self):
        while self.steps:
            name, fn = self.steps.pop(0)
            if self.only and name not in self.only and name != 'quit':
                continue
            try:
                fn()
            except Exception:
                traceback.print_exc()
                QTimer.singleShot(300, self.next)
            return

    def save(self, w, name):
        path = os.path.join(self.dir, f'{self.tag}-{name}.png')
        w.grab().save(path)
        print('SHOT', path, flush=True)

    def later(self, ms, fn):
        QTimer.singleShot(ms, fn)

    def scrolled(self):
        # Short window so the list scrolls; scroll half-way; both shades should show.
        self.gui.statusBar().setVisible(True)
        self.gui.resize(self.gui.width(), 620)
        av = self.gui.library_view.alternate_views

        def go():
            sb = av.current_view.verticalScrollBar()
            print('SCROLL range', sb.minimum(), sb.maximum(), flush=True)
            v = av.current_view
            ix = v.model().index(45, 1)
            v.setCurrentIndex(ix)
            v.scrollTo(ix)
            shade = self.gui._adwaita_shade
            self.later(500, lambda: (print('SCROLL now', sb.value(), shade.top.isVisible(),
                                           shade.bottom.isVisible(), flush=True),
                                     self.gui.repaint(),
                                     self.save(av.current_view, 'scrolled-view'),
                                     self.save(self.gui, 'scrolled'),
                                     print('STATUS', self.gui.status_bar.defmsg.text(), flush=True),
                                     self.next()))
        self.later(800, go)

    def sidebar(self):
        # Expand everything in the tag browser so it scrolls, then scroll it a little.
        tv = self.gui.tags_view
        tv.expandAll()

        def go():
            sb = tv.verticalScrollBar()
            sb.setValue(min(sb.maximum(), 60))
            sh = tv._adwaita_shades
            self.later(500, lambda: (print('SIDEBAR range', sb.maximum(), 'value', sb.value(), 'top',
                                           sh.top.isVisible(), 'bottom', sh.bottom.isVisible(), flush=True),
                                     self.save(self.gui, 'sidebar'), self.next()))
        self.later(800, go)

    def perf(self):
        # Time cover-grid repaints with and without the plugin's card shadow, and the full
        # window (corner overlay, translucency) for comparison.
        import time

        from calibre.gui2.library.alternate_views import CoverDelegate
        av = self.gui.library_view.alternate_views
        self.gui.grid_view_button.setChecked(True)

        def run():
            vp = av.current_view.viewport()

            def t(label, w, n=20):
                QApplication.processEvents()
                st = time.perf_counter()
                for _ in range(n):
                    w.repaint()
                ms = (time.perf_counter() - st) * 1000 / n
                print(f'PERF {label}: {ms:.1f} ms/frame', flush=True)

            t('grid viewport, card shadow on', vp)
            patched = CoverDelegate.paint_cover
            try:
                from calibre_plugins.adwaita_for_calibre import covers
                orig = getattr(covers, '_ORIG_COVER', None)
            except ImportError:  # plain run, without the plugin
                orig = None
            if orig is not None:
                CoverDelegate.paint_cover = orig
                t('grid viewport, card shadow off', vp)
                CoverDelegate.paint_cover = patched
            t('whole window', self.gui, 10)
            try:
                from calibre_plugins.adwaita_for_calibre import covers
                from qt.core import QPainter, QPixmap, QRect, Qt
                img = QPixmap(1200, 1200)
                img.setDevicePixelRatio(2.0)
                img.fill(Qt.GlobalColor.transparent)
                r = QRect(40, 40, 180, 270)
                for label, fn in (('key+cache lookup', lambda p: covers._card_pixmap(180, 270, 2.0)),
                                  ('paint_card', lambda p: covers.paint_card(p, r))):
                    p = QPainter(img)
                    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                    st = time.perf_counter()
                    for _ in range(200):
                        fn(p)
                    p.end()
                    print(f'PERF {label}: {(time.perf_counter() - st) * 1000 / 200:.3f} ms/cover', flush=True)
            except ImportError:
                pass
            self.next()
        self.later(2500, run)

    def layoutmenu(self):
        from calibre.gui2.layout_menu import LayoutMenu
        m = self.gui.findChild(LayoutMenu)
        print('LAYOUTMENU found', m is not None, flush=True)
        if m is None:
            self.next()
            return
        m.show()

        def done():
            self.save(self.gui, 'layoutmenu')
            m.hide()
            self.next()
        self.later(800, done)

    def hover(self):
        # Paint a tag-browser row as hovered (the delegate's own code path) and check its pen.
        from qt.core import QStyle, QStyleOptionViewItem
        tv = self.gui.tags_view
        ix = tv.model().index(0, 0)
        opt = QStyleOptionViewItem()
        tv.initViewItemOption(opt) if hasattr(tv, 'initViewItemOption') else None
        opt.rect = tv.visualRect(ix)
        opt.state |= QStyle.StateFlag.State_MouseOver
        d = tv.itemDelegate()
        print('HOVER text colour', d.text_color(True, opt.palette).name(),
              'normal', d.text_color(False, opt.palette).name(), flush=True)
        self.next()

    def statusbar(self):
        # Toggle the status bar off and on again, as calibre's Layout / Hide Statusbar do.
        sb = self.gui.statusBar()
        sb.setVisible(False)

        def back():
            self.save(self.gui, 'statusbar-hidden')
            sb.setVisible(True)
            self.later(600, lambda: (self.save(self.gui, 'statusbar'), self.next()))
        self.later(600, back)

    def focus(self):
        self.gui.search.setFocus()
        self.later(600, lambda: (self.save(self.gui.search_bar, 'focus'), self.next()))

    def main(self):
        tv = getattr(self.gui, 'tags_view', None)
        if tv is not None and tv.model().rowCount() > 0:
            for r in range(tv.model().rowCount()):
                ix = tv.model().index(r, 0)
                if 'Tags' in str(tv.model().data(ix)):
                    tv.expand(ix)
        w = int(os.environ.get('ADWAITA_SHOT_WIDTH', '0'))
        if w:
            self.gui.resize(w, self.gui.height())
        self.gui.library_view.select_rows([self.gui.library_view.model().id(0)])
        self.later(1500, lambda: (self.save(self.gui, 'main'), self.next()))

    def menu(self):
        lv = self.gui.library_view
        m = lv.context_menu
        m.popup(lv.mapToGlobal(QPoint(200, 120)))

        def done():
            self.save(m, 'menu')
            m.close()
            self.next()
        self.later(800, done)

    def menus(self):
        # Every action's drop-down menu plus the context menu's submenus, one shot each.
        seen, queue = set(), []
        for name, ac in sorted(self.gui.iactions.items()):
            m = ac.qaction.menu()
            if m is not None and id(m) not in seen:
                seen.add(id(m))
                queue.append((name, m))
        for a in self.gui.library_view.context_menu.actions():
            m = a.menu()
            if m is not None and id(m) not in seen:
                seen.add(id(m))
                queue.append(('ctx-' + a.text().replace('&', ''), m))

        def one():
            if not queue:
                self.next()
                return
            name, m = queue.pop(0)
            try:
                m.aboutToShow.emit()
            except Exception:
                pass
            m.popup(self.gui.mapToGlobal(QPoint(300, 200)))

            def done():
                safe = ''.join(c if c.isalnum() else '_' for c in name)
                self.save(m, 'm-' + safe)
                m.close()
                self.later(150, one)
            self.later(500, done)
        one()

    def grid(self):
        try:
            self.gui.library_view.alternate_views.show_view('grid')
        except Exception:
            traceback.print_exc()

        def done():
            self.save(self.gui, 'grid')
            try:
                self.gui.library_view.alternate_views.show_view(None)
            except Exception:
                pass
            self.next()
        self.later(1500, done)

    def prefs(self):
        from calibre.gui2.preferences.main import Preferences
        d = Preferences(self.gui)
        d.show()
        pages = [p for p in ('Look & feel', 'Adding books', 'Behavior')]

        def page(i=0):
            if i == 0:
                self.save(d, 'prefs')
            if i < len(pages):
                from calibre.customize.ui import preferences_plugins
                for p in preferences_plugins():
                    if p.gui_name == pages[i]:
                        d.show_plugin(p)
                        break
                self.later(1200, lambda: (self.save(d, 'prefs-' + pages[i].split()[0].lower()), page(i + 1)))
            else:
                d.hide()
                self.next()
        self.later(1500, page)

    def modal(self, name, opener):
        def grab():
            w = QApplication.activeModalWidget()
            if w is not None:
                self.save(w, name)
                w.reject()
        self.later(3000, grab)
        opener()
        self.later(500, self.next)

    def metadata(self):
        self.modal('metadata', lambda: self.gui.iactions['Edit Metadata'].edit_metadata(False))

    def news(self):
        self.modal('news', lambda: self.gui.iactions['Fetch News'].scheduler.show_dialog())

    def flip(self):
        # Exercise the live GNOME light/dark switch path (styleHints().colorSchemeChanged).
        from qt.core import Qt
        pm = QApplication.instance().palette_manager
        pm.color_palette = 'system'
        dark = pm.is_dark_theme
        pm.color_scheme_changed(Qt.ColorScheme.Light if dark else Qt.ColorScheme.Dark)
        self.later(1500, lambda: (self.save(self.gui, 'flipped'), self.next()))

    def views(self):
        # Click each switcher button, then use calibre's own grid toggle (the shortcut's
        # action) and check that the switcher follows.
        from qt.core import QFrame
        box = self.gui.findChild(QFrame, 'adwaita_view_switcher')
        av = self.gui.library_view.alternate_views
        if box is None:
            print('VIEWS no switcher', flush=True)
            self.next()
            return
        buttons = box._adwaita_buttons

        def current():
            return next((k for k, v in av.views.items() if v is av.current_view), None)

        def which():
            return next((k for k, b in buttons.items() if b.isChecked()), 'none')

        seq = [('click', 'grid'), ('click', 'bookshelf'), ('click', None), ('click', 'grid'),
               ('shortcut-grid', None), ('shortcut-bookshelf', None), ('click', None)]

        def step():
            if not seq:
                self.next()
                return
            kind, key = seq.pop(0)
            if kind == 'click':
                buttons[key].click()
            elif kind == 'shortcut-grid':
                self.gui.grid_view_button.action_toggle.trigger()
            else:
                self.gui.bookshelf_view_button.action_toggle.trigger()

            def report():
                from qt.core import QFrame
                sw = self.gui.findChild(QFrame, 'adwaita_view_switcher')
                print(f'VIEWS {kind} {key}: shown={current()} switcher={which()} '
                      f'search_w={self.gui.search.width()} switcher_x={sw.x()}', flush=True)
                if kind == 'click' and key == 'grid' and not seq[1:2] == []:
                    pass
                self.save(self.gui, f'views-{len(seq)}')
                step()
            self.later(700, report)
        step()

    def prefcheck(self):
        # Toolbars & menus: save with Preferences in neither the toolbar nor the menu bar.
        from calibre.gui2.preferences import AbortCommit
        from calibre.gui2.preferences.toolbar import ConfigWidget
        w = ConfigWidget(self.gui)
        w.genesis(self.gui)
        w.initialize()
        for key in ('toolbar', 'menubar'):
            m = w.models[key][1]
            orig = m.has_action
            m.has_action = lambda name, orig=orig: False if name == 'Preferences' else orig(name)
        # Drop the error dialog the original check would show, so the run cannot block.
        import calibre.gui2.preferences.toolbar as tb
        tb.error_dialog = lambda *a, **k: print('PREFCHECK error dialog:', a[1], flush=True)
        try:
            w.commit()
            print('PREFCHECK saved without Preferences in toolbar/menubar', flush=True)
        except AbortCommit:
            print('PREFCHECK refused', flush=True)
        self.later(300, self.next)

    def closebtn(self):
        # Click the integrated title bar's close button the way a user would.
        from qt.core import QToolButton
        b = self.gui.findChild(QToolButton, 'adwaita_window_button')
        print('CLOSEBTN found', b is not None, flush=True)
        if b is not None:
            b.click()
        self.later(8000, lambda: (print('CLOSEBTN still running', flush=True), self.next()))

    def quit(self):
        QApplication.instance().exit(0)
