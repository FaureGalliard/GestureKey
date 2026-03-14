from __future__ import annotations
from collections import deque, Counter
from typing import Optional

from domain.enums import HandState


class StateStabilizer:
    def __init__(
        self,
        window: int = 4,
        consensus: int = 2,
        min_confidence: float = 0.60,
    ) -> None:
        self._window          = window
        self._consensus       = consensus
        self._min_confidence  = min_confidence
        self._buffer: deque[HandState] = deque(maxlen=window)
        self._current: Optional[HandState] = None

    def update(self, raw_state: HandState, confidence: float) -> Optional[HandState]:
        effective = raw_state if confidence >= self._min_confidence else HandState.UNKNOWN
        self._buffer.append(effective)

        if len(self._buffer) < self._window:
            return None

        most_common, count = Counter(self._buffer).most_common(1)[0]
        if count >= self._consensus:
            stable = HandState(most_common)
            if stable != self._current:
                self._current = stable
            return stable

        return None

    @property
    def current(self) -> Optional[HandState]:
        return self._current

    def reset(self) -> None:
        self._buffer.clear()
        self._current = None