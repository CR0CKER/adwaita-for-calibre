"""Three-pane layout: pane | content | pane, all in one surface.

* The tag browser (left) and book details (right) use the content colour (`pane_bg`), so they read
  as part of the book area rather than of the header bar; a 1 px hairline (libadwaita's
  --border-color) on the pane's side of each splitter handle separates them.
* calibre's splitter grips (the dots, CalibreStyle's CE_Splitter) become that hairline; the rest
  of the handle takes the content colour. Panes stay resizable: the handle keeps its width, only
  its painting changes.
* The details pane gets 12 px insets, so the cover sits on it as a card.
"""

from qt.core import QColor, QPainter, Qt

INSET = 12


def _tokens():
    from calibre_plugins.adwaita_for_calibre import adwaita
    from qt.core import QApplication
    return adwaita.tokens(QApplication.instance().palette_manager.is_dark_theme)


def _hairline(dark):
    # libadwaita --border-color: currentColor at 15 % (white in dark, rgb(0 0 6 / 80%) in light).
    c = QColor(255, 255, 255) if dark else QColor(0, 0, 6)
    c.setAlphaF(0.15 if dark else 0.12)
    return c


def install(gui):
    from calibre.gui2.central import SplitterHandle

    # calibre keeps a 2 px divider for each hidden pane (cover browser, Quickview, side panels).
    # It is a separate strip the content cannot scroll under, so above the book area it showed as
    # a dark line under the header bar. Hidden panes take no space now; they reopen from the
    # Layout button or their shortcut, as before.
    SplitterHandle.COLLAPSED_SIZE = 0

    if not getattr(SplitterHandle, '_adwaita_patched', False):
        def paint(self, ev):
            from qt.core import QApplication
            t = _tokens()
            dark = QApplication.instance().palette_manager.is_dark_theme
            p = QPainter(self)
            r = self.rect()
            p.fillRect(r, QColor(t['view_bg']))
            if min(r.width(), r.height()) <= self.COLLAPSED_SIZE:
                # A collapsed handle stands in for a hidden pane (the 2 px stub above the book
                # area when Quickview is hidden): no divider, or it reads as a line under the
                # header bar.
                p.end()
                return
            line = _hairline(dark)
            parent = self.parentWidget()
            if self.orientation is Qt.Orientation.Vertical:
                # Vertical handle between side-by-side panes: border on the sidebar's side.
                mid = self.mapTo(parent, r.center()).x() if parent is not None else 0
                left_half = parent is None or mid < parent.width() / 2
                x = r.left() if left_half else r.right()
                p.fillRect(x, r.top(), 1, r.height(), line)
            else:
                p.fillRect(r.left(), r.center().y(), r.width(), 1, line)
            p.end()

        SplitterHandle.paintEvent = paint
        SplitterHandle._adwaita_patched = True

    from calibre.gui2.book_details import BookDetails
    from qt.core import QWidget
    for w in gui.findChildren(QWidget):
        if isinstance(w, BookDetails):
            w.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            w.setContentsMargins(INSET, INSET, INSET, INSET)
            w.do_layout(w.rect())
    for h in gui.findChildren(SplitterHandle):
        h.update()
    container = getattr(gui, 'layout_container', None)
    if container is not None and hasattr(container, 'relayout'):
        container.relayout()
