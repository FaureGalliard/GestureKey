"""
CloseWindowGesture — swipe fist downward to close the active window.
"""
from __future__ import annotations
from typing import List

from domain.enums import GestureEvent, HandState
from domain.models import FrameData
from gestures.base import Gesture
from core.cooldown_manager import CooldownManager
from utils.geometry import hand_center


class CloseWindowGesture(Gesture):
    NAME = "CLOSE_WINDOW"

    def __init__(self, cooldown: CooldownManager) -> None:
        self._cooldown = cooldown
        self.reset()

    def detect(self, frame_data: FrameData) -> List[GestureEvent]:
        events: List[GestureEvent] = []

        if frame_data.state != HandState.FIST:
            self.reset()
            return events

        main_hand = frame_data.main_hand
        if main_hand is None:
            return events

        center = hand_center(main_hand)

        if self._prev_center is not None:
            dy = center[1] - self._prev_center[1]
            if dy > 0.12 and self._cooldown.ok(self.NAME):
                events.append(GestureEvent.CLOSE_WINDOW)

        self._prev_center = center
        return events

    def reset(self) -> None:
        self._prev_center = None