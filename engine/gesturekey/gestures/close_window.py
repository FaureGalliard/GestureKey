from __future__ import annotations
from typing import Optional

from gesturekey.actions.types import Hotkey
from gesturekey.config import CloseWindowConfig
from gesturekey.core.cooldown import CooldownManager
from gesturekey.core.geometry import hand_center
from gesturekey.core.types import FrameData, GestureEvent, HandState, Point
from gesturekey.gestures.base import Gesture, Output


class CloseWindowGesture(Gesture):
    """FIST with a sharp downward jerk → Alt+F4."""

    NAME = "CLOSE_WINDOW"

    def __init__(self, cooldown: CooldownManager, cfg: CloseWindowConfig) -> None:
        self._cooldown = cooldown
        self.reset()

    def update(self, frame: FrameData, out: Output) -> None:
        hand = frame.main_hand
        if frame.state != HandState.FIST or hand is None:
            self.reset()
            return

        center = hand_center(hand.norm)
        if self._prev_center is not None:
            dy = center[1] - self._prev_center[1]
            if dy > 0.12 and self._cooldown.ok(self.NAME, frame.timestamp):
                out.emit(GestureEvent.CLOSE_WINDOW, Hotkey(("alt", "f4")))
        self._prev_center = center

    def reset(self) -> None:
        self._prev_center: Optional[Point] = None
