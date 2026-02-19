"""
PinchZoomGesture — pinch open/close to zoom in/out (Ctrl+/Ctrl-).
"""
from __future__ import annotations
import math
from typing import List

import pyautogui

from domain.enums import GestureEvent, HandState
from domain.models import FrameData
from gestures.base import Gesture
from utils.geometry import hand_center

pyautogui.PAUSE = 0.01

BASE_GAIN              = 10
ACCEL_FACTOR           = 1.5
MAX_ZOOM_STEP          = 5
MIN_ZOOM_STEP          = 1

SIZE_COMPENSATION      = True
SIZE_RATIO_MIN         = 0.3
SIZE_RATIO_MAX         = 1.8
SIZE_ALPHA             = 0.6
POSITION_ALPHA         = 0.7
PINCH_ALPHA            = 0.5
MAX_POSITION_JUMP      = 0.15
MAX_SIZE_CHANGE        = 0.30
MAX_PINCH_JUMP         = 0.10
OUTLIER_RECOVERY_FRAMES = 2

VELOCITY_DEADZONE      = 0.003
TEMPORAL_FRAMES        = 3
MOTION_THRESHOLD       = 0.004
STILLNESS_TIMEOUT      = 0.1

INTENT_Z_ENTER         = -0.045
INTENT_Z_EXIT          = -0.005


def _euclidean(p1, p2) -> float:
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


