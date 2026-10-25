from __future__ import annotations
from collections import deque
from typing import Deque, Tuple

from gesturekey.actions.types import Hotkey
from gesturekey.config import ScreenshotConfig
from gesturekey.core.cooldown import CooldownManager
from gesturekey.core.geometry import dist
from gesturekey.core.types import FrameData, GestureEvent, HandState
from gesturekey.gestures.base import Gesture, Output

WINDOW_S     = 0.25   # look-back window
SHRINK_RATIO = 0.70   # palm must shrink to 70 % of its recent max


class ScreenshotGesture(Gesture):
    """
    PALM pushed quickly away from the camera → Win+PrintScreen.

    Measured in image space: in v2 this used the wrist→middle-MCP distance of
    the *normalised* landmarks, which is always 1.0, so it never fired.
    """

    NAME = "SCREENSHOT"

    def __init__(self, cooldown: CooldownManager, cfg: ScreenshotConfig) -> None:
        self._cooldown = cooldown
        self.reset()

    def update(self, frame: FrameData, out: Output) -> None:
        hand = frame.main_hand
        if frame.state != HandState.PALM or hand is None:
            self.reset()
            return

        now   = frame.timestamp
        scale = dist(hand.img[0], hand.img[9])
        self._recent.append((now, scale))
        while self._recent and now - self._recent[0][0] > WINDOW_S:
            self._recent.popleft()

        peak = max(s for _, s in self._recent)
        if peak > 0 and scale < peak * SHRINK_RATIO and self._cooldown.ok(self.NAME, now):
            out.emit(GestureEvent.SCREENSHOT, Hotkey(("win", "printscreen")))
            self._recent.clear()

    def reset(self) -> None:
        self._recent: Deque[Tuple[float, float]] = deque()
