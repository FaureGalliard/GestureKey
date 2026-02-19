"""
TaskViewGesture — bring both palms together to open Win+Tab Task View.
"""
from __future__ import annotations
import time
from typing import List

import pyautogui

from domain.enums import GestureEvent, HandState
from domain.models import FrameData
from gestures.base import Gesture
from core.cooldown_manager import CooldownManager
from utils.geometry import dist, hand_center

pyautogui.PAUSE = 0.01

MIN_INITIAL_DISTANCE   = 0.30
MIN_APPROACH_TOTAL     = 0.15
MAX_APPROACH_SPEED     = 0.50
MAX_POSITION_JUMP      = 0.20
OUTLIER_RECOVERY_FRAMES = 2
DISTANCE_ALPHA         = 0.60
STABILITY_TIME         = 0.15
STABILITY_FRAMES       = 3


class TaskViewGesture(Gesture):
    NAME = "TASK_VIEW"

    def __init__(
        self,
        cooldown: CooldownManager,
        arm_time: float = 0.15,
        min_approach: float = 0.15,
        task_view_cooldown: float = 1.5,
    ) -> None:
        self._cooldown          = cooldown
        self._arm_time          = arm_time
        self._min_approach      = min_approach
        self._task_view_cooldown = task_view_cooldown
        self._last_activation   = 0.0
        self.reset()

    # ------------------------------------------------------------------
    def detect(self, frame_data: FrameData) -> List[GestureEvent]:
        events: List[GestureEvent] = []
        now = frame_data.timestamp

        if not frame_data.has_both_hands or frame_data.state != HandState.PALM:
            self.reset()
            return events

        center_left  = hand_center(frame_data.hands["Left"])
        center_right = hand_center(frame_data.hands["Right"])
        distance_raw = dist(center_left, center_right)

        if self._smoothed_distance is None:
            self._smoothed_distance = distance_raw
        else:
            self._smoothed_distance = (DISTANCE_ALPHA * distance_raw
                                       + (1 - DISTANCE_ALPHA) * self._smoothed_distance)

        # Stability validation (pre-arm only)
        if not self._armed:
            if self._stable(center_left, center_right):
                self._stable_count += 1
                self._last_valid_left  = center_left
                self._last_valid_right = center_right
                self._outlier_count    = 0
            else:
                self._stable_count = 0
                self._outlier_count += 1
                if self._outlier_count > OUTLIER_RECOVERY_FRAMES:
                    self.reset()
                return events

            if self._stable_count < STABILITY_FRAMES:
                return events

            # Arm by time
            if self._both_start is None:
                self._both_start      = now
                self._initial_dist    = distance_raw
                self._anchor_dist     = distance_raw
                self._prev_dist_raw   = distance_raw
                return events

            if self._initial_dist < MIN_INITIAL_DISTANCE:
                self.reset()
                return events

            if now - self._both_start < STABILITY_TIME:
                self._prev_dist_raw = distance_raw
                return events

            self._armed = True

        # Accumulate approach
        if self._prev_dist_raw is not None:
            delta = self._prev_dist_raw - distance_raw
            if delta > MAX_APPROACH_SPEED:
                self._prev_dist_raw = distance_raw
                return events
            if delta > 0:
                self._total_approach += delta

            if self._total_approach >= self._min_approach:
                if self._local_cooldown_ok(now):
                    self._execute()
                    events.append(GestureEvent.TASK_VIEW)
                    self.reset()

        self._prev_dist_raw = distance_raw
        return events

    # ------------------------------------------------------------------
    def reset(self) -> None:
        self._both_start      = None
        self._armed           = False
        self._initial_dist    = None
        self._anchor_dist     = None
        self._prev_dist_raw   = None
        self._smoothed_distance = None
        self._stable_count    = 0
        self._outlier_count   = 0
        self._last_valid_left  = None
        self._last_valid_right = None
        self._total_approach  = 0.0

    def _stable(self, left, right) -> bool:
        if self._last_valid_left is None or self._last_valid_right is None:
            return True
        if dist(left,  self._last_valid_left)  > MAX_POSITION_JUMP:
            return False
        if dist(right, self._last_valid_right) > MAX_POSITION_JUMP:
            return False
        return True

    def _local_cooldown_ok(self, now: float) -> bool:
        if now - self._last_activation < self._task_view_cooldown:
            return False
        if self._cooldown.ok(self.NAME):
            self._last_activation = now
            return True
        return False

    @staticmethod
    def _execute() -> None:
        try:
            pyautogui.hotkey("win", "tab")
        except Exception as exc:
            print(f"[TASK_VIEW] Error: {exc}")