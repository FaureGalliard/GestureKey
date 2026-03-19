from __future__ import annotations
from typing import List

from enums import GestureEvent, HandState
from models import FrameData
from gestures.base import Gesture
from pipeline.cooldown_manager import CooldownManager


class MuteToggleGesture(Gesture):
    NAME = "MUTE_TOGGLE"

    def __init__(self, cooldown: CooldownManager, mute_max_time: float = 1.0) -> None:
        self._cooldown     = cooldown
        self._max_time     = mute_max_time
        self._history: list = []  # list of (HandState, float)

    def detect(self, frame_data: FrameData) -> List[GestureEvent]:

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