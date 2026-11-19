"""Book covers as libadwaita cards, so white covers stand out on a white grid.

libadwaita's .card: box-shadow: 0 0 0 1px rgb(0 0 6 / 3%), 0 1px 3px 1px rgb(0 0 6 / 7%),
0 2px 6px 2px rgb(0 0 6 / 3%). On dark backgrounds that shadow all but vanishes, so dark mode
adds a faint light hairline instead, keeping dark covers off the dark grid.

Hooks: the cover grid's CoverDelegate.paint_cover and the book details panel's CoverView. Both
follow calibre's cover corner radius setting.
"""

from qt.core import QColor, QPainter, QPainterPath, QRect, QRectF, QSize, Qt

_ORIG_COVER = None

# Room around the details-panel cover for the shadow: spread + offset + blur of the wider layer.
SHADOW_ROOM = 10

# (spread, y offset, blur, alpha) per libadwaita shadow layer.
LAYERS = ((1, 1, 3, 0.07), (2, 2, 6, 0.03))


def _dark():
    from qt.core import QApplication
    return QApplication.instance().palette_manager.is_dark_theme


def _rounded(rect, grow=0.0):
    from calibre.gui2 import gprefs
    r = gprefs['cover_corner_radius']
    path = QPainterPath()
    rect = QRectF(rect).adjusted(-grow, -grow, grow, grow)
    if r > 0:
        relative = gprefs['cover_corner_radius_unit'] == '%'
        mode = Qt.SizeMode.RelativeSize if relative else Qt.SizeMode.AbsoluteSize
        extra = 0 if mode == Qt.SizeMode.RelativeSize else grow
        path.addRoundedRect(rect, r + extra, r + extra, mode)
    else:
        path.addRect(rect)
    return path


# The shadow is costly to draw (about 20 anti-aliased path rings); scrolling the grid repainted
# it for every cover in every frame and more than doubled the paint time. Render it once per
# cover size, mode and corner setting into a pixmap and stamp that.
PAD = 12  # room around the cover inside the cached pixmap: spread + offset + blur
EDGE_RADIUS = 16  # covers the largest usual corner radius; the strips must include the rounding
_CACHE = {}
_CACHE_MAX = 64


def _draw_card(painter, rect):
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    cover = _rounded(rect)
    for spread, dy, blur, alpha in LAYERS:
        # Stacked rings, each alpha/steps: dense near the cover, fading out over the blur.
        steps = max(2, blur * 2)
        for i in range(steps):
            grow = spread + blur * (i + 1) / steps
            ring = _rounded(QRect(rect).translated(0, dy), grow).subtracted(cover)
            c = QColor(0, 0, 6)
            c.setAlphaF(alpha / steps)
            painter.fillPath(ring, c)
    hair = _rounded(rect, 1).subtracted(cover)
    edge = QColor(255, 255, 255) if _dark() else QColor(0, 0, 6)
    edge.setAlphaF(0.08 if _dark() else 0.06)
    painter.fillPath(hair, edge)


def _card_pixmap(w, h, dpr):
    from calibre.gui2 import gprefs
    from qt.core import QPixmap
    key = (w, h, round(dpr * 100), _dark(), gprefs['cover_corner_radius'], gprefs['cover_corner_radius_unit'])
    pm = _CACHE.get(key)
    if pm is None:
        if len(_CACHE) >= _CACHE_MAX:
            _CACHE.clear()
        pm = QPixmap(round((w + 2 * PAD) * dpr), round((h + 2 * PAD) * dpr))
        pm.setDevicePixelRatio(dpr)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        _draw_card(p, QRect(PAD, PAD, w, h))
        p.end()
        _CACHE[key] = pm
    return pm


