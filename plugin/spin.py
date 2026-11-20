"""Geometry of libadwaita's spinner (AdwSpinner), without Qt so it can be unit-tested.

Ported from libadwaita's src/adw-spinner-paintable.c (LGPL-2.1-or-later, (C) 2024 Alice
Mikhaylenko). The arc's head and tail move continuously: the progress runs linearly in time and
each end eases in and out (sine) on its own, so there is no pause and no fast whip, unlike
calibre's own spinner (which holds the arc for half of each cycle, then swings it round 315 degrees
in a quarter of the cycle, in whole-degree steps).

Angles here are in degrees, clockwise from 3 o'clock (GSK's circle path), as floats.
"""

import math

SPIN_DURATION_MS = 1200
MAX_RADIUS = 32
START_ANGLE = math.pi * 0.35
CIRCLE_OPACITY = 0.15
MIN_ARC_LENGTH = math.pi * 0.015
MAX_ARC_LENGTH = math.pi * 0.9
IDLE_DISTANCE = math.pi * 0.9
OVERLAP_DISTANCE = math.pi * 0.7
EXTEND_DISTANCE = math.pi * 1.1
CONTRACT_DISTANCE = math.pi * 1.35
# Full turns until the pattern repeats; one loop of the animation lasts N_CYCLES turns.
N_CYCLES = 53
LOOP_END = N_CYCLES * 2 * math.pi
LOOP_MS = SPIN_DURATION_MS * N_CYCLES
# Progress shown when not animating (libadwaita's value without an animation).
STILL = EXTEND_DISTANCE - OVERLAP_DISTANCE / 2

_CYCLE = IDLE_DISTANCE + EXTEND_DISTANCE + CONTRACT_DISTANCE - OVERLAP_DISTANCE


def _lerp(a: float, b: float, t: float) -> float:
    return a * (1 - t) + b * t


def _ease_in_out_sine(t: float) -> float:
    return -(math.cos(math.pi * t) - 1) / 2


def _arc_start(angle: float) -> float:
    angle = math.fmod(angle, _CYCLE)
    t = 1.0 if angle > EXTEND_DISTANCE else _ease_in_out_sine(angle / EXTEND_DISTANCE)
    return _lerp(MIN_ARC_LENGTH, MAX_ARC_LENGTH, t) - angle * MAX_ARC_LENGTH / _CYCLE


def _arc_end(angle: float) -> float:
    angle = math.fmod(angle, _CYCLE)
    if angle < EXTEND_DISTANCE - OVERLAP_DISTANCE:
        t = 0.0
    elif angle > _CYCLE - IDLE_DISTANCE:
        t = 1.0
    else:
        t = _ease_in_out_sine((angle - EXTEND_DISTANCE + OVERLAP_DISTANCE) / CONTRACT_DISTANCE)
    return _lerp(0, MAX_ARC_LENGTH - MIN_ARC_LENGTH, t) - angle * MAX_ARC_LENGTH / _CYCLE


def arc(progress: float) -> tuple[float, float]:
    """(tail, span) in degrees for an animation progress in radians (0 .. LOOP_END).

    The arc runs clockwise from `tail` over `span` degrees, ending at the head."""
    head = progress + _arc_start(progress) + START_ANGLE
    tail = progress + _arc_end(progress) + START_ANGLE
    span = (head - tail) % (2 * math.pi)
    return math.degrees(tail % (2 * math.pi)), math.degrees(span)


def line_width(diameter: float) -> float:
    """Stroke width at libadwaita's default weight: 2 px for a 16 px spinner."""
    return diameter / 8.0


def radius(width: float, height: float) -> float:
    return float(min(math.floor(min(width, height) / 2), MAX_RADIUS))
