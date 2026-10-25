from __future__ import annotations
from abc import abstractmethod
from typing import FrozenSet, Optional

from gesturekey.config import ContinuousConfig
from gesturekey.core.geometry import dist
from gesturekey.core.types import FrameData, Hand, HandState, Point
from gesturekey.gestures.base import Gesture, Output


class ContinuousGesture(Gesture):
    """
    Base for gestures that act for as long as a pose is held (scroll, volume, zoom).

    Lifecycle: IDLE → ARMING (pose held `arm_time`) → ACTIVE → end.

    Knowing *when the user is done* is the hard part. An active gesture ends
    the moment any of these happens:
      - the filtered state leaves the pose            → "pose"
      - the classifier disagrees for `doubt_time`     → "doubt"  (frozen meanwhile)
      - the wrist moves faster than `exit_speed`      → "fast"   (dropping the hand)
      - the hand is lost                               → "lost"
    Subclasses get begin/act/end hooks; `end` can undo the last moments, which
    is how volume and zoom forgive the movement of putting the hand down.
    """

    POSE: HandState = HandState.UNKNOWN
    #: states that keep an active gesture alive (zoom tolerates an opening pinch)
    KEEP: FrozenSet[HandState] = frozenset()

    def __init__(self, cc: ContinuousConfig) -> None:
        self._arm_time   = cc.arm_time
        self._exit_speed = cc.exit_speed
        self._doubt_time = cc.doubt_time
        self._keep = self.KEEP | {self.POSE}
        self._prev: Optional[tuple] = None   # (t, wrist) for speed
        self.reset()

    # ── hooks ────────────────────────────────────────────────────────────────

    @abstractmethod
    def begin(self, hand: Hand, now: float, out: Output) -> None: ...

    @abstractmethod
    def act(self, hand: Hand, now: float, dt: float, out: Output) -> None: ...

    def end(self, now: float, reason: str, out: Output) -> None:
        """Called once when an active gesture finishes."""

    # ── state machine ────────────────────────────────────────────────────────

    @property
    def engaged(self) -> bool:
        return self._active

    def update(self, frame: FrameData, out: Output) -> None:
        hand, now = frame.main_hand, frame.timestamp
        if hand is None:
            self.on_lost(now, out)
            return
        speed, dt = self._speed(hand.wrist, now)

        if self._active:
            if frame.state not in self._keep:
                return self._finish(now, "pose", out)
            if speed > self._exit_speed:
                return self._finish(now, "fast", out)
            if frame.raw_state is not None and frame.raw_state not in self._keep:
                self._doubt_since = self._doubt_since or now
                if now - self._doubt_since >= self._doubt_time:
                    return self._finish(now, "doubt", out)
                return                                  # frozen while in doubt
            self._doubt_since = None
            self.act(hand, now, dt, out)
            return

        if frame.state != self.POSE:
            self.reset()
            return
        if self._arm_start is None:
            self._arm_start = now
        elif now - self._arm_start >= self._arm_time and speed < self._exit_speed:
            self._active = True
            self.begin(hand, now, out)

    def on_lost(self, now: float, out: Output) -> None:
        if self._active:
            self._finish(now, "lost", out)
        else:
            self.reset()

    def _finish(self, now: float, reason: str, out: Output) -> None:
        self.end(now, reason, out)
        self.reset()

    def _speed(self, wrist: Point, now: float) -> tuple:
        prev, self._prev = self._prev, (now, wrist)
        if prev is None or now <= prev[0]:
            return 0.0, 0.0
        dt = now - prev[0]
        return dist(wrist, prev[1]) / dt, dt

    def reset(self) -> None:
        self._active = False
        self._arm_start: Optional[float] = None
        self._doubt_since: Optional[float] = None
