from __future__ import annotations
from collections import deque
from typing import Deque, Tuple

from gesturekey.actions.types import VolumeBegin, VolumeSet
from gesturekey.config import ContinuousConfig, VolumeConfig
from gesturekey.core.geometry import palm_center, palm_length
from gesturekey.core.types import GestureEvent, Hand, HandState
from gesturekey.gestures.base import Output
from gesturekey.gestures.continuous import ContinuousGesture

MIN_STEP = 0.005   # don't send changes smaller than half a percent


class VolumeGesture(ContinuousGesture):
    """
    🤟 three fingers, absolute: the hand's height relative to where the
    gesture started maps to a volume level (start level ± per_palm per palm
    length). Going up and back down the same distance lands on the same
    level. Volume is bounded (0–100), so position — not speed — is the
    natural mapping.

    When the gesture ends, the last `rollback` seconds are undone: that is
    the hand travelling to its resting place, not an intention.
    """

    NAME = "VOLUME"
    POSE = HandState.THREE_FINGERS

    def __init__(self, cfg: VolumeConfig, cc: ContinuousConfig) -> None:
        self._per_palm = cfg.per_palm
        self._deadzone = cfg.deadzone
        self._rollback = cfg.rollback
        super().__init__(cc)

    def begin(self, hand: Hand, now: float, out: Output) -> None:
        self._anchor_y = palm_center(hand)[1]
        self._sent = 0.0
        self._history.append((now, 0.0))
        out.actions.append(VolumeBegin())

    def act(self, hand: Hand, now: float, dt: float, out: Output) -> None:
        offset = (self._anchor_y - palm_center(hand)[1]) / palm_length(hand)   # + = hand moved up
        mag = max(0.0, abs(offset) - self._deadzone)
        delta = mag * self._per_palm * (1 if offset > 0 else -1)
        if abs(delta - self._sent) >= MIN_STEP:
            event = GestureEvent.VOLUME_UP if delta > self._sent else GestureEvent.VOLUME_DOWN
            self._sent = delta
            out.emit(event, VolumeSet(delta))
        self._history.append((now, self._sent))

    def end(self, now: float, reason: str, out: Output) -> None:
        keep = self._sent
        for t, sent in self._history:
            if t <= now - self._rollback:
                keep = sent
        if abs(keep - self._sent) >= MIN_STEP:
            out.actions.append(VolumeSet(keep))

    def reset(self) -> None:
        super().reset()
        self._anchor_y = 0.0
        self._sent = 0.0
        self._history: Deque[Tuple[float, float]] = deque(maxlen=120)
