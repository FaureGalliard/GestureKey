from __future__ import annotations
from collections import deque
from typing import Deque, Optional, Tuple

from gesturekey.actions.types import Hotkey
from gesturekey.config import CloseWindowConfig
from gesturekey.core.cooldown import CooldownManager
from gesturekey.core.geometry import palm_center, palm_length
from gesturekey.core.types import FrameData, GestureEvent, HandState
from gesturekey.gestures.base import Gesture, Output

STILL_SPEED = 0.6   # image units/s: the fist must be held fairly still to arm


class CloseWindowGesture(Gesture):
    """
    ✊ fist held still (`arm_time`), then a sharp drop of `distance` palm
    lengths within `within` seconds → Alt+F4.

    Destructive, so it asks for more: a deliberate hold first, then a real
    jerk measured in image space (v2 measured the hand centre relative to its
    own wrist, so it reacted to bending the wrist, not to moving the fist).
    Opening the palm first and then closing it is a grab, not this.
    """

    NAME = "CLOSE_WINDOW"

    def __init__(self, cooldown: CooldownManager, cfg: CloseWindowConfig) -> None:
        self._cooldown = cooldown
        self._cfg = cfg
        self.reset()

    def update(self, frame: FrameData, out: Output) -> None:
        hand, now = frame.main_hand, frame.timestamp
        if frame.state != HandState.FIST or hand is None:
            self.reset()
            return

        y = palm_center(hand)[1]
        self._trail.append((now, y))
        if self._still_since is None:
            self._still_since = now

        if not self._armed:
            speed = self._speed()
            if speed is not None and speed > STILL_SPEED:
                self._still_since = now
            elif now - self._still_since >= self._cfg.arm_time:
                self._armed = True
                self._armed_y = y
            return

        drop = (y - min(v for t, v in self._trail if now - t <= self._cfg.within)) / palm_length(hand)
        if drop >= self._cfg.distance and self._cooldown.ok(self.NAME, now):
            out.emit(GestureEvent.CLOSE_WINDOW, Hotkey(("alt", "f4")))
            self.reset()

    def _speed(self) -> Optional[float]:
        if len(self._trail) < 2:
            return None
        (t0, y0), (t1, y1) = self._trail[-2], self._trail[-1]
        return abs(y1 - y0) / (t1 - t0) if t1 > t0 else None

    def reset(self) -> None:
        self._trail: Deque[Tuple[float, float]] = deque(maxlen=60)
        self._still_since: Optional[float] = None
        self._armed = False
        self._armed_y = 0.0
