"""
VolumeGesture — three-finger vertical movement to change system volume.
"""
from __future__ import annotations
from typing import List

import pyautogui

from domain.enums import GestureEvent, HandState
from domain.models import FrameData
from gestures.base import Gesture
from utils.geometry import hand_center

pyautogui.PAUSE = 0.01

# ---- tuning -----------------------------------------------------------
BASE_GAIN              = 100
ACCEL_FACTOR           = 200
MAX_VOLUME_STEP        = 30
MIN_VOLUME_STEP        = 1

SIZE_COMPENSATION      = True
SIZE_RATIO_MIN         = 0.7
SIZE_RATIO_MAX         = 1.4
SIZE_ALPHA             = 0.6
POSITION_ALPHA         = 0.7
MAX_POSITION_JUMP      = 0.15
MAX_SIZE_CHANGE        = 0.30
OUTLIER_RECOVERY_FRAMES = 2

VELOCITY_DEADZONE      = 0.0025
TEMPORAL_FRAMES        = 3
MOTION_THRESHOLD       = 0.0035
STILLNESS_TIMEOUT      = 0.1

INTENT_Z_ENTER         = -0.045
INTENT_Z_EXIT          = -0.005


class VolumeGesture(Gesture):
    NAME = "VOLUME"

    def __init__(self, arm_time: float = 0.20) -> None:
        self._arm_time = arm_time
        self.reset()

    # ------------------------------------------------------------------
    def detect(self, frame_data: FrameData) -> List[GestureEvent]:
        events: List[GestureEvent] = []

        if frame_data.state != HandState.THREE_FINGERS:
            self.reset()
            return events

        main_hand = frame_data.main_hand
        hand_raw  = frame_data.main_hand_raw
        now       = frame_data.timestamp

        if main_hand is None:
            return events

        center_raw        = hand_center(main_hand)
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

        if not self._active:
            if not self._valid_detection(self._smoothed_center, self._smoothed_hand_size):
                self._outlier_count += 1
                if self._outlier_count > OUTLIER_RECOVERY_FRAMES:
                    self.reset()
                return events
            self._outlier_count      = 0
            self._last_valid_center  = self._smoothed_center
            self._last_valid_size    = self._smoothed_hand_size

        if hand_raw is not None and not self._depth_intent_ok(hand_raw):
            self.reset()
            return events

        if not self._active:
            if self._start_time is None:
                self._start_time      = now
                self._prev_center_raw = center_raw
                self._anchor_y        = center_raw[1]
                self._ref_hand_size   = self._smoothed_hand_size
                return events
            if now - self._start_time < self._arm_time:
                self._prev_center_raw = center_raw
                return events
            self._active = True

        if self._prev_center_raw is not None:
            dy_raw = center_raw[1] - self._prev_center_raw[1]

            if (SIZE_COMPENSATION and self._smoothed_hand_size
                    and self._ref_hand_size and self._ref_hand_size > 0):
                ratio = max(SIZE_RATIO_MIN, min(SIZE_RATIO_MAX,
                            self._ref_hand_size / self._smoothed_hand_size))
                dy = dy_raw * ratio
            else:
                dy = dy_raw

            if abs(dy) < VELOCITY_DEADZONE:
                dy = 0.0

            if abs(dy) > MOTION_THRESHOLD:
                self._last_motion_time = now
            elif self._last_motion_time and now - self._last_motion_time > STILLNESS_TIMEOUT:
                self._prev_center_raw = center_raw
                return events

            if self._pos_100ms is None or self._t_100ms is None:
                self._pos_100ms = center_raw[1]
                self._t_100ms   = now
            elif now - self._t_100ms >= 0.1:
                if abs(center_raw[1] - self._pos_100ms) < MOTION_THRESHOLD:
                    self._prev_center_raw = center_raw
                    return events
                self._pos_100ms = center_raw[1]
                self._t_100ms   = now

            if dy != 0.0:
                self._dy_buffer.append(dy)
                if len(self._dy_buffer) > TEMPORAL_FRAMES:
                    self._dy_buffer.pop(0)

            if len(self._dy_buffer) < TEMPORAL_FRAMES:
                self._prev_center_raw = center_raw
                return events

            dy_eff      = sum(self._dy_buffer) / len(self._dy_buffer)
            dist_anchor = abs(center_raw[1] - self._anchor_y)
            gain        = BASE_GAIN + dist_anchor * ACCEL_FACTOR
            steps       = int(dy_eff * gain)

            if abs(steps) >= MIN_VOLUME_STEP:
                steps = max(-MAX_VOLUME_STEP, min(MAX_VOLUME_STEP, steps))
                if dy_eff < 0:
                    for _ in range(abs(steps)):
                        pyautogui.press("volumeup")
                    events.append(GestureEvent.VOLUME_UP)
                else:
                    for _ in range(abs(steps)):
                        pyautogui.press("volumedown")
                    events.append(GestureEvent.VOLUME_DOWN)

        self._prev_center_raw = center_raw
        return events

    # ------------------------------------------------------------------
    def reset(self) -> None:
        self._prev_center_raw    = None
        self._active             = False
        self._start_time         = None
        self._anchor_y           = None
        self._ref_hand_size      = None
        self._smoothed_hand_size = None
        self._outlier_count      = 0
        self._last_valid_center  = None
        self._last_valid_size    = None
        self._smoothed_center    = None
        self._dy_buffer: list    = []
        self._last_motion_time   = None
        self._pos_100ms          = None
        self._t_100ms            = None
        self._intent_active      = False

    # ------------------------------------------------------------------
    def _valid_detection(self, center, hand_size) -> bool:
        if self._last_valid_center is None:
            return True
        if abs(center[1] - self._last_valid_center[1]) > MAX_POSITION_JUMP:
            return False
        if (hand_size and self._last_valid_size and self._last_valid_size > 0
                and abs(hand_size - self._last_valid_size) / self._last_valid_size > MAX_SIZE_CHANGE):
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