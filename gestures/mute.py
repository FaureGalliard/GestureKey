"""
MuteToggleGesture — PALM → FIST → PALM quickly to toggle mute.
"""
from __future__ import annotations
from typing import List

from domain.enums import GestureEvent, HandState
from domain.models import FrameData
from gestures.base import Gesture
from core.cooldown_manager import CooldownManager


class MuteToggleGesture(Gesture):
    NAME = "MUTE_TOGGLE"

    def __init__(self, cooldown: CooldownManager, mute_max_time: float = 1.0) -> None:
        self._cooldown     = cooldown
        self._max_time     = mute_max_time
        self._history: list = []  # list of (HandState, float)

    def detect(self, frame_data: FrameData) -> List[GestureEvent]:
        """
        Looks at the frame_data state and maintains its own compact state history
        (does not depend on the engine's deque directly).
        """
        events: List[GestureEvent] = []
        self._history.append((frame_data.state, frame_data.timestamp))

        # Trim history to last 3 entries
        if len(self._history) > 3:
            self._history = self._history[-3:]

        if len(self._history) == 3:
            (s1, t1), (s2, _), (s3, t3) = self._history
            if (s1 == HandState.PALM
                    and s2 == HandState.FIST
                    and s3 == HandState.PALM
                    and (t3 - t1) < self._max_time
                    and self._cooldown.ok(self.NAME)):
                events.append(GestureEvent.MUTE_TOGGLE)
                self._history.clear()

        return events

    def reset(self) -> None:
        self._history.clear()