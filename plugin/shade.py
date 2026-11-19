"""libadwaita's "raised" bars: when the book list/grid/bookshelf is scrolled, a soft shadow
appears under the header bar (and above the status bar while more content lies below), so
the content reads as sliding underneath the bars, as in GNOME Text Editor or Files.

From default.css: toolbarview > .top-bar.raised { box-shadow: 0 1px <shade 50%>,
0 2px 4px <shade 50%> } with --headerbar-shade-color rgb(0 0 6 / 36%) dark, 12% light.
Drawn as click-through overlays on calibre's view stack.
"""

from qt.core import QColor, QEvent, QLinearGradient, QObject, QPainter, Qt, QWidget

# libadwaita's exact undershoot (1 px line + 4 px gradient at ~19 %) is all but invisible over
# calibre's dark book list, so the same shape is drawn deeper and stronger.
HEIGHT = 12


def _alphas():
    """(edge line, gradient start) opacities."""
    from qt.core import QApplication
    dark = QApplication.instance().palette_manager.is_dark_theme
    # Light: close to libadwaita (headerbar shade 12 % at 50 %); a dark edge line on white is harsh.
    return (0.60, 0.30) if dark else (0.08, 0.07)


class Shade(QWidget):
    def __init__(self, parent, edge):
        super().__init__(parent)
        self.edge = edge  # 'top' or 'bottom'
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.hide()

    def paintEvent(self, ev):
        _, a = _alphas()
        p = QPainter(self)
        w, h = self.width(), self.height()
        g = QLinearGradient(0, 0, 0, h) if self.edge == 'top' else QLinearGradient(0, h, 0, 0)
        c0, c1 = QColor(0, 0, 6), QColor(0, 0, 6)
        c0.setAlphaF(a)
        c1.setAlphaF(0)
        g.setColorAt(0, c0)
        g.setColorAt(1, c1)
        p.fillRect(0, 0, w, h, g)
        # No 1 px edge line: tried (libadwaita draws one), Nils preferred the shadow alone.
        p.end()


class Controller(QObject):
    def __init__(self, gui, stack, av):
        super().__init__(stack)
        self.gui, self.stack, self.av = gui, stack, av
        self.top = Shade(stack, 'top')
        self.bottom = Shade(stack, 'bottom')
        stack.installEventFilter(self)
        stack.currentChanged.connect(self.update)
        for view in av.views.values():
            sb = view.verticalScrollBar() if hasattr(view, 'verticalScrollBar') else None
            if sb is not None:
                sb.valueChanged.connect(self.update)
                sb.rangeChanged.connect(self.update)
        status = gui.statusBar()
        if status is not None:
            status.installEventFilter(self)
        self.update()

    def eventFilter(self, obj, ev):
        if ev.type() in (QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.Hide):
            self.update()
        return False

    def update(self, *args):
        try:
            view = self.av.current_view
            sb = view.verticalScrollBar() if hasattr(view, 'verticalScrollBar') else None
            w = self.stack.width()
            self.top.setGeometry(0, 0, w, HEIGHT)
            self.bottom.setGeometry(0, self.stack.height() - HEIGHT, w, HEIGHT)
            scrolled = sb is not None and sb.value() > sb.minimum()
            more_below = sb is not None and sb.value() < sb.maximum()
            status = self.gui.statusBar()
            self.top.setVisible(scrolled)
            self.bottom.setVisible(bool(more_below and status is not None and status.isVisible()))
            self.top.raise_()
            self.bottom.raise_()
        except RuntimeError:
            pass  # shutting down


def install(gui):
    av = getattr(gui.library_view, 'alternate_views', None)
    if av is None or av.stack is None:
        return None
    gui._adwaita_shade = c = Controller(gui, av.stack, av)
    return c


# A gap up to this wide between a scroll area's viewport and its pane's edge is padding (the
# tree's own frame, the pane's insets), so the shade runs across it to the pane's edge, as
# libadwaita's undershoot does. A wider gap holds something else (the details cover beside the
# text), which the shade must not darken.
EDGE_SNAP = 32


class ScrollAreaShades(QObject):
    """The same raised-bar shadows for a single scroll area (the tag browser): under the header
    bar once scrolled, above the bottom bar (Configure / Find) while more lies below.

    The shades run edge to edge across ``pane`` (default: the scroll area itself), from its top
    and bottom, so the content's padding does not leave them short at the sides or push them
    away from the bars.
    For a pane, they are children of the pane's parent: BookDetails is a QSplitter, which adopts
    every child widget as a new splitter section."""

    def __init__(self, area, bottom=True, pane=None):
        super().__init__(area)
        self.area = area
        self.pane = pane if pane is not None else area
        self.host = area if pane is None else pane.parentWidget()
        self.top = Shade(self.host, 'top')
        self.bottom = Shade(self.host, 'bottom')
        self.with_bottom = bottom
        sb = area.verticalScrollBar()
        sb.valueChanged.connect(self.update)
        sb.rangeChanged.connect(self.update)
        area.installEventFilter(self)
        if self.pane is not area:
            self.pane.installEventFilter(self)
        self.update()

    def eventFilter(self, obj, ev):
        if ev.type() in (QEvent.Type.Resize, QEvent.Type.Move, QEvent.Type.Show, QEvent.Type.Hide):
            self.update()
        return False

    def update(self, *args):
        from qt.core import QRect
        try:
            area, pane, host = self.area, self.pane, self.host
            vp = area.viewport().geometry()  # in area coordinates
            if host is not area:
                vp = QRect(area.mapTo(host, vp.topLeft()), vp.size())
                pr = QRect(pane.mapTo(host, pane.rect().topLeft()), pane.size())
            else:
                pr = area.rect()
            left = pr.left() if vp.left() - pr.left() <= EDGE_SNAP else vp.left()
            right = pr.right() if pr.right() - vp.right() <= EDGE_SNAP else vp.right()
            # The same snap vertically: the shades start right under the header bar and end
            # right on the bottom bar, not at the viewport's padded top and bottom.
            top = pr.top() if vp.top() - pr.top() <= EDGE_SNAP else vp.top()
            bottom = pr.bottom() if pr.bottom() - vp.bottom() <= EDGE_SNAP else vp.bottom()
            width = right - left + 1
            self.top.setGeometry(left, top, width, HEIGHT)
            self.bottom.setGeometry(left, bottom - HEIGHT + 1, width, HEIGHT)
            sb = area.verticalScrollBar()
            shown = area.isVisible()
            self.top.setVisible(shown and sb.value() > sb.minimum())
            self.bottom.setVisible(shown and self.with_bottom and sb.value() < sb.maximum())
            self.top.raise_()
            self.bottom.raise_()
        except RuntimeError:
            pass


def install_sidebar(gui):
    from qt.core import QTreeView
    for tv in gui.findChildren(QTreeView):
        if type(tv).__name__ == 'TagsView':
            tv._adwaita_shades = ScrollAreaShades(tv)
    # Book details text: scrolled text slides under the cover instead of being cut off at it.
    # No bottom shade: nothing sits below the pane.
    from calibre.gui2.book_details import BookDetails
    from qt.core import QTextBrowser
    for bd in gui.findChildren(BookDetails):
        for tb in bd.findChildren(QTextBrowser):
            tb._adwaita_shades = ScrollAreaShades(tb, bottom=False, pane=bd)
