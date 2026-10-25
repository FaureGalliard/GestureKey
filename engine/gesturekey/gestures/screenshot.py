from __future__ import annotations
import math
from typing import Optional

from gesturekey.actions.types import Hotkey
from gesturekey.config import ScreenshotConfig
from gesturekey.core.cooldown import CooldownManager
from gesturekey.core.geometry import dist, palm_center, palm_length
from gesturekey.core.types import FrameData, GestureEvent, Hand
from gesturekey.gestures.base import Gesture, Output

INDEX_OUT  = 1.30   # index tip ↔ wrist (palm lengths): extended
THUMB_OUT  = 0.60   # thumb tip ↔ index knuckle: stretched away, not tucked across the palm
THUMB_WIDE = 50.0   # degrees between thumb and index: an L, not a flat palm
CURLED     = 1.20   # middle / ring tip ↔ wrist below this: folded
MIN_APART  = 0.15   # image units between the two hands
MAX_DRIFT  = 0.06   # image units a hand may wander while the frame is held


def is_l_shape(hand: Hand) -> bool:
    """
    👆 index and thumb stretched apart like an L, the other fingers folded.
    Pure finger geometry, so it works with the L at any angle (one hand is
    often upside down in a frame), where the pose model has no class for it.
    """
    p, pl = hand.img, palm_length(hand)
    if dist(p[8], p[0]) / pl < INDEX_OUT or dist(p[4], p[5]) / pl < THUMB_OUT:
        return False
    if dist(p[12], p[0]) / pl > CURLED or dist(p[16], p[0]) / pl > CURLED:
        return False
    tx, ty = p[4][0] - p[2][0], p[4][1] - p[2][1]
    ix, iy = p[8][0] - p[5][0], p[8][1] - p[5][1]
    cos = (tx * ix + ty * iy) / ((math.hypot(tx, ty) * math.hypot(ix, iy)) or 1e-9)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos)))) >= THUMB_WIDE


class ScreenshotGesture(Gesture):
    """
    🖼️ both hands in an L, framing the screen like a photo, held `hold` s →
    Win+PrintScreen (saved to Pictures\\Screenshots). Two hands in a pose
    nothing else uses, so it cannot fire by accident.
    """

    NAME = "SCREENSHOT"

    def __init__(self, cooldown: CooldownManager, cfg: ScreenshotConfig) -> None:
        self._cooldown = cooldown
        self._hold = cfg.hold
        self.reset()

    @property
    def progress(self) -> Optional[float]:
        if self._since is None:
            return None
        return min(1.0, (self._now - self._since) / self._hold)

    def update(self, frame: FrameData, out: Output) -> None:
        now = self._now = frame.timestamp
        hands = frame.hands
        if not frame.has_both_hands or not all(is_l_shape(h) for h in hands.values()):
            return self.reset()
        left, right = palm_center(hands["Left"]), palm_center(hands["Right"])
        if dist(left, right) < MIN_APART:
            return self.reset()
        if self._since is None or dist(left, self._left) > MAX_DRIFT or dist(right, self._right) > MAX_DRIFT:
            self._since, self._left, self._right = now, left, right       # (re)start the hold
            return
        if now - self._since >= self._hold and self._cooldown.ok(self.NAME, now):
            out.emit(GestureEvent.SCREENSHOT, Hotkey(("win", "printscreen")))
            self.reset()

    def reset(self) -> None:
        self._since: Optional[float] = None
        self._left = self._right = (0.0, 0.0)
        self._now = 0.0
