"""The Edit metadata dialog.

* Format buttons (add/remove format, cover/metadata from format) at 20 px like the dialog's other
  icons; calibre hard-codes 32 (FormatsManager.ICON_SIZE).
* The cover preview as a card: inset so its shadow fits, like the book details cover.
* Sort fields: calibre marks them with hard-coded green/red 2 px borders on a 3 px radius
  (widgets.stylesheet_for_lineedit). Use libadwaita's success/error colours on the 9 px entry.
* Tool buttons with a label next to the icon (Browse, Remove, Trim borders...): a little more room
  between icon and label than Qt's fixed 4 px.
"""

from calibre_plugins.adwaita_for_calibre import adwaita
from qt.core import QPainter, QRect, Qt, QToolButton

FORMAT_ICON = 20
COVER_ROOM = 10


def _tokens():
    from qt.core import QApplication
    return adwaita.tokens(QApplication.instance().palette_manager.is_dark_theme)


def space_icon_labels(root):
    """Qt puts a fixed 4 px between a tool button's icon and label (no stylesheet control);
    GNOME uses about 8. A leading space gives about the same gap."""
    for b in root.findChildren(QToolButton):
        text = b.text()
        if (text and not text.startswith(' ') and not b.icon().isNull()
                and b.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonTextBesideIcon):
            b.setText(' ' + text)


def _lineedit_stylesheet(ok, selector='QLineEdit'):
    if ok is None:
        return ''
    t = _tokens()
    col = adwaita.mix(t['success_bg'] if ok else t['destructive_bg'], t['window_bg'], 0.7)
    return f'{selector} {{ border: 2px solid {col}; border-radius: 9px }}'


def _paint_cover(self, ev):
    """calibre's ImageView.paintEvent, fitted COVER_ROOM inside the widget with a card shadow."""
    from calibre import fit_image
    from calibre.gui2 import clip_border_radius
    from calibre.gui2.widgets import draw_size
    from calibre_plugins.adwaita_for_calibre.covers import paint_card

    pmap = self._pixmap
    if pmap.isNull():
        return _ORIGINAL_PAINT(self, ev)
    p = QPainter(self)
    p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
    area = self.rect().adjusted(COVER_ROOM, COVER_ROOM, -COVER_ROOM, -COVER_ROOM)
    dpr = pmap.devicePixelRatio()
    w, h = pmap.width(), pmap.height()
    ow, oh = w, h
    pcw, pch = max(1, round(area.width() * dpr)), max(1, round(area.height() * dpr))
    scaled, nw, nh = fit_image(w, h, pcw, pch)
    if not scaled and (w != pcw or h != pch):
        scale = min(pcw / w, pch / h)
        nw, nh = int(w * scale), int(h * scale)
        scaled = True
    if scaled:
        pmap = pmap.scaled(nw, nh, Qt.AspectRatioMode.IgnoreAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
    w, h = int(pmap.width() / dpr), int(pmap.height() / dpr)
    target = QRect(area.x() + (area.width() - w) // 2, area.y() + (area.height() - h) // 2, w, h)
    paint_card(p, target)
    with clip_border_radius(p, target):
        p.drawPixmap(target, pmap)
    if self.show_size:
        draw_size(p, target, ow, oh)
    p.end()


_ORIGINAL_PAINT = None


def install():
    global _ORIGINAL_PAINT
    try:
        import calibre.gui2.widgets as widgets
        from calibre.gui2.metadata.basic_widgets import Cover, FormatsManager
        from calibre.gui2.metadata.single import MetadataSingleDialogBase
    except ImportError:
        return False
    if getattr(FormatsManager, '_adwaita_patched', False):
        return True
    FormatsManager.ICON_SIZE = FORMAT_ICON
    widgets.stylesheet_for_lineedit = _lineedit_stylesheet

    _ORIGINAL_PAINT = Cover.paintEvent
    Cover.paintEvent = _paint_cover

    original_init = MetadataSingleDialogBase.__init__

    def init(self, *a, **kw):
        original_init(self, *a, **kw)
        try:
            space_icon_labels(self)
        except Exception:
            pass

    MetadataSingleDialogBase.__init__ = init
    FormatsManager._adwaita_patched = True
    return True

