"""Adwaita colours for calibre 9's bookshelf view.

calibre paints the bookshelf as wood: two hard-coded palettes (light oak, dark walnut) with
gradients, grain lines, knots and bevels (`calibre/gui2/library/bookshelf_view.py`, `WoodTheme`
and `ColorTheme`). GNOME has no skeuomorphic surfaces, so the plugin swaps both themes for flat
libadwaita colours: the view background, shelves as plain ledges in the sidebar colour, and
dividers in the border/card colours. The drawing code is untouched; only its colours change.
"""

from calibre_plugins.adwaita_for_calibre import adwaita
from qt.core import QColor

CLEAR = QColor(0, 0, 0, 0)
_theme = None  # main.Theme, for the live accent colour


def _tokens(dark):
    return adwaita.tokens(dark, _theme.accent if _theme is not None else adwaita.DEFAULT_ACCENT)


def _wood(dark, original):
    t = _tokens(dark)
    view = QColor(t['view_bg'])
    shelf = QColor(t['sidebar_bg'])
    line = QColor(adwaita.mix(t['view_fg'], t['view_bg'], 0.15))
    shade = QColor(0, 0, 6, 40 if dark else 18)
    return original._replace(
        background=view,
        wood_top=shelf, wood_mid_light=shelf, wood_mid_dark=shelf, wood_bottom=shelf,
        grain_color=CLEAR, grain_alpha_range=(0, 0), knot_color=CLEAR,
        highlight_color=CLEAR, shadow_color=shade,
        edge_color=line, end_grain_dark=CLEAR, end_grain_light=CLEAR,
        bevel_light=CLEAR, bevel_dark=CLEAR,
        back_panel_base=view, back_panel_dark=view, side_panel_base=view, side_panel_dark=view,
        inner_shadow_color=CLEAR, cavity_color=view,
    )


def _colors(dark, original):
    t = _tokens(dark)
    return original._replace(
        divider_text_color=QColor(t['fg_dim']),
        divider_background_color=QColor(t['sidebar_bg']),
        divider_line_color=QColor(adwaita.mix(t['view_fg'], t['view_bg'], 0.15)),
        # calibre uses LinkVisited / Mid / Highlight here; GNOME marks selection with the accent.
        current_selected_color=QColor(t['accent_bg']),
        current_color=QColor(adwaita.mix(t['view_fg'], t['view_bg'], 0.30)),
        selected_color=QColor(t['accent_bg']),
    )


def install(theme=None):
    global _theme
    _theme = theme
    try:
        from calibre.gui2.library import bookshelf_view as bv
    except ImportError:
        return False  # calibre before 9 has no bookshelf view
    wood, colors = bv.WoodTheme, bv.ColorTheme
    if getattr(wood, '_adwaita_patched', False):
        return True
    orig_wl, orig_wd = wood.light_theme.__func__, wood.dark_theme.__func__
    orig_cl, orig_cd = colors.light_theme.__func__, colors.dark_theme.__func__
    wood.light_theme = classmethod(lambda cls: _wood(False, orig_wl(cls)))
    wood.dark_theme = classmethod(lambda cls: _wood(True, orig_wd(cls)))
    colors.light_theme = classmethod(lambda cls: _colors(False, orig_cl(cls)))
    colors.dark_theme = classmethod(lambda cls: _colors(True, orig_cd(cls)))
    wood._adwaita_patched = True
    return True


def refresh(gui):
    """Drop any wood the view rendered before the patch."""
    view = getattr(gui, 'bookshelf_view', None)
    rc = getattr(view, 'case_renderer', None)
    if rc is not None:
        for attr in ('dark_theme', 'light_theme'):
            if attr in rc.__dict__:
                delattr(rc, attr)
        rc.shelf_cache.clear()
        rc.last_rendered_background_at = (None,)
        rc.last_rendered_shelf_at = (None,)
    if view is not None and hasattr(view, 'palette_changed'):
        view.palette_changed()
