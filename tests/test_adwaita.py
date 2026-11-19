import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'plugin'))

import adwaita  # noqa: E402

QSS = open(os.path.join(ROOT, 'plugin', 'adwaita.qss'), encoding='utf-8').read()


class Tokens(unittest.TestCase):
    def test_dark_surfaces_match_libadwaita(self):
        t = adwaita.tokens(True, '#c88800')
        self.assertEqual(t['window_bg'], '#222226')
        self.assertEqual(t['view_bg'], '#1d1d20')
        self.assertEqual(t['headerbar_bg'], '#2e2e32')
        self.assertEqual(t['popover_bg'], '#36363a')
        self.assertEqual(t['fg'], '#ffffff')

    def test_light_foreground_is_80_percent_near_black(self):
        t = adwaita.tokens(False, '#3584e4')
        self.assertEqual(t['window_bg'], '#fafafb')
        # rgb(0 0 6 / 80%) over #fafafb
        self.assertEqual(t['fg'], '#323237')

    def test_standalone_accent(self):
        # libadwaita: dark lifts the accent to OKLab L >= .85, light caps it at .5
        dark = adwaita.standalone_accent('#c88800', True)
        light = adwaita.standalone_accent('#3584e4', False)
        self.assertGreater(adwaita.to_oklab(dark)[0], 0.84)
        self.assertLess(adwaita.to_oklab(light)[0], 0.51)

    def test_oklab_round_trip(self):
        for c in adwaita.ACCENTS.values():
            self.assertEqual(adwaita.from_oklab(adwaita.to_oklab(c)), c)

    def test_mix(self):
        self.assertEqual(adwaita.mix('#ffffff', '#000000', 0.5), '#808080')
        self.assertEqual(adwaita.rgba('#ffffff', 0.15), 'rgba(255, 255, 255, 38)')


class Portal(unittest.TestCase):
    def test_accent(self):
        self.assertEqual(adwaita.accent_from_portal((0.7843137, 0.5333333, 0.0)), '#c88800')

    def test_accent_unset(self):
        # The portal reports an out-of-range triple when no accent is set.
        self.assertIsNone(adwaita.accent_from_portal((-1.0, -1.0, -1.0)))
        self.assertIsNone(adwaita.accent_from_portal(None))
        self.assertIsNone(adwaita.accent_from_portal('x'))

    def test_font(self):
        self.assertEqual(adwaita.parse_font('Adwaita Sans 11'), ('Adwaita Sans', 11.0))
        self.assertEqual(adwaita.parse_font('Cantarell Bold 10.5'), ('Cantarell', 10.5))
        self.assertIsNone(adwaita.parse_font('Adwaita'))
        self.assertIsNone(adwaita.parse_font(None))


class Stylesheet(unittest.TestCase):
    def render(self, dark):
        t = dict(adwaita.tokens(dark, '#c88800'))
        t['img'] = '/x'
        return adwaita.render(QSS, t)

    def test_every_token_resolves(self):
        for dark in (True, False):
            out = self.render(dark)
            self.assertNotRegex(out, r'@[a-z_]+@')

    def test_unknown_token_raises(self):
        with self.assertRaises(KeyError):
            adwaita.render('a { color: @nope@; }', {})

    def test_braces_balance(self):
        out = re.sub(r'/\*.*?\*/', '', self.render(True), flags=re.S)
        self.assertEqual(out.count('{'), out.count('}'))

    def test_images_referenced_exist_in_main(self):
        main = open(os.path.join(ROOT, 'plugin', 'main.py'), encoding='utf-8').read()
        for name in set(re.findall(r'@img@/([\w.-]+)', QSS)):
            self.assertIn(f"'{name}'", main, name)


class Recolor(unittest.TestCase):
    def test_shipped_svgs_have_a_recolourable_fill(self):
        d = os.path.join(ROOT, 'plugin', 'images')
        for f in os.listdir(d):
            svg = open(os.path.join(d, f), encoding='utf-8').read()
            self.assertIn('fill="#abcdef"', adwaita.recolor_svg(svg, '#abcdef'), f)


if __name__ == '__main__':
    unittest.main()
