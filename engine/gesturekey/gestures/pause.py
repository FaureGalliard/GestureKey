from __future__ import annotations
from typing import Optional

from gesturekey.actions.types import Hotkey
from gesturekey.config import PauseConfig
from gesturekey.core.cooldown import CooldownManager
from gesturekey.core.types import FrameData, GestureEvent, HandState
from gesturekey.gestures.base import Gesture, Output


class PauseResumeGesture(Gesture):
    """
    FOUR_FINGERS held (min_time … max_time) → FIST: toggles media play/pause
    and pauses/resumes every other gesture.
    """

    NAME = "PAUSE_RESUME"

    def __init__(self, cooldown: CooldownManager, cfg: PauseConfig) -> None:
        self._cooldown       = cooldown
        self._min_time       = cfg.min_time
        self._max_time       = cfg.max_time
        self._pause_cooldown = cfg.cooldown
        self.paused          = False
        self._last_toggle    = float("-inf")
        self.reset()

    def update(self, frame: FrameData, out: Output) -> None:
        state, now = frame.state, frame.timestamp

        if state == HandState.FOUR_FINGERS:
            if self._last_state != HandState.FOUR_FINGERS:
                self._start = now
                self._armed = False
            elif self._start is not None and now - self._start >= self._min_time:
                self._armed = True

        elif state == HandState.FIST:
            if self._armed and self._last_state == HandState.FOUR_FINGERS:
                elapsed = now - (self._start or now)
                if elapsed <= self._max_time and self._cooldown_ok(now):
                    self.paused = not self.paused
                    out.emit(
                        GestureEvent.PAUSE_TOGGLE_PAUSED if self.paused else GestureEvent.PAUSE_TOGGLE_RESUMED,
                        Hotkey(("media_play_pause",)),
                    )
                    self.reset()
            elif not self._armed:
                self.reset()
        else:
            self.reset()

        self._last_state = state

    def reset(self) -> None:
        self._start: Optional[float] = None
        self._armed = False
        self._last_state: Optional[HandState] = None

    def _cooldown_ok(self, now: float) -> bool:
        if now - self._last_toggle < self._pause_cooldown:
            return False
        if self._cooldown.ok(self.NAME, now):
            self._last_toggle = now
            return True
        return False
