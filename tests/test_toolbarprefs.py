import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'plugin'))

import toolbarprefs  # noqa: E402


class Prefs(dict):
    """A JSONConfig stand-in: defaults answer reads, but `in` sees only explicit values."""

    def __init__(self, defaults=None, **values):
        super().__init__(**values)
        self.defaults = defaults or {}

    def __getitem__(self, key):
        if dict.__contains__(self, key):
            return dict.__getitem__(self, key)
        return self.defaults[key]

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default


CALIBRE = {'toolbar_icon_size': 'medium', 'toolbar_text': 'always', 'search_tool_bar_shows_text': True}
GNOME = {'toolbar_icon_size': 'small', 'toolbar_text': 'never', 'search_tool_bar_shows_text': False}
UNSET = {'toolbar_icon_size': None, 'toolbar_text': None, 'search_tool_bar_shows_text': None}


class ToolbarPrefs(unittest.TestCase):
    def test_first_run_switches_calibre_defaults_to_small_without_text(self):
        gp, p = Prefs(CALIBRE), Prefs()
        self.assertTrue(toolbarprefs.adopt(gp, p))
        self.assertEqual(dict(gp), GNOME)
        self.assertEqual(p['previous_toolbar'], UNSET)

    def test_only_once_so_a_later_choice_is_kept(self):
        gp, p = Prefs(CALIBRE), Prefs()
        toolbarprefs.adopt(gp, p)
        gp['toolbar_icon_size'] = 'large'  # the user changes it afterwards
        self.assertFalse(toolbarprefs.adopt(gp, p))
        self.assertEqual(gp['toolbar_icon_size'], 'large')

    def test_restore_unsets_what_was_unset(self):
        gp, p = Prefs(CALIBRE), Prefs()
        toolbarprefs.adopt(gp, p)
        self.assertTrue(toolbarprefs.restore(gp, p))
        self.assertEqual(dict(gp), {})
        self.assertEqual(gp['toolbar_icon_size'], 'medium')  # calibre's defaults again
        self.assertIs(gp['search_tool_bar_shows_text'], True)

    def test_restore_puts_back_explicit_values(self):
        mine = {'toolbar_icon_size': 'mid-small', 'toolbar_text': 'auto', 'search_tool_bar_shows_text': False}
        gp, p = Prefs(CALIBRE, **mine), Prefs()
        toolbarprefs.adopt(gp, p)
        toolbarprefs.restore(gp, p)
        self.assertEqual(dict(gp), mine)  # False is a value to put back, not "unset"

    def test_restore_does_not_rearm_the_first_run(self):
        gp, p = Prefs(CALIBRE), Prefs()
        toolbarprefs.adopt(gp, p)
        toolbarprefs.restore(gp, p)
        self.assertFalse(toolbarprefs.restore(gp, p))  # nothing left to put back
        self.assertFalse(toolbarprefs.adopt(gp, p))
        self.assertEqual(gp['toolbar_icon_size'], 'medium')


if __name__ == '__main__':
    unittest.main()
