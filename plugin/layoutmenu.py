"""The status bar's Layout popup as a libadwaita popover.

calibre draws it itself (`calibre/gui2/layout_menu.py`): 64 px icons sized for its colourful
icon set, and a backdrop of the window colour at 90 % opacity that all but disappears over
bright covers. Here: an opaque popover (popover colour, 12 px radius, hairline border), 32 px
icons, and libadwaita's rounded hover.
"""

from calibre_plugins.adwaita_for_calibre import adwaita
from qt.core import QColor, QPainter, QPainterPath, QPen, QRectF, QSize

ICON_SIZE = 32
RADIUS = 12


def _tokens():
    from qt.core import QApplication
    return adwaita.tokens(QApplication.instance().palette_manager.is_dark_theme)


def install():
    try:
        from calibre.gui2 import layout_menu as lm
    except ImportError:
        return False
    if getattr(lm.LayoutMenuInner, '_adwaita_patched', False):
        return True

    def item_size_hint(self):
        br = self.fm.boundingRect(self.text)
        w = max(br.width(), ICON_SZ_PAD) + 16
        h = 2 * self.fm.lineSpacing() + ICON_SIZE + 2 * self.VMARGIN + 8
        return QSize(w, h)

    ICON_SZ_PAD = ICON_SIZE + 24
    original_item_paint = lm.LayoutItem.paintEvent

    def item_paint(self, ev):
        if self.mouse_over:
            t = _tokens()
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            path = QPainterPath()
            path.addRoundedRect(QRectF(self.rect()), 6, 6)
            c = QColor(t['fg'])
            c.setAlphaF(0.07)
            p.fillPath(path, c)
            p.end()
            # calibre's own hover panel would draw over ours; paint the rest without it.
            self.mouse_over = False
            try:
                original_item_paint(self, ev)
            finally:
                self.mouse_over = True
        else:
            original_item_paint(self, ev)

    def inner_paint(self, ev):
        t = _tokens()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), RADIUS, RADIUS)
        p.fillPath(path, QColor(t['popover_bg']))
        border = QColor(t['fg'])
        border.setAlphaF(0.15)
        p.setPen(QPen(border, 1))
        p.drawPath(path)
        p.end()

    original_init = lm.LayoutMenuInner.delayed_init

    def delayed_init(self):
        lay = self.layout()
        if lay is not None:
            lay.setContentsMargins(8, 8, 8, 8)
            lay.setSpacing(4)
        original_init(self)

    lm.LayoutItem.sizeHint = item_size_hint
    lm.LayoutItem.paintEvent = item_paint
    lm.LayoutMenuInner.paintEvent = inner_paint
    lm.LayoutMenuInner.delayed_init = delayed_init
    lm.LayoutMenuInner._adwaita_patched = True
    return True
