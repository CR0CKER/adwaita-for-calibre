import os
import traceback

from calibre.gui2.actions import InterfaceAction
from qt.core import QApplication, QPoint, Qt, QTimer


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
            ('main', self.main), ('jobsbutton', self.jobsbutton), ('focus', self.focus),
            ('statusbar', self.statusbar), ('spinner', self.spinner), ('hover', self.hover),
            ('layoutmenu', self.layoutmenu), ('scrolled', self.scrolled),
            ('sidebar', self.sidebar), ('perf', self.perf),
            ('edges', self.edges), ('details', self.details), ('toggles', self.toggles),
            ('sidetoggle', self.sidetoggle), ('covertoggle', self.covertoggle), ('slide', self.slide),
            ('coverroom', self.coverroom), ('mdcheck', self.mdcheck),
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
                                     self.details_extent(bd, tb),
                                     self.save(self.gui, 'details'), self.next()))
        self.later(500, shoot)

    def details_extent(self, bd, tb):
        # With the cover above the text (narrow pane), the top shade runs across the whole pane,
        # over its 12 px insets; with the cover beside the text it must stay clear of the cover.
        from qt.core import QPoint
        sh = tb._adwaita_shades.top
        sx = sh.mapTo(self.gui, QPoint(0, 0)).x()
        bx = bd.mapTo(self.gui, QPoint(0, 0)).x()
        tx = tb.mapTo(self.gui, QPoint(0, 0)).x()
        print('DETAILS extent shade', (sx, sx + sh.width()), 'pane', (bx, bx + bd.width()),
              'text', (tx, tx + tb.width()), flush=True)
        if tx - bx < 40:
            self.check((sx, sx + sh.width()) == (bx, bx + bd.width()),
                       f'details top shade spans the pane (shade {sx}+{sh.width()}, pane {bx}+{bd.width()})')
        else:
            self.check(sx >= tx, f'details top shade stays clear of the cover beside the text ({sx} >= {tx})')

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
                                     self.sidebar_extent(tv, sh),
                                     self.save(self.gui, 'sidebar'), self.next()))
        self.later(800, go)

    def sidebar_extent(self, tv, sh):
        # The scroll shades must run edge to edge across the pane, not just across the tree's
        # viewport (which sits inside calibre's layout margins).
        from qt.core import QPoint, QWidget

        def span(w):
            x = w.mapTo(self.gui, QPoint(0, 0)).x()
            return x, x + w.width()
        w = tv
        while w is not None and w is not self.gui:
            lay = QWidget.layout(w)
            m = lay.contentsMargins() if lay is not None else None
            print('SIDEBAR chain', type(w).__name__, w.objectName(), 'x', span(w),
                  'layout margins', (m.left(), m.top(), m.right(), m.bottom()) if m else None, flush=True)
            w = w.parentWidget()
        pane = self.gui.tb_widget if hasattr(self.gui, 'tb_widget') else tv.parentWidget()
        for name, s in (('top', sh.top), ('bottom', sh.bottom)):
            self.check(span(s) == span(pane),
                       f'tag browser {name} shade spans the pane (shade {span(s)}, pane {span(pane)})')
        hb = self.gui.search_bar
        header = hb.mapTo(self.gui, QPoint(0, hb.height())).y()
        st = sh.top.mapTo(self.gui, QPoint(0, 0)).y()
        self.check(st == header,
                   f'tag browser top shade starts at the header bar (shade {st}, header {header})')
        tb = tv.mapTo(self.gui, QPoint(0, tv.height())).y()
        sb_ = sh.bottom.mapTo(self.gui, QPoint(0, sh.bottom.height())).y()
        self.check(sb_ == tb, f'tag browser bottom shade ends on the bottom bar (shade {sb_}, tree {tb})')

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

    def coverroom(self):
        # The details cover's card shadow must fit inside the cover view: its outermost pixel
        # rows and columns are pure background (a clipped shadow reaches the edge).
        from calibre.gui2.book_details import CoverView
        for cv in self.gui.findChildren(CoverView):
            if not cv.isVisible():
                continue
            img = cv.grab().toImage()
            w, h = img.width(), img.height()
            bg = img.pixel(0, 0)

            def off(px, bg=bg):  # more than 3 levels away from the background in any channel
                return any(abs(((px >> sh) & 255) - ((bg >> sh) & 255)) > 3 for sh in (0, 8, 16))
            edge = [img.pixel(x, y) for x in range(w) for y in (0, h - 1)]
            edge += [img.pixel(x, y) for y in range(h) for x in (0, w - 1)]
            bad = sum(1 for px in edge if off(px))
            self.check(bad == 0, f'details cover shadow fits its view ({bad} edge pixels not background)')
        self.next()

    def slide(self):
        # Pane slide (plugin/slide.py): an overlay plays the slide while the real layout is
        # already final; then it goes away and the real widgets show the end state.
        c = self.gui.layout_container
        stack = self.gui.library_view.alternate_views.stack
        if os.environ.get('SLIDE_LIST'):
            self.gui.grid_view_button.setChecked(False)
        start_w = stack.geometry().width()
        seq = [('tag_browser_button', 'tb'), ('tag_browser_button', 'tb'),
               ('book_details_button', 'bd'), ('book_details_button', 'bd')]

        def step():
            if not seq:
                self.check(stack.geometry().width() == start_w, 'book area back to its width')
                self.next()
                return
            attr, tag = seq.pop(0)
            btn = getattr(c, attr)
            btn.click()
            state = 'open' if btn.isChecked() else 'close'

            def mid():
                ov = getattr(c, '_adwaita_overlay', None)
                self.check(ov is not None and ov.isVisible(), f'{tag} {state}: slide overlay playing')
                if not os.environ.get('ADWAITA_SLIDE_TIMING'):  # a grab stalls the animation
                    self.save(self.gui, f'slide-{tag}-{state}-mid')

            def end(tries=0):
                # A screenshot mid-slide stalls the event loop; give the slide up to 2 s to end.
                gone = getattr(c, '_adwaita_overlay', None) is None
                if not gone and tries < 15:
                    self.later(100, lambda: end(tries + 1))
                    return
                self.check(gone, f'{tag} {state}: overlay gone')
                step()
            self.later(int(os.environ.get('SLIDE_MID_MS') or 90), mid)
            self.later(500, end)
        step()

    def covertoggle(self):
        # The header bar's cover-browser toggle follows calibre's button and shows/hides the strip.
        from qt.core import QToolButton
        b = self.gui.search_bar.findChild(QToolButton, 'adwaita_cover_toggle')
        self.check(b is not None, 'cover browser toggle in the header bar')
        if b is None:
            self.next()
            return
        cb = self.gui.layout_container.cover_browser
        start = b.isChecked()
        b.click()

        def after_first():
            self.check(b.isChecked() != start and b.isChecked() == b._adwaita_target.isChecked(),
                       'cover browser toggle follows the strip')
            shown = 'shown' if b.isChecked() else 'hidden'
            self.check(cb.isVisible() == b.isChecked(), f'cover browser {shown}')
            if b.isChecked():
                from calibre_plugins.adwaita_for_calibre import panes
                from qt.core import QWidget
                pad = self.gui.layout_container.findChild(QWidget, 'adwaita_cover_browser_pad')
                self.check(cb.y() == panes.COVER_BROWSER_GAP and pad is not None and pad.isVisible()
                           and pad.y() == 0 and pad.height() == cb.y(),
                           f'cover browser padded {panes.COVER_BROWSER_GAP}px at the top (black pad)')
                self.save(self.gui, 'covertoggle-on')
            b.click()
            self.later(500, lambda: (self.check(b.isChecked() == start and cb.isVisible() == start,
                                                'cover browser back to its state'), self.next()))
        self.later(700, after_first)

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
        # calibre's Layout popup, opened from the header bar's main menu (its status-bar button
        # is hidden): it drops from the top right, under the header bar.
        from calibre.gui2.layout_menu import LayoutMenu
        from qt.core import QToolButton
        m = self.gui.findChild(LayoutMenu)
        lb = getattr(self.gui, 'layout_button', None)
        self.check(lb is not None and not lb.isVisible(), 'status bar Layout button hidden')
        mb = self.gui.search_bar.findChild(QToolButton, 'adwaita_main_menu')
        act = next((a for a in mb.menu().actions() if a.text().startswith('Layout')), None) if mb else None
        self.check(act is not None, 'Layout… in the main menu')
        if m is None or act is None:
            self.next()
            return
        act.trigger()

        def done():
            top = m.inner.mapTo(self.gui, QPoint(0, 0)).y()
            hb = self.gui.search_bar.mapTo(self.gui, QPoint(0, self.gui.search_bar.height())).y()
            self.check(m.isVisible() and hb <= top <= hb + 20,
                       f'Layout popup under the header bar (top {top}, header bottom {hb})')
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

    def jobsbutton(self):
        # The status bar is hidden by default (pref show_status_bar); Preferences -> Interface ->
        # "Show status bar" brings it back; while it is hidden, running jobs show as a header-bar
        # spinner button.
        from qt.core import QToolButton, QWidget
        gui = self.gui
        sb = gui.statusBar()
        jm = gui.job_manager
        self.check(sb.isHidden(), 'status bar hidden by default')
        b = gui.search_bar.findChild(QToolButton, 'adwaita_jobs_button')
        self.check(b is not None, 'jobs button in the header bar')
        main_menu = gui.search_bar.findChild(QToolButton, 'adwaita_main_menu').menu()
        self.check(not any(a.text() == 'Show status bar' for a in main_menu.actions()),
                   'no status bar entry at the top of the main menu')
        pm = gui.iactions['Preferences'].preferences_menu
        pm.aboutToShow.emit()  # what opening Preferences in the main menu does
        look = gui.iactions['Preferences'].action_map['Look & Feel']
        subs = [a.menu() for a in pm.actions() if a.menu() is not None]
        interface = next((m for m in subs if look in m.actions()), None)
        entries = interface.actions() if interface is not None else []
        entry = next((a for a in entries if a.text() == 'Show status bar'), None)
        where = interface.title() if interface is not None else None
        self.check(entry is not None and entry.isCheckable() and not entry.isChecked(),
                   f'unchecked "Show status bar" under Preferences -> {where}')
        if b is None or entry is None:
            self.next()
            return
        self.check(b.isHidden(), 'jobs button hidden with no jobs')
        jm.job_added.emit(1)  # what calibre's JobManager emits when a job starts
        self.check(not b.isHidden(), 'jobs button shown while a job runs')
        self.check('One running job' in b.toolTip(), f'jobs button tooltip ({b.toolTip()!r})')
        spinner = b.findChildren(QWidget)[0]
        self.check(spinner.running(), 'spinner animates while a job runs')

        def shown():
            self.save(gui.search_bar, 'jobsbutton')
            entry.trigger()
            self.check(not sb.isHidden(), 'menu entry shows the status bar')
            from calibre_plugins.adwaita_for_calibre.main import prefs
            self.check(prefs()['show_status_bar'] is True, 'menu entry saves the choice')
            self.check(b.isHidden(), 'jobs button hidden while the status bar shows')
            entry.trigger()
            self.check(sb.isHidden(), 'menu entry hides the status bar again')
            self.check(not b.isHidden(), 'jobs button back once the status bar hides')
            jm.job_done.emit(0)
            self.check(b.isHidden(), 'jobs button hidden when the last job ends')
            self.check(not spinner.running(), 'spinner stops when the last job ends')
            # Ctrl+Shift+S, the Hide Statusbar plugin's shortcut, through calibre's keyboard manager.
            keys = [k.toString() for k in gui.keyboard.keys_map.get('adwaita toggle status bar', ())]
            self.check(keys == ['Ctrl+Shift+S'], f'status bar shortcut is Ctrl+Shift+S ({keys})')
            self.check(entry in gui.actions(), 'shortcut works with the menu closed')
            sb.setVisible(True)  # shown by something else: the entry's check mark is stale
            entry.trigger()
            self.check(sb.isHidden(), 'shortcut toggles from the bar itself, not a stale check mark')
            self.check(prefs()['show_status_bar'] is False and not entry.isChecked(),
                       'shortcut saves the choice and updates the check mark')
            self.next()
        self.later(600, shown)

    def spinner(self):
        # The header-bar jobs spinner: how often it actually repaints, how long a repaint takes,
        # and which other widgets repaint along with it (all with a fake running job).
        import time

        from qt.core import QEvent, QObject, QToolButton, QWidget
        gui = self.gui
        b = gui.search_bar.findChild(QToolButton, 'adwaita_jobs_button')
        if b is None:
            self.next()
            return
        spinner = b.findChildren(QWidget)[0]
        stamps, others = [], {}

        class Watch(QObject):
            def eventFilter(self, obj, ev):
                if ev.type() == QEvent.Type.Paint:
                    if obj is spinner:
                        stamps.append(time.perf_counter())
                    else:
                        k = type(obj).__name__ + ':' + obj.objectName()
                        others[k] = others.get(k, 0) + 1
                return False
        w = Watch(gui)
        watched = [spinner] + [x for x in gui.findChildren(QWidget) if x.isVisible()] + [gui]
        for x in watched:
            x.installEventFilter(w)
        gui.job_manager.job_added.emit(1)

        def done():
            for x in watched:
                x.removeEventFilter(w)
            gaps = sorted((b2 - a) * 1000 for a, b2 in zip(stamps, stamps[1:], strict=False))
            if gaps:
                n = len(gaps)
                print(f'SPIN paints {len(stamps)} in 3 s; gap ms median {gaps[n // 2]:.1f} '
                      f'p90 {gaps[int(n * 0.9)]:.1f} max {gaps[-1]:.1f}', flush=True)
            top = sorted(others.items(), key=lambda kv: -kv[1])[:8]
            print('SPIN also repainted', top, flush=True)
            st = time.perf_counter()
            for _ in range(30):
                spinner.repaint()
            print(f'SPIN repaint {(time.perf_counter() - st) * 1000 / 30:.2f} ms', flush=True)
            gui.job_manager.job_done.emit(0)
            self.next()
        self.later(3000, done)

    def statusbar(self):
        # Toggle the status bar on and off again, as the Preferences entry / calibre's Layout do.
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
                if os.environ.get('ADWAITA_TREE'):
                    self.tree(w)
                self.save(w, name)
                w.reject()
        self.later(3000, grab)
        opener()
        self.later(500, self.next)

    def tree(self, root, depth=0, max_depth=9):
        # Widgets that paint a background of their own, with geometry: finds who draws what.
        from qt.core import QPoint, QWidget
        for w in root.findChildren(QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly):
            if not w.isVisible():
                continue
            p = w.mapTo(root.window(), QPoint(0, 0))
            fill = w.autoFillBackground() or w.testAttribute(Qt.WidgetAttribute.WA_StyledBackground)
            print('TREE', '  ' * depth + type(w).__name__, w.objectName() or '-', p.x(), p.y(),
                  w.width(), w.height(), 'fill' if fill else '', flush=True)
            if depth < max_depth:
                self.tree(w, depth + 1, max_depth)

    def mdcheck(self):
        # Edit metadata (metadata.py tidy_dialog / status icons): one surface, top-aligned form,
        # sort-field state as a coloured icon only, dimmed row buttons that light up on hover.
        from calibre.gui2.metadata.single import ScrollArea
        from qt.core import QEvent, QGraphicsOpacityEffect, QToolButton

        def run():
            d = QApplication.activeModalWidget()
            try:
                checks(d)
            except Exception:
                traceback.print_exc()
                self.check(False, 'metadata checks ran without errors')
                if d is not None:
                    d.reject()
                self.later(500, self.next)

        def checks(d):
            self.check(d is not None and d.findChild(ScrollArea) is not None, 'edit metadata dialog opened')
            sa = d.findChild(ScrollArea)
            self.check(not sa.viewport().autoFillBackground() and not sa.widget().autoFillBackground(),
                       'metadata: one surface (scroll area transparent)')
            rating_y = d.rating.mapTo(d, QPoint(0, 0)).y()
            self.check(rating_y < d.height() // 2, f'metadata: fields top-aligned (Rating at y={rating_y})')
            ts = d.title_sort
            self.check(ts.styleSheet() == '', 'metadata: no coloured sort border')
            ts.setText(ts.text() + ' x')
            warn = ts.status_actions[1]
            self.check(warn.isVisible() and not warn.icon().isNull(),
                       'metadata: warning icon when sort differs')
            pub_r = d.publisher.mapTo(d, QPoint(d.publisher.width(), 0)).x()
            lang_r = d.languages.mapTo(d, QPoint(d.languages.width(), 0)).x()
            self.check(abs(pub_r - lang_r) <= 1,
                       f'metadata: Languages ends with the other fields ({lang_r} vs {pub_r})')
            dimmed = [b for b in d.findChildren(QToolButton)
                      if isinstance(b.graphicsEffect(), QGraphicsOpacityEffect)]
            self.check(len(dimmed) >= 6, f'metadata: row buttons dimmed ({len(dimmed)})')
            if dimmed:
                b = dimmed[0]
                QApplication.sendEvent(b, QEvent(QEvent.Type.Enter))
                self.check(b.graphicsEffect().opacity() == 1.0, 'metadata: row button full on hover')
                QApplication.sendEvent(b, QEvent(QEvent.Type.Leave))
            # Padding inside the formats list and the comments editor: their viewports are inset.
            from calibre.gui2.comments_editor import EditorWidget
            from calibre.gui2.metadata.basic_widgets import FormatList
            for cls, need in ((FormatList, 6), (EditorWidget, 8)):
                w = d.findChild(cls)
                if w is not None:
                    inset = w.viewport().geometry().top()
                    self.check(inset >= need, f'metadata: {cls.__name__} padded ({inset}px >= {need}px)')
            d.comments.html = '<p>' + 'A comment long enough to wrap onto several lines. ' * 12 + '</p>'
            self.later(300, lambda: (self.save(d, 'mdcheck'), d.reject(), self.later(500, self.next)))
        self.later(2500, run)
        self.gui.iactions['Edit Metadata'].edit_metadata(False)

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
