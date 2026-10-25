from __future__ import annotations
import math
from collections import deque
from typing import Deque, Tuple

from gesturekey.actions.types import Hotkey
from gesturekey.config import ContinuousConfig, ZoomConfig
from gesturekey.core.geometry import dist, palm_length
from gesturekey.core.types import GestureEvent, Hand, HandState
from gesturekey.gestures.base import Output
from gesturekey.gestures.continuous import ContinuousGesture

MAX_STEPS = 10
ROLLBACK_S = 0.25


class PinchZoomGesture(ContinuousGesture):
    """
    🤏 pinch, then open / close thumb and index. Each `step_ratio` change of
    the thumb–index gap (relative to the start, in palm lengths) is one zoom
    step, so the zoom follows the fingers and is reversible: close back to
    the start and you are back at the start zoom.

    An opening pinch soon stops looking like a pinch to the classifier, so
    while active the gesture tolerates the neighbouring poses.
    """

    NAME = "ZOOM"
    POSE = HandState.PINCH
    KEEP = frozenset({HandState.TWO_FINGERS, HandState.THREE_FINGERS, HandState.UNKNOWN})

    def __init__(self, cfg: ZoomConfig, cc: ContinuousConfig) -> None:
        self._log_step = math.log(cfg.step_ratio)
        super().__init__(cc)

    @staticmethod
    def _gap(hand: Hand) -> float:
        return max(1e-3, dist(hand.img[4], hand.img[8]) / palm_length(hand))

    def begin(self, hand: Hand, now: float, out: Output) -> None:
        self._gap0 = self._gap(hand)
        self._steps = 0
        self._history.append((now, 0))

    def act(self, hand: Hand, now: float, dt: float, out: Output) -> None:
        target = round(math.log(self._gap(hand) / self._gap0) / self._log_step)
        target = max(-MAX_STEPS, min(MAX_STEPS, target))
        self._send(target - self._steps, out)
        self._steps = target
        self._history.append((now, self._steps))

    def end(self, now: float, reason: str, out: Output) -> None:
        keep = self._steps
        for t, steps in self._history:
            if t <= now - ROLLBACK_S:
                keep = steps
        self._send(keep - self._steps, out, quiet=True)

    @staticmethod
    def _send(diff: int, out: Output, quiet: bool = False) -> None:
        if diff == 0:
            return
        key = "plus" if diff > 0 else "minus"
        action = Hotkey(("ctrl", key), times=abs(diff))
        if quiet:
            out.actions.append(action)
        else:
            out.emit(GestureEvent.ZOOM_IN if diff > 0 else GestureEvent.ZOOM_OUT, action)

    def reset(self) -> None:
        super().reset()
        self._gap0 = 1.0
        self._steps = 0
        self._history: Deque[Tuple[float, int]] = deque(maxlen=120)
