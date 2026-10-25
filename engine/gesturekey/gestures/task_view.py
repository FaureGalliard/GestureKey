from __future__ import annotations
from typing import Optional

from gesturekey.actions.types import Hotkey
from gesturekey.config import TaskViewConfig
from gesturekey.core.cooldown import CooldownManager
from gesturekey.core.geometry import dist, hand_center
from gesturekey.core.types import FrameData, GestureEvent, HandState, Point
from gesturekey.gestures.base import Gesture, Output

MIN_INITIAL_DISTANCE    = 0.30
MAX_APPROACH_SPEED      = 0.50
MAX_POSITION_JUMP       = 0.20
OUTLIER_RECOVERY_FRAMES = 2
DISTANCE_ALPHA          = 0.60
STABILITY_FRAMES        = 3


class TaskViewGesture(Gesture):
    """Two open palms apart, then brought together → Win+Tab."""

    NAME = "TASK_VIEW"

    def __init__(self, cooldown: CooldownManager, cfg: TaskViewConfig) -> None:
        self._cooldown           = cooldown
        self._arm_time           = cfg.arm_time
        self._min_approach       = cfg.min_approach
        self._task_view_cooldown = cfg.cooldown
        self._last_activation    = float("-inf")
        self.reset()

    def update(self, frame: FrameData, out: Output) -> None:
        now = frame.timestamp
        if not frame.has_both_hands or frame.state != HandState.PALM:
            self.reset()
            return

        center_left  = hand_center(frame.hands["Left"].norm)
        center_right = hand_center(frame.hands["Right"].norm)
        distance_raw = dist(center_left, center_right)

        if self._smoothed_distance is None:
            self._smoothed_distance = distance_raw
        else:
            self._smoothed_distance = DISTANCE_ALPHA * distance_raw + (1 - DISTANCE_ALPHA) * self._smoothed_distance

        if not self._armed:
            if self._stable(center_left, center_right):
                self._stable_count     += 1
                self._last_valid_left  = center_left
                self._last_valid_right = center_right
                self._outlier_count    = 0
            else:
                self._stable_count   = 0
                self._outlier_count += 1
                if self._outlier_count > OUTLIER_RECOVERY_FRAMES:
                    self.reset()
                return

            if self._stable_count < STABILITY_FRAMES:
                return

            if self._both_start is None:
                self._both_start    = now
                self._initial_dist  = distance_raw
                self._prev_dist_raw = distance_raw
                return

            if self._initial_dist is not None and self._initial_dist < MIN_INITIAL_DISTANCE:
                self.reset()
                return

            if now - self._both_start < self._arm_time:
                self._prev_dist_raw = distance_raw
                return

            self._armed = True

        if self._prev_dist_raw is not None:
            delta = self._prev_dist_raw - distance_raw
            if delta > MAX_APPROACH_SPEED:
                self._prev_dist_raw = distance_raw
                return
            if delta > 0:
                self._total_approach += delta

            if self._total_approach >= self._min_approach and self._cooldown_ok(now):
                out.emit(GestureEvent.TASK_VIEW, Hotkey(("win", "tab")))
                self.reset()
                return

        self._prev_dist_raw = distance_raw

    def reset(self) -> None:
        self._both_start:        Optional[float] = None
        self._armed:             bool            = False
        self._initial_dist:      Optional[float] = None
        self._prev_dist_raw:     Optional[float] = None
        self._smoothed_distance: Optional[float] = None
        self._stable_count:      int             = 0
        self._outlier_count:     int             = 0
        self._last_valid_left:   Optional[Point] = None
        self._last_valid_right:  Optional[Point] = None
        self._total_approach:    float           = 0.0

    def _stable(self, left: Point, right: Point) -> bool:
        if self._last_valid_left is None or self._last_valid_right is None:
            return True
        return (dist(left, self._last_valid_left) <= MAX_POSITION_JUMP
                and dist(right, self._last_valid_right) <= MAX_POSITION_JUMP)

    def _cooldown_ok(self, now: float) -> bool:
        if now - self._last_activation < self._task_view_cooldown:
            return False
        if self._cooldown.ok(self.NAME, now):
            self._last_activation = now
            return True
        return False
