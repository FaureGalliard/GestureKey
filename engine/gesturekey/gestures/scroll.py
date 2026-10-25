from __future__ import annotations
from typing import Any, Dict, Optional

from gesturekey.actions.types import Scroll
from gesturekey.config import ContinuousConfig, ScrollConfig
from gesturekey.core.geometry import palm_center, palm_length
from gesturekey.core.types import GestureEvent, Hand, HandState
from gesturekey.gestures.base import Output
from gesturekey.gestures.continuous import ContinuousGesture

MIN_EMIT = 15   # wheel units accumulated before sending (keeps input events reasonable)


class ScrollGesture(ContinuousGesture):
    """
    ✌️ two fingers, joystick-style: the hand's offset from where the gesture
    started sets the scroll *speed*. Back to the start point → stops. A small
    dead zone around it absorbs jitter; the curve is gentle near the centre
    and fast further out. Scrolling is unbounded, so speed (not position) is
    the right mapping — unlike volume.
    """

    NAME = "SCROLL"
    POSE = HandState.TWO_FINGERS

    def __init__(self, cfg: ScrollConfig, cc: ContinuousConfig) -> None:
        self._deadzone = cfg.deadzone
        self._gain     = cfg.gain
        self._max_rate = cfg.max_rate
        super().__init__(cc)

    @property
    def readout(self) -> Optional[Dict[str, Any]]:
        return {"rate": round(self._rate / self._max_rate, 3)} if self._active else None

    def begin(self, hand: Hand, now: float, out: Output) -> None:
        self._anchor_y = palm_center(hand)[1]
        self._accum = 0.0

    def act(self, hand: Hand, now: float, dt: float, out: Output) -> None:
        offset = (palm_center(hand)[1] - self._anchor_y) / palm_length(hand)   # + = hand moved down
        mag = max(0.0, abs(offset) - self._deadzone)
        self._rate = min(self._max_rate, self._gain * mag ** 1.5) * (1 if offset > 0 else -1)
        self._accum += self._rate * dt
        if abs(self._accum) >= MIN_EMIT:
            amount = int(self._accum)
            self._accum -= amount
            out.emit(GestureEvent.SCROLL, Scroll(-amount))   # hand down → page down (wheel negative)

    def reset(self) -> None:
        super().reset()
        self._anchor_y = 0.0
        self._accum = 0.0
        self._rate = 0.0
