"""
ScreenshotGesture — push palm toward camera to take a screenshot.
"""
from __future__ import annotations
from typing import List

from domain.enums import GestureEvent, HandState
from domain.models import FrameData
from gestures.base import Gesture
from core.cooldown_manager import CooldownManager
from utils.geometry import dist


class ScreenshotGesture(Gesture):
    NAME = "SCREENSHOT"

    def __init__(self, cooldown: CooldownManager) -> None:
        self._cooldown = cooldown
        self.reset()

    def detect(self, frame_data: FrameData) -> List[GestureEvent]:
        events: List[GestureEvent] = []

        if frame_data.state != HandState.PALM:
            self.reset()
            return events

        main_hand = frame_data.main_hand
        if main_hand is None:
            return events

        wrist      = main_hand[0]
        middle_mcp = main_hand[9]
        scale      = dist(wrist, middle_mcp)

        if self._prev_scale is not None:
            if (self._prev_scale - scale) > 0.08 and self._cooldown.ok(self.NAME):
                events.append(GestureEvent.SCREENSHOT)

        self._prev_scale = scale
        return events

    def reset(self) -> None:
        self._prev_scale = None