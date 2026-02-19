"""
Pure geometric utility functions.
No imports from the rest of the project — safe to use anywhere.
"""
from __future__ import annotations
import math
from typing import Sequence, Tuple

Point2D = Tuple[float, float]


def dist(a: Point2D, b: Point2D) -> float:
    """Euclidean distance between two 2D points."""
    return math.hypot(a[0] - b[0], a[1] - b[1])


def hand_center(landmarks: Sequence[Point2D]) -> Point2D:
    """Geometric centroid of a hand landmark list."""
    xs = [p[0] for p in landmarks]
    ys = [p[1] for p in landmarks]
    n = len(landmarks)
    return (sum(xs) / n, sum(ys) / n)


def angle(a: Point2D, b: Point2D, c: Point2D) -> float:
    """
    Angle ABC in degrees (vertex at B).
    Returns 0.0 if any segment has zero length.
    """
    ba = (a[0] - b[0], a[1] - b[1])
    bc = (c[0] - b[0], c[1] - b[1])
    dot = ba[0] * bc[0] + ba[1] * bc[1]
    mag_ba = math.hypot(*ba)
    mag_bc = math.hypot(*bc)
    if mag_ba * mag_bc == 0:
        return 0.0
    cos_val = max(-1.0, min(1.0, dot / (mag_ba * mag_bc)))
    return math.degrees(math.acos(cos_val))