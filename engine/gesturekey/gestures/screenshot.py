from __future__ import annotations
from collections import deque
from typing import Deque, Optional, Tuple

from gesturekey.actions.types import Hotkey
from gesturekey.config import ScreenshotConfig
from gesturekey.core.cooldown import CooldownManager
from gesturekey.core.geometry import palm_length
from gesturekey.core.types import FrameData, GestureEvent, HandState
from gesturekey.gestures.base import Gesture, Output

WINDOW_S     = 0.40   # look-back window
SHRINK_RATIO = 0.75   # palm must shrink to 75 % of its recent size
GRACE_S      = 0.15   # a fast push blurs the palm; tolerate this much non-PALM
ARM_S        = 0.30   # the palm must first be held steady this long
STEADY       = 0.08   # "steady" = palm size within ±8 % of its running level


class ScreenshotGesture(Gesture):
    """
    ✋ open palm held steady a moment, then pushed quickly away from the camera
    (it looks smaller) → Win+PrintScreen. The steady hold first keeps a hand
    that just happens to move back from firing it. Measured in image space; a
    short blur mid-push doesn't reset it.
    """

    NAME = "SCREENSHOT"

    def __init__(self, cooldown: CooldownManager, cfg: ScreenshotConfig) -> None:
        self._cooldown = cooldown
        self.reset()

    def update(self, frame: FrameData, out: Output) -> None:
        hand, now = frame.main_hand, frame.timestamp
        if hand is None:
            self.reset()
            return
        if frame.state != HandState.PALM:
            if self._last_palm is not None and now - self._last_palm > GRACE_S:
                self.reset()
            return
        self._last_palm = now

        size = palm_length(hand)
        self._recent.append((now, size))
        while self._recent and now - self._recent[0][0] > WINDOW_S:
            self._recent.popleft()

        if not self._armed:
            if self._level is None or abs(size - self._level) > STEADY * self._level:
                self._level, self._steady_since = size, now          # moving: start over
            else:
                self._level = 0.8 * self._level + 0.2 * size
                if now - self._steady_since >= ARM_S:
                    self._armed = True
            return

        peak = max(s for _, s in self._recent)
        if size < peak * SHRINK_RATIO and self._cooldown.ok(self.NAME, now):
            out.emit(GestureEvent.SCREENSHOT, Hotkey(("win", "printscreen")))
            self.reset()

    def reset(self) -> None:
        self._recent: Deque[Tuple[float, float]] = deque()
        self._last_palm: Optional[float] = None
        self._level: Optional[float] = None
        self._steady_since = 0.0
        self._armed = False
