from __future__ import annotations
from typing import Optional

from gesturekey.actions.types import Hotkey, MouseButton
from gesturekey.config import MouseConfig, TaskViewConfig
from gesturekey.core.cooldown import CooldownManager
from gesturekey.core.geometry import dist, palm_center
from gesturekey.core.types import FrameData, GestureEvent, HandState, Point
from gesturekey.gestures.base import Gesture, Output
from gesturekey.gestures.mouse import POINTING_REACH, Pointer, index_reach

MIN_INITIAL_DISTANCE    = 0.25   # image width fraction; wider and MediaPipe tends to drop a hand
MAX_APPROACH_SPEED      = 0.50
MAX_POSITION_JUMP       = 0.20
OUTLIER_RECOVERY_FRAMES = 2
DISTANCE_ALPHA          = 0.60
STABILITY_FRAMES        = 3


class TaskViewGesture(Gesture):
    """
    ✋✋ two open palms apart, brought together → Win+Tab, and then *drive* it.

    While task view is open the gesture owns the hand:
      ☝️ point                  → the cursor follows (as the mouse gesture)
      🤏 pinch on a window      → it opens (a click), and task view is done
      ✋✋ palms moving apart    → leave: opens the window under the cursor if
                                  you pointed at one, otherwise Esc (back)
    No gesture for `idle_timeout`, or the hand gone for `lost_timeout`, and it
    stops driving (task view stays as it is).

    Distances are in image space (v2 compared each hand centre relative to
    its own wrist, so the distance between hands was meaningless).
    """

    NAME = "TASK_VIEW"

    #: while the pointer is on, these keep it (a pinching hand reads as any of them)
    POINTING = frozenset({HandState.POINT, HandState.PINCH, HandState.OTHER, HandState.UNKNOWN})

    def __init__(self, cooldown: CooldownManager, cfg: TaskViewConfig, mouse: MouseConfig) -> None:
        self._cooldown           = cooldown
        self._arm_time           = cfg.arm_time
        self._min_approach       = cfg.min_approach
        self._task_view_cooldown = cfg.cooldown
        self._last_activation    = float("-inf")
        self._pointer            = Pointer(mouse)
        self._idle_timeout       = cfg.idle_timeout
        self._lost_timeout       = cfg.lost_timeout
        self.reset()

    @property
    def engaged(self) -> bool:
        return self._mode

    def update(self, frame: FrameData, out: Output) -> None:
        now = frame.timestamp
        if self._mode:
            return self._drive(frame, out)
        if not frame.has_both_hands or frame.state != HandState.PALM:
            self._reset_opening()
            return

        center_left  = palm_center(frame.hands["Left"])     # image space: real distance between hands
        center_right = palm_center(frame.hands["Right"])
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
                    self._reset_opening()
                return

            if self._stable_count < STABILITY_FRAMES:
                return

            if self._both_start is None:
                self._both_start    = now
                self._initial_dist  = distance_raw
                self._prev_dist_raw = distance_raw
                return

            if self._initial_dist is not None and self._initial_dist < MIN_INITIAL_DISTANCE:
                self._reset_opening()
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
                self._reset_opening()
                self._mode, self._last_activity = True, now      # now drive it
                return

        self._prev_dist_raw = distance_raw

    # ── driving task view ────────────────────────────────────────────────────

    def _drive(self, frame: FrameData, out: Output) -> None:
        now = frame.timestamp
        self._lost_since = None
        if now - self._last_activity > self._idle_timeout:
            return self._leave(out)

        # ✋✋ moving apart: the reverse of opening → leave
        if frame.has_both_hands and frame.state == HandState.PALM:
            self._stop_pointing(now, out)
            gap = dist(palm_center(frame.hands["Left"]), palm_center(frame.hands["Right"]))
            if self._apart_from is None or gap < self._apart_from:
                self._apart_from = gap                     # closest so far
            elif gap - self._apart_from >= self._min_approach:
                if self._pointed:                          # open what the cursor is on
                    out.emit(GestureEvent.TASK_VIEW_OPEN, MouseButton("left", True), MouseButton("left", False))
                else:
                    out.emit(GestureEvent.TASK_VIEW_CLOSED, Hotkey(("esc",)))
                return self._leave(out)
            return
        self._apart_from = None

        hand = frame.main_hand
        if hand is None:
            return
        starting = frame.state == HandState.POINT and index_reach(hand) >= POINTING_REACH
        if self._pointing and frame.state in self.POINTING or starting:
            if not self._pointing:
                self._pointer.begin(hand, now, out)
                self._pointing = self._pointed = True
            self._last_activity = now
            if self._pointer.update(hand, frame.state, now, out) == "click":
                return self._leave(out)                    # a window was clicked: Windows opens it
        else:
            self._stop_pointing(now, out)

    def _stop_pointing(self, now: float, out: Output) -> None:
        if self._pointing:
            self._pointer.end(now, out)
            self._pointing = False

    def on_lost(self, now: float, out: Output) -> None:
        if not self._mode:
            return
        self._lost_since = self._lost_since or now
        if now - self._lost_since > self._lost_timeout:
            self._leave(out)

    def _leave(self, out: Output) -> None:
        if self._pointing:
            self._pointer.end(self._last_activity, out)
        self.reset()

    def reset(self) -> None:
        self._reset_opening()
        self._mode = False
        self._last_activity = 0.0
        self._lost_since: Optional[float] = None
        self._apart_from: Optional[float] = None
        self._pointing = False      # the pointer is on right now
        self._pointed = False       # it was used this time (palms apart then open what it is on)
        self._pointer.reset()

    def _reset_opening(self) -> None:
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
