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

    failures: list = []

    def check(self, ok, what):
        """Smoke assertion: printed, and remembered so the run exits non-zero (scripts/smoke.sh)."""
        print(f'SMOKE {"ok  " if ok else "FAIL"} {what}', flush=True)
        if not ok:
            self.failures.append(what)

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
            ('edges', self.edges), ('details', self.details), ('toggles', self.toggles),
            ('sidetoggle', self.sidetoggle),
            ('reset', self.reset),
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

    def details(self):
        # Book details with a long description, scrolled: text padding and the top shade.
        from calibre.gui2.book_details import BookDetails
        from qt.core import QTextBrowser
        bd = self.gui.findChild(BookDetails)
        tb = bd.findChild(QTextBrowser)
        tb.setHtml('<p>' + ' '.join(['A long description that needs to scroll.'] * 120) + '</p>')

        def shoot():
            sb = tb.verticalScrollBar()
            sb.setValue(sb.maximum() // 3)
            self.later(300, lambda: (print('DETAILS shade', tb._adwaita_shades.top.isVisible(),
                                           flush=True),
                                     self.save(self.gui, 'details'), self.next()))
        self.later(500, shoot)

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
                return ms

            budget = float(os.environ.get('SMOKE_FRAME_BUDGET_MS', '30'))
            ms = t('grid viewport, card shadow on', vp)
            self.check(ms <= budget, f'grid repaint {ms:.1f} ms <= {budget:.0f} ms budget')
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

    def edges(self):
        # Every visible widget whose top or bottom edge lies near the header bar's bottom edge.
        from qt.core import QPoint, QWidget
        hb = self.gui.search_bar
        y = hb.mapTo(self.gui, QPoint(0, hb.height())).y()
        print('EDGE header bottom at y =', y, flush=True)
        stack = self.gui.library_view.alternate_views.stack
        stack_top = stack.mapTo(self.gui, QPoint(0, 0)).y()
        self.check(stack_top == y,
                   f'book area starts at the header bar (stack top {stack_top}, header bottom {y})')
        for w in self.gui.findChildren(QWidget):
            if not w.isVisible() or w.isWindow():
                continue
            top = w.mapTo(self.gui, QPoint(0, 0)).y()
            bottom = top + w.height()
            if 0 < w.height() <= 4 and abs(top - y) <= 1 and w.width() > 40:
                self.check(False, f'no thin strip under the header bar ({type(w).__name__} h={w.height()})')
            if abs(top - y) <= 3 or abs(bottom - y) <= 3 or (w.height() <= 4 and abs(top - y) <= 12):
                print('EDGE', type(w).__name__, w.objectName(), 'top', top, 'h', w.height(), 'w', w.width(),
                      'ss' if w.styleSheet() else '', flush=True)
        self.next()

    def sidetoggle(self):
        # The header bar's sidebar toggles: they follow the panes and hide/show them on click.
        from qt.core import QToolButton
        toggles = self.gui.search_bar.findChildren(QToolButton, 'adwaita_sidebar_toggle')
        self.check(len(toggles) == 2, f'two sidebar toggles in the header bar (found {len(toggles)})')
        stack = self.gui.library_view.alternate_views.stack
        seq = [b for b in toggles for _ in (0, 1)]  # each clicked twice: hide, show

        def step():
            if not seq:
                self.next()
                return
            b = seq.pop(0)
            before = stack.geometry().width()
            b.click()

            def report():
                t = b._adwaita_target
                self.check(b.isChecked() == t.isChecked(), f'{t.label} toggle follows the pane')
                after = stack.geometry().width()
                if t.isChecked():
                    self.check(after < before, f'{t.label} toggle shows the pane ({before} -> {after})')
                else:
                    self.check(after > before, f'{t.label} toggle hides the pane ({before} -> {after})')
                    self.save(self.gui, f'sidetoggle-{t.name}')
                step()
            self.later(500, report)
        step()

    def toggles(self):
        # Hide and re-show panes through calibre's own layout buttons; report geometry.
        buttons = {b.label: b for b in getattr(self.gui, 'layout_buttons', [])}
        names = [n for n in ('Tag browser', 'Book details', 'Cover browser') if n in buttons]
        seq = [(n, v) for n in names for v in (not buttons[n].isChecked(), buttons[n].isChecked())]
        # Baseline width of the book area before any pane is toggled.
        self._toggle_base = self.gui.library_view.alternate_views.stack.geometry().width()

        def step():
            if not seq:
                self.next()
                return
            name, visible = seq.pop(0)
            b = buttons[name]
            if b.isChecked() != visible:
                b.click()
            stack = self.gui.library_view.alternate_views.stack
            state = 'visible' if visible else 'hidden'

            def report():
                g = stack.geometry()
                print('TOGGLE', name, state, 'stack', g, flush=True)
                if name in ('Tag browser', 'Book details'):
                    base = self._toggle_base
                    if visible:
                        self.check(g.width() == base, f'{name} shown again: book area back to {base}px')
                    else:
                        self.check(g.width() > base, f'{name} hidden: book area wider ({g.width()} > {base})')
                step()
            self.later(500, report)
        step()

    def reset(self):
        # M4/L4: sync the viewer settings, then undo them as the Restore button does.
        from calibre.gui2 import gprefs
        from calibre.gui2.viewer.config import vprefs
        from calibre_plugins.adwaita_for_calibre import main as amain
        from calibre_plugins.adwaita_for_calibre import viewer
        prefs = amain.prefs()

        def state(label):
            print('RESET', label, 'names', gprefs['dark_palette_name'], gprefs['light_palette_name'],
                  'keys', sorted(gprefs['dark_palettes'] or {}), 'scheme',
                  (vprefs['session_data'] or {}).get('current_color_scheme'),
                  'flag', prefs['viewer_scheme_set'], flush=True)
        print('RESET viewer_running', viewer.viewer_running(), flush=True)
        state('before')
        viewer.sync(amain._THEME, prefs)
        state('synced')
        print('RESET unsync returned', viewer.unsync(prefs), flush=True)
        state('restored')
        self.next()

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
                self.check(current() == which(), f'view switcher follows {kind} {key} (shown {current()})')
                pos = (self.gui.search.width(), sw.x())
                first = getattr(self, '_views_pos', None)
                if first is None:
                    self._views_pos = pos
                else:
                    self.check(pos == first, f'header bar does not move on {kind} {key}')
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
            self.check(True, 'toolbar saves without Preferences (it is in the main menu)')
        except AbortCommit:
            self.check(False, 'toolbar saves without Preferences (it is in the main menu)')
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
        if os.environ.get('ADWAITA_SMOKE'):
            print(f'SMOKE {"OK" if not self.failures else "FAILED"} '
                  f'({len(self.failures)} failure{"s" if len(self.failures) != 1 else ""})', flush=True)
        QApplication.instance().exit(1 if self.failures else 0)
