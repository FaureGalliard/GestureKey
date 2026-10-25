from __future__ import annotations
from collections import Counter, deque
from typing import Deque, Optional

from gesturekey.config import StabilizerConfig
from gesturekey.core.types import HandState


class StateStabilizer:
    """Majority vote over the last `window` predictions above `min_confidence`."""

    def __init__(self, cfg: StabilizerConfig) -> None:
        self._consensus      = cfg.consensus
        self._min_confidence = cfg.min_confidence
        self._window         = cfg.window
        self._buffer: Deque[HandState] = deque(maxlen=cfg.window)
        self._current: Optional[HandState] = None

    def update(self, raw_state: HandState, confidence: float) -> Optional[HandState]:
        effective = raw_state if confidence >= self._min_confidence else HandState.UNKNOWN
        self._buffer.append(effective)
        if len(self._buffer) < self._window:
            return None
        most_common, count = Counter(self._buffer).most_common(1)[0]
        if count >= self._consensus:
            self._current = HandState(most_common)
            return self._current
        return None

    @property
    def current(self) -> Optional[HandState]:
        return self._current

    def reset(self) -> None:
        self._buffer.clear()
        self._current = None
