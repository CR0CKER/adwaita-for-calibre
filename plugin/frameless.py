"""Experimental: make the merged header bar the window's title bar (X11 / XWayland only).

The window becomes frameless and translucent. The plugin paints libadwaita's window itself: a
rounded background (15 px radius) and a soft shadow in a transparent margin. Mutter learns
where the real window edge is from `_GTK_FRAME_EXTENTS`, the same property GTK sets for its
client-side decorations, so maximizing, tiling and snapping ignore the shadow. Dragging the
empty header bar moves the window, double-click maximizes, the margin resizes, and the window
buttons follow GNOME's `button-layout`.

Wayland is left alone: Qt has no API to tell the compositor the window geometry, so a
painted shadow would count as part of the window there.
"""

import ctypes
import ctypes.util

from calibre_plugins.adwaita_for_calibre.main import debug, portal_read
from qt.core import (
    QColor,
    QEvent,
    QIcon,
    QObject,
    QPainter,
    QPainterPath,
    QPointF,
    QRectF,
    QSize,
    Qt,
    QToolButton,
    QWidget,
)

SHADOW = 16          # transparent margin for the shadow and the resize grip, logical px
RADIUS = 15          # libadwaita --window-radius
CORNER = 20          # along an edge, this close to a corner resizes diagonally


class X11:
    """Just enough libX11 to set one window property; any connection may change it."""

    def __init__(self):
        name = ctypes.util.find_library('X11') or 'libX11.so.6'
        self.lib = lib = ctypes.CDLL(name)
        lib.XOpenDisplay.restype = ctypes.c_void_p
        lib.XOpenDisplay.argtypes = [ctypes.c_char_p]
        lib.XInternAtom.restype = ctypes.c_ulong
        lib.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        lib.XChangeProperty.argtypes = [
            ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_int,
            ctypes.c_int, ctypes.c_void_p, ctypes.c_int]
        lib.XFlush.argtypes = [ctypes.c_void_p]
        # Every call needs argtypes: without them ctypes passes the 64-bit Display* as a C int
        # and libX11 segfaults.
        lib.XGetWindowAttributes.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_void_p]
        lib.XGetWindowAttributes.restype = ctypes.c_int
        self.dpy = lib.XOpenDisplay(None)
        if not self.dpy:
            raise OSError('XOpenDisplay failed')
        self.extents = lib.XInternAtom(self.dpy, b'_GTK_FRAME_EXTENTS', 0)
        self.cardinal = lib.XInternAtom(self.dpy, b'CARDINAL', 0)

    def depth(self, wid):
        # XWindowAttributes starts with int x, y, width, height, border_width, depth.
        buf = (ctypes.c_int * 64)()
        self.lib.XGetWindowAttributes(self.dpy, wid, buf)
        return buf[5]

    def set_frame_extents(self, wid, px):
        data = (ctypes.c_long * 4)(px, px, px, px)  # left, right, top, bottom (device px)
        self.lib.XChangeProperty(self.dpy, wid, self.extents, self.cardinal, 32, 0, data, 4)
        self.lib.XFlush(self.dpy)


def tokens_for(gui):
    from calibre_plugins.adwaita_for_calibre import adwaita
    from qt.core import QApplication
    return adwaita.tokens(QApplication.instance().palette_manager.is_dark_theme)