class PinchZoomGesture(Gesture):
    NAME = "ZOOM"

    def __init__(self, arm_time: float = 0.18) -> None:
        self._arm_time = arm_time
        self.reset()

    # ------------------------------------------------------------------
    def detect(self, frame_data: FrameData) -> List[GestureEvent]:
        events: List[GestureEvent] = []

        if frame_data.state != HandState.PINCH:
            self.reset()
            return events

        main_hand = frame_data.main_hand
        hand_raw  = frame_data.main_hand_raw
        now       = frame_data.timestamp

        if main_hand is None:
            return events

        center_raw        = hand_center(main_hand)
        pinch_dist_raw    = _euclidean(main_hand[4], main_hand[8])
        current_hand_size = self._calc_hand_size(hand_raw) if hand_raw else None

        if self._smoothed_hand_size is None:
            self._smoothed_hand_size = current_hand_size
        elif current_hand_size is not None:
            self._smoothed_hand_size = (SIZE_ALPHA * current_hand_size
                                        + (1 - SIZE_ALPHA) * self._smoothed_hand_size)

        if self._smoothed_center is None:
            self._smoothed_center = center_raw
        else:
            self._smoothed_center = (
                POSITION_ALPHA * center_raw[0] + (1 - POSITION_ALPHA) * self._smoothed_center[0],
                POSITION_ALPHA * center_raw[1] + (1 - POSITION_ALPHA) * self._smoothed_center[1],
            )

        if self._smoothed_pinch is None:
            self._smoothed_pinch = pinch_dist_raw
        else:
            self._smoothed_pinch = (PINCH_ALPHA * pinch_dist_raw
                                    + (1 - PINCH_ALPHA) * self._smoothed_pinch)

        if not self._active:
            if not self._valid_detection(self._smoothed_center,
                                         self._smoothed_hand_size,
                                         self._smoothed_pinch):
                self._outlier_count += 1
                if self._outlier_count > OUTLIER_RECOVERY_FRAMES:
                    self.reset()
                return events
            self._outlier_count     = 0
            self._last_valid_center = self._smoothed_center
            self._last_valid_size   = self._smoothed_hand_size
            self._last_valid_pinch  = self._smoothed_pinch

        if hand_raw is not None and not self._depth_intent_ok(hand_raw):
            self.reset()
            return events

        if not self._active:
            if self._start_time is None:
                self._start_time        = now
                self._prev_pinch_raw    = pinch_dist_raw
                self._anchor_pinch      = pinch_dist_raw
                self._ref_hand_size     = self._smoothed_hand_size
                return events
            if now - self._start_time < self._arm_time:
                self._prev_pinch_raw = pinch_dist_raw
                return events
            self._active = True

        if self._prev_pinch_raw is not None:
            delta_raw = pinch_dist_raw - self._prev_pinch_raw

            if (SIZE_COMPENSATION and self._smoothed_hand_size
                    and self._ref_hand_size and self._ref_hand_size > 0):
                ratio = max(SIZE_RATIO_MIN, min(SIZE_RATIO_MAX,
                            self._ref_hand_size / self._smoothed_hand_size))
                delta = delta_raw * ratio
            else:
                delta = delta_raw

            if abs(delta) < VELOCITY_DEADZONE:
                delta = 0.0

            if abs(delta) > MOTION_THRESHOLD:
                self._last_motion_time = now
            elif self._last_motion_time and now - self._last_motion_time > STILLNESS_TIMEOUT:
                self._prev_pinch_raw = pinch_dist_raw
                return events

            if self._pinch_100ms is None or self._t_100ms is None:
                self._pinch_100ms = pinch_dist_raw
                self._t_100ms     = now
            elif now - self._t_100ms >= 0.1:
                if abs(pinch_dist_raw - self._pinch_100ms) < MOTION_THRESHOLD:
                    self._prev_pinch_raw = pinch_dist_raw
                    return events
                self._pinch_100ms = pinch_dist_raw
                self._t_100ms     = now

            if delta != 0.0:
                self._d_buffer.append(delta)
                if len(self._d_buffer) > TEMPORAL_FRAMES:
                    self._d_buffer.pop(0)

            if len(self._d_buffer) < TEMPORAL_FRAMES:
                self._prev_pinch_raw = pinch_dist_raw
                return events

            d_eff        = sum(self._d_buffer) / len(self._d_buffer)
            dist_anchor  = abs(pinch_dist_raw - self._anchor_pinch)
            gain         = BASE_GAIN + dist_anchor * ACCEL_FACTOR
            steps        = int(d_eff * gain)

            if abs(steps) >= MIN_ZOOM_STEP:
                steps = max(-MAX_ZOOM_STEP, min(MAX_ZOOM_STEP, steps))
                if d_eff > 0:
                    for _ in range(abs(steps)):
                        pyautogui.hotkey("ctrl", "+")
                    events.append(GestureEvent.ZOOM_IN)
                else:
                    for _ in range(abs(steps)):
                        pyautogui.hotkey("ctrl", "-")
                    events.append(GestureEvent.ZOOM_OUT)

        self._prev_pinch_raw = pinch_dist_raw
        return events

    # ------------------------------------------------------------------
    def reset(self) -> None:
        self._prev_pinch_raw     = None
        self._active             = False
        self._start_time         = None
        self._anchor_pinch       = None
        self._ref_hand_size      = None
        self._smoothed_hand_size = None
        self._outlier_count      = 0
        self._last_valid_center  = None
        self._last_valid_size    = None
        self._last_valid_pinch   = None
        self._smoothed_center    = None
        self._smoothed_pinch     = None
        self._d_buffer: list     = []
        self._last_motion_time   = None
        self._pinch_100ms        = None
        self._t_100ms            = None
        self._intent_active      = False

    def _valid_detection(self, center, hand_size, pinch) -> bool:
        if self._last_valid_center is None:
            return True
        if abs(center[1] - self._last_valid_center[1]) > MAX_POSITION_JUMP:
            return False
        if (hand_size and self._last_valid_size and self._last_valid_size > 0
                and abs(hand_size - self._last_valid_size) / self._last_valid_size > MAX_SIZE_CHANGE):
            return False
        if (pinch and self._last_valid_pinch
                and abs(pinch - self._last_valid_pinch) > MAX_PINCH_JUMP):
            return False
        return True

    def _depth_intent_ok(self, hand_raw) -> bool:
        depth = self._relative_depth(hand_raw)
        if not self._intent_active:
            if depth < INTENT_Z_ENTER:
                self._intent_active = True
        else:
            if depth > INTENT_Z_EXIT:
                self._intent_active = False
        return self._intent_active

    @staticmethod
    def _relative_depth(hand_raw) -> float:
        wrist_z = hand_raw.landmark[0].z
        tip_z   = sum(hand_raw.landmark[i].z for i in [4, 8, 12, 16, 20]) / 5
        return tip_z - wrist_z

    @staticmethod
    def _calc_hand_size(hand_raw) -> float:
        w, m = hand_raw.landmark[0], hand_raw.landmark[12]
        return ((m.x-w.x)**2 + (m.y-w.y)**2 + (m.z-w.z)**2) ** 0.5