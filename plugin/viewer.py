"""Carry the theme into calibre's e-book viewer, which runs as its own program and loads no
interface plugins.

Two shared settings reach it:

* calibre's custom colour palettes (`gprefs['dark_palettes']` / `light_palettes`, the ones
  Preferences -> Look & feel -> Adjust colors edits). Every calibre GUI program reads them, the
  viewer included. The plugin stores its own palettes there under the key `adwaita` and selects
  them; a palette the user made (`__current__`) is left alone. The main window ignores these
  while the plugin runs (it installs its palettes directly), so this only affects the viewer.
* the viewer's built-in "System" reading colour scheme, which takes the page background, text
  and link colours from that palette (`viewer/web_view.py: system_colors`). Selected once; the
  scrollbar inside the page derives its colours from the scheme.

Rewritten at every start and on accent changes, so the viewer follows GNOME's accent too.
"""

from calibre_plugins.adwaita_for_calibre.main import debug

KEY = 'adwaita'


def viewer_running():
    """Whether an e-book viewer is open, via its single-instance lock (calibre/gui2/viewer/main.py:
    `singleinstance_name = 'calibre_viewer'`). An open viewer writes its whole session back on exit,
    which would undo a change made to its settings meanwhile."""
    from calibre.utils.lock import SingleInstance
    with SingleInstance('calibre_viewer') as free:
        return not free


def palette_dict(theme, dark):
    from calibre.gui2.palette import is_foreground_color, palette_colors
    from qt.core import QPalette

    pal = theme.palette(dark)
    ans = {}
    for role_name in palette_colors():
        role = getattr(QPalette.ColorRole, role_name)
        ans[role_name] = pal.color(QPalette.ColorGroup.Active, role).name()
        if is_foreground_color(role_name):
            ans[role_name + '-disabled'] = pal.color(QPalette.ColorGroup.Disabled, role).name()
    return ans


def sync(theme, prefs):
    from calibre.gui2 import gprefs

    for dark, mode in ((True, 'dark'), (False, 'light')):
        palettes = dict(gprefs[f'{mode}_palettes'] or {})
        data = palette_dict(theme, dark)
        if palettes.get(KEY) != data:
            palettes[KEY] = data
            gprefs[f'{mode}_palettes'] = palettes
        if gprefs[f'{mode}_palette_name'] in ('', None):
            gprefs[f'{mode}_palette_name'] = KEY

    if not prefs['viewer_scheme_set'] and not viewer_running():
        # Deferred to the next calibre start while a viewer is open (audit L4).
        from calibre.gui2.viewer.config import vprefs
        sd = dict(vprefs['session_data'] or {})
        prefs['viewer_previous_scheme'] = sd.get('current_color_scheme', '')
        sd['current_color_scheme'] = 'system'
        vprefs['session_data'] = sd
        prefs['viewer_scheme_set'] = True
    debug('viewer palettes synced')


def unsync(prefs):
    """Undo: stop using the Adwaita palettes (and remove them) and restore the viewer's previous
    colour scheme. Returns False when the viewer is open, so its scheme could not be restored."""
    from calibre.gui2 import gprefs
    from calibre.gui2.viewer.config import vprefs

    for mode in ('dark', 'light'):
        if gprefs[f'{mode}_palette_name'] == KEY:
            gprefs[f'{mode}_palette_name'] = ''
        palettes = dict(gprefs[f'{mode}_palettes'] or {})
        if KEY in palettes:
            del palettes[KEY]
            gprefs[f'{mode}_palettes'] = palettes
    if prefs['viewer_scheme_set']:
        if viewer_running():
            return False
        sd = dict(vprefs['session_data'] or {})
        if sd.get('current_color_scheme') == 'system' and prefs['viewer_previous_scheme']:
            sd['current_color_scheme'] = prefs['viewer_previous_scheme']
            vprefs['session_data'] = sd
        prefs['viewer_scheme_set'] = False
    return True