class Frame(QObject):
    def __init__(self, gui, header):
        super().__init__(gui)
        self.gui, self.header = gui, header
        self.x11 = X11()
        self.margin = SHADOW
        self.last_press = (0, None)
        self.corners = None

    # --- geometry -------------------------------------------------------------------------

    def tight(self):
        return bool(self.gui.windowState() & (
            Qt.WindowState.WindowMaximized | Qt.WindowState.WindowFullScreen))

    def update_margins(self):
        m = 0 if self.tight() else SHADOW
        self.margin = m
        self.gui.setContentsMargins(m, m, m, m)
        dpr = self.gui.devicePixelRatioF()
        try:
            self.x11.set_frame_extents(int(self.gui.winId()), round(m * dpr))
        except Exception as e:
            debug('frame extents failed', e)
        self.update_mask()
        self.gui.update()

    def content_rect(self):
        m = self.margin
        return QRectF(self.gui.rect()).adjusted(m, m, -m, -m)

    def update_mask(self):
        """Keep the corner overlay on top and covering the window (see Corners)."""
        c = self.corners
        if c is None:
            return
        c.setGeometry(self.gui.rect())
        c.raise_()
        c.update()

    # --- painting ---------------------------------------------------------------------------

    def corner_path(self):
        """The four areas just outside the rounded content rectangle's corners."""
        rect, r = self.content_rect(), RADIUS
        squares = QPainterPath()
        for x, y in ((rect.left(), rect.top()), (rect.right() - r, rect.top()),
                     (rect.left(), rect.bottom() - r), (rect.right() - r, rect.bottom() - r)):
            squares.addRect(QRectF(x, y, r, r))
        rounded = QPainterPath()
        rounded.addRoundedRect(rect, r, r)
        return squares.subtracted(rounded)

    def draw_shadow(self, p):
        rect = self.content_rect()
        r = 0 if self.tight() else RADIUS
        # A cheap soft shadow: stacked translucent rounded rects.
        for i in range(self.margin, 0, -2):
            c = QColor(0, 0, 6)
            c.setAlphaF(0.035 * (1 - i / self.margin) + 0.004)
            path = QPainterPath()
            path.addRoundedRect(rect.adjusted(-i, -i + 2, i, i + 2), r + i, r + i)
            p.fillPath(path, c)

    def paint(self):
        t = tokens_for(self.gui)
        p = QPainter(self.gui)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = 0 if self.tight() else RADIUS
        if self.margin:
            self.draw_shadow(p)
        path = QPainterPath()
        path.addRoundedRect(self.content_rect(), r, r)
        p.fillPath(path, QColor(t['window_bg']))
        p.end()

    def paint_corners(self, widget):
        """Children (header bar, lists, status bar) paint square corners over the rounded
        background. Erase the area outside the rounding, anti-aliased, and put the shadow back.
        Masks would also work but cannot be anti-aliased."""
        if self.tight() or not self.margin:
            return
        corners = self.corner_path()
        p = QPainter(widget)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        p.fillPath(corners, QColor(0, 0, 0))
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        p.setClipPath(corners)
        self.draw_shadow(p)
        p.end()

    # --- input ------------------------------------------------------------------------------

    def edges_at(self, pos):
        """The window edges under `pos` (a QPointF in gui coordinates), as an int bitmask.
        Only the transparent margin outside the window resizes, as in GTK: inside, the header
        bar must keep its normal cursor."""
        if self.tight():
            return 0
        rect = self.content_rect()
        if rect.contains(pos):
            return 0
        x, y = pos.x(), pos.y()
        left, right = x < rect.left() + CORNER, x > rect.right() - CORNER
        top, bottom = y < rect.top() + CORNER, y > rect.bottom() - CORNER
        e = 0
        if x < rect.left() or (left and (y < rect.top() or y > rect.bottom())):
            e |= Qt.Edge.LeftEdge.value
        if x > rect.right() or (right and (y < rect.top() or y > rect.bottom())):
            e |= Qt.Edge.RightEdge.value
        if y < rect.top() or (top and (x < rect.left() or x > rect.right())):
            e |= Qt.Edge.TopEdge.value
        if y > rect.bottom() or (bottom and (x < rect.left() or x > rect.right())):
            e |= Qt.Edge.BottomEdge.value
        return e

    L, R, T, B = (Qt.Edge.LeftEdge.value, Qt.Edge.RightEdge.value,
                  Qt.Edge.TopEdge.value, Qt.Edge.BottomEdge.value)
    CURSORS = {
        L: Qt.CursorShape.SizeHorCursor, R: Qt.CursorShape.SizeHorCursor,
        T: Qt.CursorShape.SizeVerCursor, B: Qt.CursorShape.SizeVerCursor,
        L | T: Qt.CursorShape.SizeFDiagCursor, R | B: Qt.CursorShape.SizeFDiagCursor,
        R | T: Qt.CursorShape.SizeBDiagCursor, L | B: Qt.CursorShape.SizeBDiagCursor,
    }

    def eventFilter(self, obj, ev):
        try:
            return self.filter(obj, ev)
        except RuntimeError:
            # During shutdown the main window is deleted while its children still get events.
            return False

    def filter(self, obj, ev):
        t = ev.type()
        if t in (QEvent.Type.Show, QEvent.Type.Hide) and obj is not self.gui and obj is self.gui.statusBar():
            # The status bar can be toggled at runtime (Layout, Hide Statusbar plugin); which
            # widget carries the rounded bottom corners changes with it.
            from qt.core import QTimer
            QTimer.singleShot(0, self.update_mask)
            return False
        if obj is self.gui:
            if t == QEvent.Type.Paint:
                self.paint()
            elif t in (QEvent.Type.WindowStateChange, QEvent.Type.Show):
                self.update_margins()
            elif t == QEvent.Type.Resize:
                self.update_mask()
            elif t == QEvent.Type.Leave:
                self.gui.unsetCursor()
            elif t == QEvent.Type.MouseMove and not ev.buttons():
                c = self.CURSORS.get(self.edges_at(QPointF(ev.position())))
                if c is None:
                    self.gui.unsetCursor()
                else:
                    self.gui.setCursor(c)
            elif t == QEvent.Type.MouseButtonPress and ev.button() == Qt.MouseButton.LeftButton:
                e = self.edges_at(QPointF(ev.position()))
                if e:
                    self.gui.windowHandle().startSystemResize(Qt.Edge(e))
                    return True
            return False
        # Entering the window from the resize margin: drop the resize cursor, which children
        # would otherwise inherit from the main window.
        if t == QEvent.Type.Enter:
            self.gui.unsetCursor()
            return False
        if obj is not self.header and obj not in self.gui.bars_manager.main_bars:
            return False  # the window body: cursor reset only, never drag
        # Header bar and its toolbars: drag to move, double-click to maximize. The window
        # manager takes the pointer grab on the first press, so Qt never delivers a
        # MouseButtonDblClick; detect the second press by time and distance instead.
        if t == QEvent.Type.MouseButtonPress and ev.button() == Qt.MouseButton.LeftButton:
            if obj.childAt(ev.position().toPoint()) is not None:
                return False
            from qt.core import QApplication
            now = ev.timestamp()
            gpos = ev.globalPosition()
            last_t, last_pos = self.last_press
            d = QApplication.styleHints().startDragDistance()
            if (last_pos is not None and now - last_t <= QApplication.styleHints().mouseDoubleClickInterval()
                    and abs(gpos.x() - last_pos.x()) <= d and abs(gpos.y() - last_pos.y()) <= d):
                self.last_press = (0, None)
                self.toggle_maximized()
            else:
                self.last_press = (now, gpos)
                self.gui.windowHandle().startSystemMove()
            return True
        return False

    def toggle_maximized(self):
        if self.gui.isMaximized():
            self.gui.showNormal()
        else:
            self.gui.showMaximized()


