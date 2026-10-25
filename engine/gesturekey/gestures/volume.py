from __future__ import annotations
from typing import List, Optional

from gesturekey.actions.types import Hotkey
from gesturekey.config import VolumeConfig
from gesturekey.core.geometry import hand_center, hand_size_3d, relative_depth
from gesturekey.core.types import FrameData, GestureEvent, HandState, Hand, Point
from gesturekey.gestures.base import Gesture, Output

BASE_GAIN               = 100
ACCEL_FACTOR            = 200
MAX_VOLUME_STEP         = 30
MIN_VOLUME_STEP         = 1

SIZE_COMPENSATION       = True
SIZE_RATIO_MIN          = 0.7
SIZE_RATIO_MAX          = 1.4
SIZE_ALPHA              = 0.6
POSITION_ALPHA          = 0.7
MAX_POSITION_JUMP       = 0.15
MAX_SIZE_CHANGE         = 0.30
OUTLIER_RECOVERY_FRAMES = 2

VELOCITY_DEADZONE       = 0.0025
TEMPORAL_FRAMES         = 3
MOTION_THRESHOLD        = 0.0035
STILLNESS_TIMEOUT       = 0.1

INTENT_Z_ENTER          = -0.045
INTENT_Z_EXIT           = -0.005


class VolumeGesture(Gesture):
    """THREE_FINGERS pointing at the camera, then move up/down."""

    NAME = "VOLUME"

    def __init__(self, cfg: VolumeConfig) -> None:
        self._arm_time = cfg.arm_time
        self.reset()

    @property
    def engaged(self) -> bool:
        return self._active

    def update(self, frame: FrameData, out: Output) -> None:
        hand = frame.main_hand
        if frame.state != HandState.THREE_FINGERS or hand is None:
            self.reset()
            return

        now        = frame.timestamp
        center_raw = hand_center(hand.norm)
        hand_size  = hand_size_3d(hand)

        if self._smoothed_hand_size is None:
            self._smoothed_hand_size = hand_size
        else:
            self._smoothed_hand_size = SIZE_ALPHA * hand_size + (1 - SIZE_ALPHA) * self._smoothed_hand_size

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
                return
            self._outlier_count     = 0
            self._last_valid_center = self._smoothed_center
            self._last_valid_size   = self._smoothed_hand_size

        if not self._depth_intent_ok(hand):
            self.reset()
            return

        if not self._active:
            if self._start_time is None:
                self._start_time      = now
                self._prev_center_raw = center_raw
                self._anchor_y        = center_raw[1]
                self._ref_hand_size   = self._smoothed_hand_size
                return
            if now - self._start_time < self._arm_time:
                self._prev_center_raw = center_raw
                return
            self._active = True

        if self._prev_center_raw is not None:
            dy_raw = center_raw[1] - self._prev_center_raw[1]

            if SIZE_COMPENSATION and self._smoothed_hand_size and self._ref_hand_size:
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
                return

            if self._pos_100ms is None or self._t_100ms is None:
                self._pos_100ms, self._t_100ms = center_raw[1], now
            elif now - self._t_100ms >= 0.1:
                if abs(center_raw[1] - self._pos_100ms) < MOTION_THRESHOLD:
                    self._prev_center_raw = center_raw
                    return
                self._pos_100ms, self._t_100ms = center_raw[1], now

            if dy != 0.0:
                self._dy_buffer.append(dy)
                if len(self._dy_buffer) > TEMPORAL_FRAMES:
                    self._dy_buffer.pop(0)
            if len(self._dy_buffer) < TEMPORAL_FRAMES:
                self._prev_center_raw = center_raw
                return

            dy_eff = sum(self._dy_buffer) / len(self._dy_buffer)
            gain   = BASE_GAIN + abs(center_raw[1] - self._anchor_y) * ACCEL_FACTOR
            steps  = int(dy_eff * gain)

            if abs(steps) >= MIN_VOLUME_STEP:
                steps = min(MAX_VOLUME_STEP, abs(steps))
                if dy_eff < 0:
                    out.emit(GestureEvent.VOLUME_UP, Hotkey(("volume_up",), times=steps))
                else:
                    out.emit(GestureEvent.VOLUME_DOWN, Hotkey(("volume_down",), times=steps))

        self._prev_center_raw = center_raw

    def reset(self) -> None:
        self._prev_center_raw:    Optional[Point] = None
        self._active:             bool            = False
        self._start_time:         Optional[float] = None
        self._anchor_y:           float           = 0.0
        self._ref_hand_size:      Optional[float] = None
        self._smoothed_hand_size: Optional[float] = None
        self._outlier_count:      int             = 0
        self._last_valid_center:  Optional[Point] = None
        self._last_valid_size:    Optional[float] = None
        self._smoothed_center:    Optional[Point] = None
        self._dy_buffer:          List[float]     = []
        self._last_motion_time:   Optional[float] = None
        self._pos_100ms:          Optional[float] = None
        self._t_100ms:            Optional[float] = None
        self._intent_active:      bool            = False

    def _valid_detection(self, center: Point, hand_size: Optional[float]) -> bool:
        if self._last_valid_center is None:
            return True
        if abs(center[1] - self._last_valid_center[1]) > MAX_POSITION_JUMP:
            return False
        if (hand_size and self._last_valid_size
                and abs(hand_size - self._last_valid_size) / self._last_valid_size > MAX_SIZE_CHANGE):
            return False
        return True

    def _depth_intent_ok(self, hand: Hand) -> bool:
        depth = relative_depth(hand)
        if not self._intent_active:
            if depth < INTENT_Z_ENTER:
                self._intent_active = True
        elif depth > INTENT_Z_EXIT:
            self._intent_active = False
        return self._intent_active
