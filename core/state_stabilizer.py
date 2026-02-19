"""
StateStabilizer — temporal filter that turns noisy per-frame predictions
into stable, confirmed hand states.

Previously this logic lived as module-level variables in detect_states.py.
Now it is a proper class with no global state.
"""
from __future__ import annotations
from collections import deque, Counter
from typing import Optional

from domain.enums import HandState


class StateStabilizer:
    """
    Accumulates raw predictions into a rolling window and returns a stable
    state only when a clear consensus is reached.

    Parameters
    ----------
    window : int
        Number of frames kept in the rolling buffer.
    consensus : int
        Minimum occurrences of the dominant state required to confirm it.
    min_confidence : float
        Predictions below this confidence are replaced with UNKNOWN.
    """

    def __init__(
        self,
        window: int = 4,
        consensus: int = 2,
        min_confidence: float = 0.60,
    ) -> None:
        self._window = window
        self._consensus = consensus
        self._min_confidence = min_confidence
        self._buffer: deque[HandState] = deque(maxlen=window)
        self._current: Optional[HandState] = None

    # ------------------------------------------------------------------
    def update(self, raw_state: HandState, confidence: float) -> Optional[HandState]:
        """
        Feed a new prediction.

        Returns the stable (consensus) state if consensus is reached,
        or None if the buffer hasn't settled yet.
        The *current stable state* is also cached in self.current.
        """
        # Low-confidence predictions are treated as unknown
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

        return None  # no consensus yet

    @property
    def current(self) -> Optional[HandState]:
        """The last confirmed stable state, or None if not yet settled."""
        return self._current

    def reset(self) -> None:
        self._buffer.clear()
        self._current = None