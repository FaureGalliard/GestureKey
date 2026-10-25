from __future__ import annotations
import math
from typing import Optional

from gesturekey.core.types import Point


class OneEuroFilter:
    """
    One Euro filter (Casiez et al. 2012): heavy smoothing when the signal is
    still, little lag when it moves fast. Good for landmark jitter.
    """

    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.02, d_cutoff: float = 1.0) -> None:
        self.min_cutoff = min_cutoff
        self.beta       = beta
        self.d_cutoff   = d_cutoff
        self.reset()

    def reset(self) -> None:
        self._x:  Optional[float] = None
        self._dx: float           = 0.0
        self._t:  Optional[float] = None

    @staticmethod
    def _alpha(cutoff: float, dt: float) -> float:
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def __call__(self, x: float, t: float) -> float:
        if self._x is None or self._t is None or t <= self._t:
            self._x, self._t = x, t
            return x
        dt = t - self._t
        dx = (x - self._x) / dt
        a_d = self._alpha(self.d_cutoff, dt)
        self._dx = a_d * dx + (1 - a_d) * self._dx
        cutoff = self.min_cutoff + self.beta * abs(self._dx)
        a = self._alpha(cutoff, dt)
        self._x = a * x + (1 - a) * self._x
        self._t = t
        return self._x


class PointFilter:
    """One Euro filter applied independently to x and y."""

    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.02) -> None:
        self._fx = OneEuroFilter(min_cutoff, beta)
        self._fy = OneEuroFilter(min_cutoff, beta)

    def reset(self) -> None:
        self._fx.reset()
        self._fy.reset()

    def __call__(self, p: Point, t: float) -> Point:
        return (self._fx(p[0], t), self._fy(p[1], t))
