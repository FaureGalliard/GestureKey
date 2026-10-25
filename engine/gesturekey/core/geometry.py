from __future__ import annotations
import math
from typing import Sequence

from gesturekey.core.types import Hand, Point

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


def palm_length(hand: Hand) -> float:
    """Wrist → middle MCP in image units: the yardstick that makes gestures distance-invariant."""
    return dist(hand.img[0], hand.img[9]) or 1e-3


def palm_center(hand: Hand) -> Point:
    idx = (0, 5, 9, 13, 17)
    return (sum(hand.img[i][0] for i in idx) / 5, sum(hand.img[i][1] for i in idx) / 5)
