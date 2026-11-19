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
    return (0.60, 0.45) if dark else (0.20, 0.15)


class Shade(QWidget):
    def __init__(self, parent, edge):
        super().__init__(parent)
        self.edge = edge  # 'top' or 'bottom'
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.hide()

    def paintEvent(self, ev):
        line_a, a = _alphas()
        p = QPainter(self)
        w, h = self.width(), self.height()
        line = QColor(0, 0, 6)
        line.setAlphaF(line_a)
        g = QLinearGradient(0, 0, 0, h) if self.edge == 'top' else QLinearGradient(0, h, 0, 0)
        c0, c1 = QColor(0, 0, 6), QColor(0, 0, 6)
        c0.setAlphaF(a)
        c1.setAlphaF(0)
        g.setColorAt(0, c0)
        g.setColorAt(1, c1)
        p.fillRect(0, 0, w, h, g)
        p.fillRect(0, 0 if self.edge == 'top' else h - 1, w, 1, line)
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
