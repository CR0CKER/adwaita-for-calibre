"""The Edit metadata dialog.

* Format buttons (add/remove format, cover/metadata from format) at 20 px like the dialog's other
  icons; calibre hard-codes 32 (FormatsManager.ICON_SIZE).
* The cover preview as a card: inset so its shadow fits, like the book details cover.
* Sort fields: calibre marks them with hard-coded green/red 2 px borders
  (widgets.stylesheet_for_lineedit) plus a check / warning icon. The border is dropped; the icon
  carries the state, in libadwaita's success / warning colour.
* One surface: calibre's scroll area paints the window colour over the dialog colour, leaving a
  lighter frame in the dialog margin. Its viewport and content are made transparent.
* Default layout: the middle column's upper spacer no longer pushes the fields to the vertical
  centre; Languages ends where the other fields do; the per-row buttons (clear, list, swap,
  copy) are dimmed until hovered.
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
    # No coloured border: the status icon (status_icons) carries the state.
    return ''


def _status_icons(self, ok, tooltip=''):
    """Colour the sort fields' check / warning icons (calibre's are plain glyphs, white with the
    Adwaita icon set)."""
    _ORIGINAL_STATUS(self, ok, tooltip)
    from calibre_plugins.adwaita_for_calibre import main
    from qt.core import QIcon
    try:
        d = main._current_image_dir()
        self.status_actions[0].setIcon(QIcon(f'{d}/status-ok.svg'))
        self.status_actions[1].setIcon(QIcon(f'{d}/status-warning.svg'))
    except Exception as e:  # noqa: BLE001 -- cosmetic; calibre's icons stay
        main.debug('sort status icons skipped', e)


_ORIGINAL_STATUS = None
DIM = 0.55  # opacity of the per-row buttons until hovered


class _HoverDim:
    """Event filter: a row button at DIM opacity, full while hovered or focused."""

    def __init__(self):
        from qt.core import QEvent, QObject

        class F(QObject):
            def eventFilter(self, obj, ev):
                t = ev.type()
                if t in (QEvent.Type.Enter, QEvent.Type.FocusIn):
                    _set_opacity(obj, 1.0)
                elif t in (QEvent.Type.Leave, QEvent.Type.FocusOut):
                    if not obj.underMouse() and not obj.hasFocus():
                        _set_opacity(obj, DIM)
                return False
        self.filter = F()


def _set_opacity(w, value):
    eff = w.graphicsEffect()
    if eff is not None:
        eff.setOpacity(value)


def _dim_row_buttons(dialog, forms):
    from qt.core import QGraphicsOpacityEffect
    keep = dialog.__dict__.setdefault('_adwaita_dim', _HoverDim())
    for form in forms:
        for b in form.findChildren(QToolButton):
            if (b.parentWidget() is not form
                    or b.toolButtonStyle() != Qt.ToolButtonStyle.ToolButtonIconOnly
                    or b.graphicsEffect() is not None):
                continue
            eff = QGraphicsOpacityEffect(b)
            eff.setOpacity(DIM)
            b.setGraphicsEffect(eff)
            b.installEventFilter(keep.filter)


def tidy_dialog(dialog):
    """One surface, a top-aligned form and quieter row buttons (default layout only for the
    layout parts)."""
    from calibre.gui2.metadata.single import ScrollArea
    from qt.core import QSizePolicy
    for sa in dialog.findChildren(ScrollArea):
        sa.viewport().setAutoFillBackground(False)
        if sa.widget() is not None:
            sa.widget().setAutoFillBackground(False)
    if type(dialog).__name__ != 'MetadataSingleDialog':
        return
    rating = getattr(dialog, 'rating', None)
    middle = rating.parentWidget() if rating is not None else None
    grid = middle.layout() if middle is not None else None
    if grid is not None and hasattr(grid, 'getItemPosition'):
        spacers = []
        for i in range(grid.count()):
            item = grid.itemAt(i)
            if item.spacerItem() is not None:
                spacers.append((grid.getItemPosition(i)[0], item.spacerItem()))
        if len(spacers) >= 2:
            # calibre: one expanding spacer above Rating, one above Download metadata. Keep
            # only the lower one, so the fields sit right under the cover actions.
            spacers.sort(key=lambda x: x[0])
            spacers[0][1].changeSize(10, 12, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            grid.invalidate()
        langs = getattr(dialog, 'languages', None)
        idx = grid.indexOf(langs) if langs is not None else -1
        if idx >= 0:
            row, col, rs, cs = grid.getItemPosition(idx)
            if cs > 1:  # it spans the clear-button column the other rows use
                grid.removeWidget(langs)
                grid.addWidget(langs, row, col, rs, cs - 1)
    content = dialog.findChild(ScrollArea)
    forms = [w for w in (content.widget() if content is not None else None, middle) if w is not None]
    _dim_row_buttons(dialog, forms)


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
    global _ORIGINAL_STATUS
    _ORIGINAL_STATUS = widgets.update_status_actions
    widgets.update_status_actions = _status_icons

    _ORIGINAL_PAINT = Cover.paintEvent
    Cover.paintEvent = _paint_cover

    original_init = MetadataSingleDialogBase.__init__

    def init(self, *a, **kw):
        original_init(self, *a, **kw)
        for step in (space_icon_labels, tidy_dialog):
            try:
                step(self)
            except Exception as e:  # noqa: BLE001 -- cosmetic; never break the dialog over looks
                from calibre_plugins.adwaita_for_calibre.main import debug
                debug(f'{step.__name__} skipped', e)

    MetadataSingleDialogBase.__init__ = init
    FormatsManager._adwaita_patched = True
    return True

