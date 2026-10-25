from __future__ import annotations
import math
from typing import Sequence

from gesturekey.core.types import Hand, Point

FINGERTIPS = (4, 8, 12, 16, 20)


def dist(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def hand_center(landmarks: Sequence[Point]) -> Point:
    n = len(landmarks)
    return (sum(p[0] for p in landmarks) / n, sum(p[1] for p in landmarks) / n)


def angle(a: Point, b: Point, c: Point) -> float:
    ba = (a[0] - b[0], a[1] - b[1])
    bc = (c[0] - b[0], c[1] - b[1])
    mag = math.hypot(*ba) * math.hypot(*bc)
    if mag == 0:
        return 0.0
    cos_val = max(-1.0, min(1.0, (ba[0] * bc[0] + ba[1] * bc[1]) / mag))
    return math.degrees(math.acos(cos_val))


def hand_size_3d(hand: Hand) -> float:
    """Wrist → middle fingertip distance in image space (with depth)."""
    (wx, wy), (mx, my) = hand.img[0], hand.img[12]
    dz = hand.z[12] - hand.z[0]
    return math.sqrt((mx - wx) ** 2 + (my - wy) ** 2 + dz ** 2)


def relative_depth(hand: Hand) -> float:
    """Mean fingertip depth relative to the wrist (negative = pointing at camera)."""
    return sum(hand.z[i] for i in FINGERTIPS) / len(FINGERTIPS) - hand.z[0]
