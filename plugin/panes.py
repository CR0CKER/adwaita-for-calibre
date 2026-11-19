"""Three-pane layout as libadwaita does it: sidebar | content | sidebar.

* The book details pane on the right becomes a sidebar too (an AdwOverlaySplitView utility pane
  uses the same sidebar style as the navigation sidebar on the left), framing the book area,
  which stays the only view-coloured surface.
* calibre's splitter grips (the dots, CalibreStyle's CE_Splitter) become libadwaita's 1 px
  sidebar border on the sidebar side; the rest of the handle takes the content colour. Panes stay
  resizable: the handle keeps its width, only its painting changes.
* The details pane gets 12 px insets, so the cover sits on it as a card.
"""

from qt.core import QColor, QPainter, Qt

INSET = 12


def _tokens():
    from calibre_plugins.adwaita_for_calibre import adwaita
    from qt.core import QApplication
    return adwaita.tokens(QApplication.instance().palette_manager.is_dark_theme)


def _sidebar_border(dark):
    # --sidebar-border-color: rgb(0 0 6 / 36%) dark, 7 % light
    c = QColor(0, 0, 6)
    c.setAlphaF(0.36 if dark else 0.07)
    return c


def install(gui):
    from calibre.gui2.central import SplitterHandle

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
            line = _sidebar_border(dark)
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
