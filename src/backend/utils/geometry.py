
from __future__ import annotations
import math
from typing import Sequence, Tuple

Point2D = Tuple[float, float]


def dist(a: Point2D, b: Point2D) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def hand_center(landmarks: Sequence[Point2D]) -> Point2D:
    xs = [p[0] for p in landmarks]
    ys = [p[1] for p in landmarks]
    n = len(landmarks)
    return (sum(xs) / n, sum(ys) / n)
