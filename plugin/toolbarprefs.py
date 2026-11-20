"""calibre's toolbar settings, set to GNOME's once (no calibre or Qt imports: unit-tested).

The header bar is built for 16 px icon-only buttons; calibre's defaults (Medium icons with text,
and text on the search-bar buttons) make it 96 px tall with three toolbar buttons visible. On the
plugin's first run, calibre's own settings (Look & feel -> Toolbar: Small, no text; Searching:
no text on the search-bar buttons) are switched once. What was there before is remembered,
including "not set" (calibre's default), and "Restore calibre's look" puts it back. The user can
change the settings afterwards; the plugin does not switch them again.

`gp` is calibre's gprefs and `prefs` the plugin's JSONConfig. In a JSONConfig, `key in p` is true
only for a value set explicitly (not a default), and `del p[key]` unsets it on disk.
"""

from collections.abc import MutableMapping

KEYS = ('toolbar_icon_size', 'toolbar_text', 'search_tool_bar_shows_text')
GNOME: dict[str, object] = {
    'toolbar_icon_size': 'small', 'toolbar_text': 'never', 'search_tool_bar_shows_text': False}
ADOPTED = 'toolbar_adopted'
PREVIOUS = 'previous_toolbar'


def adopt(gp: MutableMapping[str, object], prefs: MutableMapping[str, object]) -> bool:
    """Switch calibre's toolbar to GNOME's size once; True if this call did it."""
    if prefs.get(ADOPTED):
        return False
    prefs[PREVIOUS] = {k: (gp[k] if k in gp else None) for k in KEYS}
    for k, v in GNOME.items():
        gp[k] = v
    prefs[ADOPTED] = True
    return True


def restore(gp: MutableMapping[str, object], prefs: MutableMapping[str, object]) -> bool:
    """Put back what adopt() replaced; True if there was something to put back. The first run
    stays remembered, so the plugin does not switch the setting again."""
    previous = prefs.get(PREVIOUS)
    if not isinstance(previous, dict) or not previous:
        return False
    for k in KEYS:
        v = previous.get(k)
        if v is None:
            if k in gp:
                del gp[k]
        else:
            gp[k] = v
    prefs[PREVIOUS] = {}
    return True
