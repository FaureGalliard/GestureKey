from __future__ import annotations
from typing import List, Tuple

from gesturekey.actions.types import Hotkey
from gesturekey.config import MuteConfig
from gesturekey.core.cooldown import CooldownManager
from gesturekey.core.types import FrameData, GestureEvent, HandState
from gesturekey.gestures.base import Gesture, Output


class MuteToggleGesture(Gesture):
    """PALM → FIST → PALM on three consecutive stable frames, within max_time."""

    NAME = "MUTE_TOGGLE"

    def __init__(self, cooldown: CooldownManager, cfg: MuteConfig) -> None:
        self._cooldown = cooldown
        self._max_time = cfg.max_time
        self._history: List[Tuple[HandState, float]] = []

    def update(self, frame: FrameData, out: Output) -> None:
        self._history.append((frame.state, frame.timestamp))
        if len(self._history) > 3:
            self._history = self._history[-3:]

        if len(self._history) == 3:
            (s1, t1), (s2, _), (s3, t3) = self._history
            if (s1 == HandState.PALM and s2 == HandState.FIST and s3 == HandState.PALM
                    and (t3 - t1) < self._max_time
                    and self._cooldown.ok(self.NAME, frame.timestamp)):
                out.emit(GestureEvent.MUTE_TOGGLE, Hotkey(("volume_mute",)))
                self._history.clear()

    def reset(self) -> None:
        self._history.clear()