class Corners(QWidget):
    """A click-through layer over the whole window that rounds its corners (Frame.paint_corners)."""

    def __init__(self, gui, frame):
        super().__init__(gui)
        self.frame = frame
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setGeometry(gui.rect())

    def paintEvent(self, ev):
        try:
            self.frame.paint_corners(self)
        except RuntimeError:
            pass


def window_buttons(gui, header_layout, frame, image_dir):
    """Buttons per org.gnome.desktop.wm.preferences button-layout (e.g. 'appmenu:close')."""
    layout = portal_read('org.gnome.desktop.wm.preferences', 'button-layout') or 'appmenu:close'
    right = layout.split(':', 1)[1] if ':' in layout else layout
    names = [n.strip() for n in right.split(',') if n.strip()]
    spec = {
        'minimize': ('window-minimize', gui.showMinimized),
        'maximize': ('window-maximize', frame.toggle_maximized),
        'close': ('window-close', gui.close),
    }
    for n in names:
        if n not in spec:
            continue
        icon_name, fn = spec[n]
        b = QToolButton(header_layout.parentWidget())
        b.setObjectName('adwaita_window_button')
        b.setIcon(QIcon(f'{image_dir}/{icon_name}.svg'))
        b.setIconSize(QSize(16, 16))
        b.setAutoRaise(True)
        b.setToolTip(n.capitalize())
        b.clicked.connect(fn)
        header_layout.addWidget(b)


def prepare(gui):
    """Before the window is first shown (plugin genesis). X11 fixes a window's visual, and so
    whether it can be translucent, when the native window is created; flipping the attribute
    on an existing window leaves an opaque visual and the shadow margin renders black."""
    from qt.core import QApplication
    platform = QApplication.instance().platformName()
    if platform != 'xcb':
        debug('integrated title bar needs X11/XWayland; skipped on', platform)
        return None
    if gui.testAttribute(Qt.WidgetAttribute.WA_WState_Created):
        debug('main window already created; integrated title bar would render opaque, skipped')
        return None
    gui.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    gui.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
    gui.setMouseTracking(True)
    frame = Frame(gui, None)
    gui._adwaita_frame = frame
    gui.installEventFilter(frame)
    gui.setContentsMargins(SHADOW, SHADOW, SHADOW, SHADOW)
    frame.corners = Corners(gui, frame)
    return frame


def install(gui, image_dir):
    """After the window is built (initialization_complete): window buttons and drag areas."""
    frame = getattr(gui, '_adwaita_frame', None)
    header = getattr(gui, 'search_bar', None)
    if frame is None or header is None or not getattr(header, '_adwaita_merged', False):
        return False
    frame.header = header
    window_buttons(gui, header._layout, frame, image_dir)
    header.installEventFilter(frame)
    for bar in gui.bars_manager.main_bars:
        bar.installEventFilter(frame)
    for w in (gui.centralWidget(), gui.statusBar()):
        if w is not None:
            w.installEventFilter(frame)
    if gui.statusBar() is not None:
        # The shadow margin resizes the window; the grip would paint into the rounded corner.
        gui.statusBar().setSizeGripEnabled(False)
    frame.update_margins()
    try:
        debug('window depth', frame.x11.depth(int(gui.winId())))
    except Exception as e:
        debug('depth check failed', e)
    debug('integrated title bar on')
    return True
