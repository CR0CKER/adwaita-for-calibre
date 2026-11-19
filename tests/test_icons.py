import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'icons'))

from mapping import KEEP, MAPPING  # noqa: E402

SRC = '/usr/share/icons/Adwaita/symbolic'


@unittest.skipUnless(os.path.isdir(SRC), 'adwaita-icon-theme not installed')
class Mapping(unittest.TestCase):
    def path(self, icon):
        if icon.startswith('local:'):
            return os.path.join(ROOT, 'icons', 'extra', icon[6:] + '-symbolic.svg')
        if icon.startswith('hicolor:'):
            return os.path.join('/usr/share/icons/hicolor/symbolic', icon[8:] + '-symbolic.svg')
        return os.path.join(SRC, icon + '-symbolic.svg')

    def test_every_target_exists(self):
        missing = sorted({v for v in MAPPING.values() if not os.path.exists(self.path(v))})
        self.assertEqual(missing, [])

    def test_targets_render_as_plain_shapes(self):
        # Filters, masks and embedded bitmaps render as a solid square once recoloured
        # (preferences-desktop-appearance did).
        bad = []
        for v in set(MAPPING.values()):
            with open(self.path(v), encoding='utf-8') as f:
                if re.search(r'<(filter|mask|image)\b', f.read()):
                    bad.append(v)
        self.assertEqual(sorted(bad), [])

    def test_names_look_like_calibre_images(self):
        for name in MAPPING:
            self.assertTrue(name.endswith('.png'), name)
            self.assertNotIn('-for-', name)
            self.assertLessEqual(name.count('/'), 1, name)
        self.assertFalse(set(MAPPING) & KEEP)

    def test_format_icons_stay_calibre(self):
        # Book-format pictures carry meaning in colour; only UI-action icons from the
        # subfolders are mapped.
        for fmt in ('epub', 'pdf', 'mobi', 'azw3', 'txt', 'docx', 'unknown'):
            self.assertNotIn(f'mimetypes/{fmt}.png', MAPPING)


if __name__ == '__main__':
    unittest.main()
