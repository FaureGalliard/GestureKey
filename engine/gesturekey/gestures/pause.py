from __future__ import annotations
from typing import Optional

from gesturekey.actions.types import Hotkey
from gesturekey.config import PauseConfig
from gesturekey.core.cooldown import CooldownManager
from gesturekey.core.types import FrameData, GestureEvent, HandState
from gesturekey.gestures.base import Gesture, Output

FIST_WITHIN = 0.5   # after leaving FOUR_FINGERS, the fist may arrive this late


class PauseResumeGesture(Gesture):
    """
    🖖 FOUR_FINGERS held (min_time … max_time), then ✊ → media play/pause.

    The hold must be long enough that the brief FOUR_FINGERS a hand passes
    through while closing from PALM to FIST doesn't count. Between letting go
    of four fingers and the fist the state filter may show a pose or two in
    passing (three fingers, unknown…): they are tolerated for FIST_WITHIN.
    """

    NAME = "PAUSE_RESUME"

    def __init__(self, cooldown: CooldownManager, cfg: PauseConfig) -> None:
        self._cooldown       = cooldown
        self._min_time       = cfg.min_time
        self._max_time       = cfg.max_time
        self._pause_cooldown = cfg.cooldown
        self._last_toggle    = float("-inf")
        self.reset()

    def update(self, frame: FrameData, out: Output) -> None:
        state, now = frame.state, frame.timestamp

        if state == HandState.FOUR_FINGERS:
            if self._start is None:
                self._start = now
            self._held = now - self._start
            self._left_at = None
            return

        if self._start is None:
            return
        if self._left_at is None:
            self._left_at = now
        armed = self._min_time <= self._held <= self._max_time

        if state == HandState.FIST and armed and self._cooldown_ok(now):
            out.emit(GestureEvent.MEDIA_PLAY_PAUSE, Hotkey(("media_play_pause",)))
            self.reset()
        elif not armed or now - self._left_at > FIST_WITHIN or state == HandState.PALM:
            self.reset()

    def reset(self) -> None:
        self._start: Optional[float] = None
        self._held = 0.0
        self._left_at: Optional[float] = None

    def _cooldown_ok(self, now: float) -> bool:
        if now - self._last_toggle < self._pause_cooldown:
            return False
        if self._cooldown.ok(self.NAME, now):
            self._last_toggle = now
            return True
        return False
