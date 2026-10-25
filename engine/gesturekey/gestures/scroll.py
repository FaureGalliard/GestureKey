from __future__ import annotations
from collections import deque
from typing import Any, Deque, Dict, Optional, Tuple

from gesturekey.actions.types import Scroll
from gesturekey.config import ContinuousConfig, ScrollConfig
from gesturekey.core.geometry import palm_center, palm_length
from gesturekey.core.types import GestureEvent, Hand, HandState
from gesturekey.gestures.base import Output
from gesturekey.gestures.continuous import ContinuousGesture

MIN_EMIT = 10   # wheel units accumulated before sending (keeps input events reasonable)


class ScrollGesture(ContinuousGesture):
    """
    ✌️ two fingers, drag-style: the page follows the hand like two fingers on a
    touchpad, with pointer-style acceleration (a quick flick travels far, a
    slow move is precise). Reversing direction is instant, so skimming up and
    down to look for something feels light.

    Moving fast is the point here, so speed does not end the gesture.
    Instead, when it ends the last `rollback` seconds are scrolled back: that
    was the hand going to rest, not an intention.
    """

    NAME = "SCROLL"
    POSE = HandState.TWO_FINGERS
    EXIT_ON_SPEED = False

    def __init__(self, cfg: ScrollConfig, cc: ContinuousConfig) -> None:
        self._cfg = cfg
        super().__init__(cc)

    @property
    def readout(self) -> Optional[Dict[str, Any]]:
        return {"rate": round(self._rate, 1)} if self._active else None

    def begin(self, hand: Hand, now: float, out: Output) -> None:
        self._last_y = palm_center(hand)[1]

    def act(self, hand: Hand, now: float, dt: float, out: Output) -> None:
        cfg = self._cfg
        y = palm_center(hand)[1]
        step = (y - self._last_y) / palm_length(hand)            # palm lengths, + = hand down
        self._last_y = y
        if dt <= 0:
            return
        speed = abs(step) / dt
        if speed < cfg.min_speed:                                 # jitter
            self._rate = 0.0
            return
        gain = min(cfg.max_gain, 1.0 + cfg.accel * max(0.0, speed - cfg.accel_from))
        wheel = step * cfg.per_palm * gain                        # + = hand down
        self._rate = wheel / dt
        self._accum += wheel
        if abs(self._accum) >= MIN_EMIT:
            amount = int(self._accum)
            self._accum -= amount
            self._send(amount, now, out)

    def end(self, now: float, reason: str, out: Output) -> None:
        undo = sum(a for t, a in self._sent if now - t <= self._cfg.rollback)
        if undo:
            out.actions.append(Scroll(self._wheel(-undo)))

    def _send(self, amount: int, now: float, out: Output) -> None:
        self._sent.append((now, amount))
        out.emit(GestureEvent.SCROLL, Scroll(self._wheel(amount)))

    def _wheel(self, hand_down: int) -> int:
        # wheel delta is positive = up; by default hand down → page down
        return hand_down if self._cfg.natural else -hand_down

    def reset(self) -> None:
        super().reset()
        self._last_y = 0.0
        self._accum = 0.0
        self._rate = 0.0
        self._sent: Deque[Tuple[float, int]] = deque(maxlen=240)
