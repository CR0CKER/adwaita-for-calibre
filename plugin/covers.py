"""Book covers as libadwaita cards, so white covers stand out on a white grid.

libadwaita's .card: box-shadow: 0 0 0 1px rgb(0 0 6 / 3%), 0 1px 3px 1px rgb(0 0 6 / 7%),
0 2px 6px 2px rgb(0 0 6 / 3%). On dark backgrounds that shadow all but vanishes, so dark mode
adds a faint light hairline instead, keeping dark covers off the dark grid.

Hooks: the cover grid's CoverDelegate.paint_cover and the book details panel's CoverView. Both
follow calibre's cover corner radius setting.
"""

from qt.core import QColor, QPainter, QPainterPath, QRect, QRectF, QSize, Qt

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


def paint_card(painter, rect):
    if rect.width() < 4 or rect.height() < 4:
        return
    painter.save()
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
    painter.restore()


def install():
    try:
        from calibre.gui2.book_details import CoverView
        from calibre.gui2.library.alternate_views import CoverDelegate
    except ImportError:
        return False
    if getattr(CoverDelegate, '_adwaita_patched', False):
        return True

    original_cover = CoverDelegate.paint_cover

    def paint_cover(self, painter, rect, pixmap):
        paint_card(painter, rect)
        original_cover(self, painter, rect, pixmap)

    original_details = CoverView.paintEvent

    def details_paint(self, ev):
        # Same target rectangle calibre computes in CoverView.paintEvent.
        canvas = self.rect()
        w, h = self.current_pixmap_size.width(), self.current_pixmap_size.height()
        x = max(canvas.width() - w, 0) // 2
        y = max(canvas.height() - h, 0) // 2
        # The pixmap keeps its aspect ratio inside that rectangle.
        size = QSize(self.pixmap.size())
        size.scale(QSize(w, h), Qt.AspectRatioMode.KeepAspectRatio)
        target = QRect(x + (w - size.width()) // 2, y + (h - size.height()) // 2, size.width(), size.height())
        p = QPainter(self)
        paint_card(p, target)
        p.end()
        original_details(self, ev)

    CoverDelegate.paint_cover = paint_cover
    CoverView.paintEvent = details_paint
    CoverDelegate._adwaita_patched = True
    return True
