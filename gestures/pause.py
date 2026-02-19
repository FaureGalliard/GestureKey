"""
PauseResumeGesture — stable PALM then FIST transition to toggle media play/pause.
"""
from __future__ import annotations
import time
from typing import List, Optional

try:
    import win32api, win32con
    _HAS_WIN32 = True
except ImportError:
    _HAS_WIN32 = False

from domain.enums import GestureEvent, HandState
from domain.models import FrameData
from gestures.base import Gesture
from core.cooldown_manager import CooldownManager


class PauseResumeGesture(Gesture):
    NAME = "PAUSE_RESUME"

    def __init__(
        self,
        cooldown: CooldownManager,
        min_time: float = 0.20,
        max_time: float = 1.50,
        pause_cooldown: float = 0.50,
    ) -> None:
        self._cooldown      = cooldown
        self._min_time      = min_time
        self._max_time      = max_time
        self._pause_cooldown = pause_cooldown
        self._paused        = False
        self._last_toggle   = 0.0
        self.reset()

    # ------------------------------------------------------------------
    def detect(self, frame_data: FrameData) -> List[GestureEvent]:
        events: List[GestureEvent] = []
        state = frame_data.state
        now   = frame_data.timestamp

        if state == HandState.PALM:
            if self._last_state != HandState.PALM:
                self._palm_start = now
                self._armed      = False
            elif self._palm_start is not None:
                if now - self._palm_start >= self._min_time and not self._armed:
                    self._armed = True

        elif state == HandState.FIST:
            if self._armed and self._last_state == HandState.PALM:
                elapsed = now - (self._palm_start or now)
                if elapsed <= self._max_time and self._local_cooldown_ok(now):
                    self._execute_toggle()
                    self._paused = not self._paused
                    event = (GestureEvent.PAUSE_TOGGLE_PAUSED
                             if self._paused
                             else GestureEvent.PAUSE_TOGGLE_RESUMED)
                    events.append(event)
                    self.reset()
            elif not self._armed:
                self.reset()
        else:
            self.reset()

        self._last_state = state
        return events

    # ------------------------------------------------------------------
    def reset(self) -> None:
        self._palm_start: Optional[float] = None
        self._armed      = False
        self._last_state: Optional[HandState] = None

    def is_paused(self) -> bool:
        return self._paused

    # ------------------------------------------------------------------
    def _local_cooldown_ok(self, now: float) -> bool:
        if now - self._last_toggle < self._pause_cooldown:
            return False
        if self._cooldown.ok(self.NAME):
            self._last_toggle = now
            return True
        return False

    @staticmethod
    def _execute_toggle() -> None:
        if not _HAS_WIN32:
            print("[PAUSE] win32api not available — skipping key press")
            return
        try:
            win32api.keybd_event(win32con.VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
            time.sleep(0.05)
            win32api.keybd_event(win32con.VK_MEDIA_PLAY_PAUSE, 0,
                                 win32con.KEYEVENTF_KEYUP, 0)
        except Exception as exc:
            print(f"[PAUSE] Error sending key: {exc}")