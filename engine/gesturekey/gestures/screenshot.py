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


class ScreenshotGesture(Gesture):
    """
    ✋ open palm pushed quickly away from the camera (it looks smaller) →
    Win+PrintScreen. Measured in image space; a short blur mid-push doesn't
    reset it.
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

        peak = max(s for _, s in self._recent)
        if size < peak * SHRINK_RATIO and self._cooldown.ok(self.NAME, now):
            out.emit(GestureEvent.SCREENSHOT, Hotkey(("win", "printscreen")))
            self._recent.clear()

    def reset(self) -> None:
        self._recent: Deque[Tuple[float, float]] = deque()
        self._last_palm: Optional[float] = None
