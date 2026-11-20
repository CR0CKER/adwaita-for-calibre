import math
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'plugin'))

import spin  # noqa: E402

FRAME = spin.LOOP_END / (spin.LOOP_MS / 1000 * 60)  # progress per frame at 60 fps


def _apart(a, b):
    """Shortest distance between two angles in degrees."""
    d = abs(a - b) % 360
    return min(d, 360 - d)


def _frames(turns):
    p, prev = 0.0, spin.arc(0.0)
    while p < turns * 2 * math.pi:
        p += FRAME
        cur = spin.arc(p)
        yield prev, cur
        prev = cur


class Spinner(unittest.TestCase):
    def test_arc_moves_at_most_ten_degrees_a_frame(self):
        # The smoothness claim: calibre's spinner swings its arc ~20 degrees a frame at its
        # fastest; libadwaita's head and tail never move more than ~9.6.
        worst = 0.0
        for (t0, s0), (t1, s1) in _frames(3):
            worst = max(worst, _apart(t0, t1), _apart(t0 + s0, t1 + s1))
        self.assertLess(worst, 10.0)
        self.assertGreater(worst, 5.0)  # it does move: one turn per 1.2 s is 6 degrees a frame

    def test_span_stays_between_min_and_max_arc(self):
        spans = [cur[1] for _prev, cur in _frames(3)]
        self.assertGreaterEqual(min(spans), math.degrees(spin.MIN_ARC_LENGTH) - 1e-6)
        self.assertLessEqual(max(spans), math.degrees(spin.MAX_ARC_LENGTH) + 1e-6)
        self.assertGreater(max(spans) - min(spans), 90)  # it grows and shrinks

    def test_loop_is_seamless(self):
        t0, s0 = spin.arc(0.0)
        t1, s1 = spin.arc(spin.LOOP_END)
        self.assertAlmostEqual(_apart(t0, t1), 0, places=6)
        self.assertAlmostEqual(s0, s1, places=6)

    def test_one_turn_takes_1200_ms(self):
        self.assertEqual(spin.LOOP_MS / spin.N_CYCLES, 1200)

    def test_line_width_and_radius_follow_libadwaita(self):
        self.assertEqual(spin.line_width(16), 2)
        self.assertEqual(spin.radius(16, 16), 8)
        self.assertEqual(spin.radius(17, 30), 8)
        self.assertEqual(spin.radius(200, 200), spin.MAX_RADIUS)


if __name__ == '__main__':
    unittest.main()
