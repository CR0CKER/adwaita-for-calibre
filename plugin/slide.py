"""Side panes slide in and out, like libadwaita's split views.

calibre lays the main window out in `CentralContainer.do_wide_layout` and shows or hides a pane
instantly. Laying the window out on every animation frame is far too slow here (each frame
re-lays out the book grid or list and repaints the whole window: 70-80 ms per frame, measured),
so the slide is played on snapshots:

1. Before calibre lays out the new state, the container is grabbed as it looks now.
2. calibre's own layout runs once, to the final state, under an overlay.
3. After one event-loop turn (so the views have finished their delayed item layout), the final
   state is grabbed too.
4. For DURATION_MS the overlay composes each frame from the two pictures: the pane slides in or
   out at its full width, the book area follows its edge (cropped, not reflowed), and the
   hairline moves with it. Then the overlay goes away; the real widgets are already in place.

Only the wide layout animates; the narrow layout and calibre's "Disable animations" setting keep
the instant behaviour. A resize or a second toggle during a slide finishes it at once.
"""

import os
import time

from qt.core import QColor, QEasingCurve, QPainter, QRectF, Qt, QTimer, QVariantAnimation, QWidget

DURATION_MS = 200
PANES = ('tag_browser', 'book_details')
TIMING = bool(os.environ.get('ADWAITA_SLIDE_TIMING'))


def _animations_enabled():
    try:
        from calibre.gui2 import config
        return not config['disable_animations']
    except Exception:  # noqa: BLE001 -- calibre internals may change; fall back to animating
        return True


class State:
    """A picture of the container plus where its panes and book area were."""

    def __init__(self, c, visible):
        self.pixmap = c.grab()
        self.dpr = self.pixmap.devicePixelRatio() or 1.0
        self.visible = dict(visible)
        self.left = c.tag_browser.geometry()
        self.right = c.book_details.geometry()
        self.content_x = c.left_handle.x() + c.left_handle.width()
        self.content_w = max(0, c.right_handle.x() - self.content_x)


class Overlay(QWidget):
    def __init__(self, container, before):
        super().__init__(container)
        self.c = container
        self.before = before
        self.after = None
        self.changed = ()
        self.progress = {w: 1.0 if before.visible[w] else 0.0 for w in PANES}
        self.anim = None
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setGeometry(container.rect())
        self.show()
        self.raise_()

    def start(self):
        try:
            self.hide()
            bd = self.c.book_details
            self.c._adwaita_starting = True
            try:
                if bd.isVisible() and hasattr(bd, 'do_layout'):
                    # A pane that was just shown lays its cover out lazily; the picture needs it.
                    bd.do_layout(bd.rect())
                self.after = State(self.c, {w: bool(getattr(self.c.is_visible, w)) for w in PANES})
            finally:
                self.c._adwaita_starting = False
            self.show()
            self.raise_()
        except Exception as e:  # noqa: BLE001 -- never leave the overlay up: show the real widgets
            from calibre_plugins.adwaita_for_calibre.main import debug
            debug('slide skipped', repr(e))
            self.finish()
            return
        self.changed = [w for w in PANES if self.before.visible[w] != self.after.visible[w]]
        if not self.changed:
            self.finish()
            return
        self.anim = a = QVariantAnimation(self)
        a.setDuration(DURATION_MS)
        a.setStartValue(0.0)
        a.setEndValue(1.0)
        a.setEasingCurve(QEasingCurve.Type.OutCubic)
        a.valueChanged.connect(self.step)
        a.finished.connect(self.finish)
        a.start()

    def step(self, t):
        t = float(t)
        for w in self.changed:
            self.progress[w] = t if self.after.visible[w] else 1.0 - t
        self.update()

    def finish(self):
        if self.anim is not None:
            self.anim.stop()
        if getattr(self.c, '_adwaita_overlay', None) is self:
            self.c._adwaita_overlay = None
        self.hide()
        self.deleteLater()

    def _pane_source(self, which):
        """The state that shows the pane at full size."""
        if self.before.visible[which] or self.after is None:
            return self.before
        return self.after

    def _content_source(self):
        b, a = self.before, self.after
        return b if a is None or b.content_w >= a.content_w else a

    @staticmethod
    def _draw(p, state, target, sx):
        d = state.dpr
        p.drawPixmap(target, state.pixmap, QRectF(sx * d, 0, target.width() * d, target.height() * d))

    def paintEvent(self, ev):
        from calibre_plugins.adwaita_for_calibre import panes
        st = time.perf_counter()
        p = QPainter(self)
        bg = QColor(panes._tokens()['view_bg'])
        h, W = self.height(), self.width()
        p.fillRect(self.rect(), bg)
        hw_l = self.c.left_handle.width() or self.c.right_handle.width() or 6
        hw_r = self.c.right_handle.width() or hw_l

        ls, rs = self._pane_source('tag_browser'), self._pane_source('book_details')
        lw = ls.left.width() if ls.visible['tag_browser'] else 0
        rw = rs.right.width() if rs.visible['book_details'] else 0
        pl, pr = self.progress['tag_browser'], self.progress['book_details']
        lx = pl * lw                  # right edge of the left pane
        rx = W - pr * rw              # left edge of the right pane
        cx = lx + (hw_l if pl > 0 else 0) * min(1.0, pl * 4)
        cr = rx - (hw_r if pr > 0 else 0) * min(1.0, pr * 4)

        # Book area: cropped from the state where it is wider, anchored at its left edge.
        cs = self._content_source()
        cw = max(0.0, min(cr - cx, cs.content_w))
        if cw > 0:
            self._draw(p, cs, QRectF(cx, 0, cw, h), cs.content_x)
        line = panes._hairline(bg.lightness() < 128)
        if pl > 0 and lw:
            self._draw(p, ls, QRectF(lx - lw, 0, lw, h), ls.left.x())
            p.fillRect(QRectF(lx, 0, 1, h), line)
        if pr > 0 and rw:
            self._draw(p, rs, QRectF(rx, 0, rw, h), rs.right.x())
            p.fillRect(QRectF(rx - 1, 0, 1, h), line)
        p.end()
        if TIMING:
            print(f'SLIDEFRAME {time.perf_counter() * 1000 % 100000:.0f} '
                  f'{(time.perf_counter() - st) * 1000:.1f} ms', flush=True)


def install():
    from calibre.gui2.central import CentralContainer, Layout

    if getattr(CentralContainer, '_adwaita_slide', False):
        return
    orig_relayout = CentralContainer.relayout

    def relayout(self):
        if getattr(self, '_adwaita_starting', False):  # re-entered while taking the picture
            orig_relayout(self)
            return
        now = {w: bool(getattr(self.is_visible, w)) for w in PANES}
        last = getattr(self, '_adwaita_last', None)
        self._adwaita_last = now
        current = getattr(self, '_adwaita_overlay', None)
        if current is not None:
            current.finish()  # a resize or another toggle: jump to the end
        changed = last is not None and now != last
        if not (changed and self.layout is Layout.wide and self.isVisible() and _animations_enabled()):
            orig_relayout(self)
            return
        try:
            # The widgets still show the previous state: calibre has only flipped the flags.
            before = State(self, last)
        except RuntimeError:
            orig_relayout(self)
            return
        orig_relayout(self)
        self._adwaita_overlay = ov = Overlay(self, before)
        QTimer.singleShot(0, ov.start)

    CentralContainer.relayout = relayout
    CentralContainer._adwaita_slide = True
