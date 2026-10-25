from __future__ import annotations
from typing import Dict, Optional

from gesturekey.config import PowerConfig
from gesturekey.core.geometry import dist
from gesturekey.core.types import FrameData, GestureEvent, HandState, Point
from gesturekey.gestures.base import Gesture, Output


class PowerToggleGesture(Gesture):
    """
    ✋✋ both palms held still for `hold_time` → toggle GestureKey on/off.

    Runs outside the arbiter, even while GestureKey is off, so the same
    gesture turns it back on. Still (not approaching) is what separates it
    from task view. After firing it latches until the palms drop.
    """

    NAME = "POWER"

    def __init__(self, cfg: PowerConfig) -> None:
        self._hold_time = cfg.hold_time
        self._max_drift = cfg.max_drift
        self._latched = False
        self.reset()

    @property
    def progress(self) -> Optional[float]:
        return self._progress

    def update(self, frame: FrameData, out: Output, enabled: bool = True) -> None:  # type: ignore[override]
        both = frame.has_both_hands and frame.state == HandState.PALM
        if not both:
            self._latched = False
            self.reset()
            return
        if self._latched:
            return

        wrists: Dict[str, Point] = {side: hand.wrist for side, hand in frame.hands.items()}
        if self._start is None or self._anchor is None:
            self._start, self._anchor = frame.timestamp, wrists
            self._progress = 0.0
            return
        if any(dist(wrists[s], self._anchor[s]) > self._max_drift for s in wrists if s in self._anchor):
            self._start, self._anchor = frame.timestamp, wrists   # moved: start over
            self._progress = 0.0
            return

        self._progress = min(1.0, (frame.timestamp - self._start) / self._hold_time)
        if self._progress >= 1.0:
            out.emit(GestureEvent.POWER_OFF if enabled else GestureEvent.POWER_ON)
            self._latched = True
            self.reset()

    def reset(self) -> None:
        self._start: Optional[float] = None
        self._anchor: Optional[Dict[str, Point]] = None
        self._progress: Optional[float] = None
