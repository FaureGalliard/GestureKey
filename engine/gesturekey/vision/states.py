from __future__ import annotations
import math
from typing import Dict, List, Optional

import numpy as np

from gesturekey.config import StatesConfig
from gesturekey.core.types import HandState


class StateFilter:
    """
    Sticky HMM over the classifier's per-class probabilities.

        belief_t ∝ P(obs | s) · Σ_s' P(s | s') · belief_{t-1}(s')

    The transition prior says "hands keep their pose": the chance of a change
    grows with the time since the last frame (switch_rate per second), so it
    behaves the same at 15, 30 or 60 fps. A single uncertain frame barely moves
    the belief; a few confident frames switch it quickly. The output only
    changes when the new state's belief passes `enter` (hysteresis).
    """

    def __init__(self, classes: List[str], cfg: StatesConfig) -> None:
        self._classes = classes
        self._rate    = cfg.switch_rate
        self._enter   = cfg.enter
        self._floor   = cfg.floor
        self.reset()

    def reset(self) -> None:
        self._belief: Optional[np.ndarray] = None
        self._t: Optional[float] = None
        self._current = HandState.NO_HANDS
        self._confidence = 1.0

    @property
    def current(self) -> HandState:
        return self._current

    @property
    def confidence(self) -> float:
        return self._confidence

    def update(self, proba: Optional[Dict[str, float]], t: float) -> HandState:
        """`proba` is None when no hand is visible."""
        if proba is None:
            self.reset()
            self._t = t
            return self._current

        k = len(self._classes)
        obs = np.array([proba.get(c, 0.0) for c in self._classes]) + self._floor
        obs /= obs.sum()

        if self._belief is None:
            belief = obs
        else:
            dt = max(1e-3, t - (self._t or t))
            stay = math.exp(-self._rate * dt)
            prior = stay * self._belief + (1 - stay) * (1 - self._belief) / (k - 1)
            belief = prior * obs
            belief /= belief.sum()
        self._belief, self._t = belief, t

        best = int(np.argmax(belief))
        state = _to_state(self._classes[best])
        if state != self._current and (belief[best] >= self._enter or self._current == HandState.NO_HANDS):
            self._current = state
        idx = self._classes.index(self._current.value) if self._current.value in self._classes else best
        self._confidence = float(belief[idx])
        return self._current


def _to_state(name: str) -> HandState:
    try:
        return HandState(name)
    except ValueError:
        return HandState.UNKNOWN