def paint_card(painter, rect):
    if rect.width() < 4 or rect.height() < 4:
        return
    dev = painter.device()
    dpr = dev.devicePixelRatioF() if dev is not None and hasattr(dev, 'devicePixelRatioF') else 1.0
    pm = _card_pixmap(rect.width(), rect.height(), dpr)
    # Only the frame around the cover: the inside is transparent and hidden by the cover anyway,
    # and blending it cost several ms per frame on a full grid.
    from qt.core import QRectF
    W, H = rect.width() + 2 * PAD, rect.height() + 2 * PAD
    E = PAD + EDGE_RADIUS
    x0, y0 = rect.x() - PAD, rect.y() - PAD
    for sx, sy, sw, sh in ((0, 0, W, E), (0, H - E, W, E), (0, E, E, H - 2 * E), (W - E, E, E, H - 2 * E)):
        if sw > 0 and sh > 0:
            painter.drawPixmap(QRectF(x0 + sx, y0 + sy, sw, sh), pm,
                               QRectF(sx * dpr, sy * dpr, sw * dpr, sh * dpr))


def install():
    try:
        from calibre.gui2.book_details import CoverView
        from calibre.gui2.library.alternate_views import CoverDelegate
    except ImportError:
        return False
    if getattr(CoverDelegate, '_adwaita_patched', False):
        return True

    global _ORIG_COVER
    original_cover = _ORIG_COVER = CoverDelegate.paint_cover

    def paint_cover(self, painter, rect, pixmap):
        paint_card(painter, rect)
        original_cover(self, painter, rect, pixmap)

    original_details = CoverView.paintEvent

    def details_paint(self, ev):
        # Clamp the cover inside the view minus SHADOW_ROOM at paint time. details_layout does
        # the same, but the view sits in a QSplitter, which resizes it without calling
        # do_layout; the stale size then filled the new height and the card shadow was clipped
        # at the view's edges. calibre's paintEvent reads _current_pixmap_size, so set it for
        # this paint only (the animation keeps driving the real value).
        canvas = self.rect()
        current = QSize(self._current_pixmap_size)
        avail = QSize(max(1, canvas.width() - 2 * SHADOW_ROOM), max(1, canvas.height() - 2 * SHADOW_ROOM))
        size = QSize(current)
        if size.width() > avail.width() or size.height() > avail.height():
            size.scale(avail, Qt.AspectRatioMode.KeepAspectRatio)
        self._current_pixmap_size = size
        try:
            # Same target rectangle calibre computes in CoverView.paintEvent.
            w, h = size.width(), size.height()
            x = max(canvas.width() - w, 0) // 2
            y = max(canvas.height() - h, 0) // 2
            # The pixmap keeps its aspect ratio inside that rectangle.
            psize = QSize(self.pixmap.size())
            psize.scale(QSize(w, h), Qt.AspectRatioMode.KeepAspectRatio)
            target = QRect(x + (w - psize.width()) // 2, y + (h - psize.height()) // 2,
                           psize.width(), psize.height())
            p = QPainter(self)
            paint_card(p, target)
            p.end()
            original_details(self, ev)
        finally:
            self._current_pixmap_size = current

    original_layout = CoverView.do_layout

    def details_layout(self):
        # calibre sizes the cover to fill the view exactly, which leaves no room for the card
        # shadow (it was clipped left and right). Fit it inside the view minus SHADOW_ROOM.
        original_layout(self)
        r = self.rect()
        avail = QSize(max(1, r.width() - 2 * SHADOW_ROOM), max(1, r.height() - 2 * SHADOW_ROOM))
        size = QSize(self.current_pixmap_size)
        if size.width() > avail.width() or size.height() > avail.height():
            size.scale(avail, Qt.AspectRatioMode.KeepAspectRatio)
            self.pwidth, self.pheight = size.width(), size.height()
            self.current_pixmap_size = size
            self.animation.setEndValue(size)

    CoverDelegate.paint_cover = paint_cover
    CoverView.paintEvent = details_paint
    CoverView.do_layout = details_layout
    CoverDelegate._adwaita_patched = True
    return True
