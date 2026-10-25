from __future__ import annotations
from typing import Optional

from gesturekey.actions.types import WindowGrab, WindowMove, WindowRelease
from gesturekey.config import GrabWindowConfig
from gesturekey.core.cooldown import CooldownManager
from gesturekey.core.filters import PointFilter
from gesturekey.core.types import FrameData, GestureEvent, HandState, Point
from gesturekey.gestures.base import Gesture, Output


class _Phase:
    IDLE    = "IDLE"
    ARMING  = "ARMING"    # PALM shown, waiting min_arm_time
    HOLDING = "HOLDING"   # FIST shown, waiting hold_time (a quick blink is MUTE)
    GRABBED = "GRABBED"   # dragging — owns the hand


class GrabWindowGesture(Gesture):
    """
    PALM (≥ min_arm_time) → FIST (≥ hold_time) : grab the foreground window
    FIST + move                                : drag it (filtered wrist)
    FIST → PALM                                : release where it is, or
                                                 snap left/right on a wide
                                                 throw, maximize on an upward one
    hand lost ≥ lost_timeout                   : release in place
    """

    NAME = "GRAB_WINDOW"

    def __init__(self, cooldown: CooldownManager, cfg: GrabWindowConfig) -> None:
        self._cooldown = cooldown
        self._cfg      = cfg
        self._filter   = PointFilter(min_cutoff=1.2, beta=8.0)
        self.reset()

    @property
    def engaged(self) -> bool:
        return self._phase == _Phase.GRABBED

    def update(self, frame: FrameData, out: Output) -> None:
        hand, state, now = frame.main_hand, frame.state, frame.timestamp
        cfg = self._cfg
        if hand is None:
            return
        wrist = self._filter(hand.wrist, now)

        if self._phase == _Phase.IDLE:
            if state == HandState.PALM:
                self._phase, self._arm_start = _Phase.ARMING, now

        elif self._phase == _Phase.ARMING:
            if state == HandState.FIST:
                if now - self._arm_start >= cfg.min_arm_time:
                    self._phase, self._fist_start = _Phase.HOLDING, now
                else:
                    self._phase = _Phase.IDLE
            elif state != HandState.PALM:
                self._phase = _Phase.IDLE

        elif self._phase == _Phase.HOLDING:
            if state == HandState.FIST:
                if now - self._fist_start >= cfg.hold_time and self._cooldown.ok(self.NAME, now, cfg.cooldown):
                    self._phase      = _Phase.GRABBED
                    self._origin     = wrist
                    self._last       = wrist
                    self._last_seen  = now
                    out.emit(GestureEvent.GRAB_WINDOW_START, WindowGrab())
            elif state == HandState.PALM:
                self._phase = _Phase.ARMING          # still armed; try again
            else:
                self._phase = _Phase.IDLE

        elif self._phase == _Phase.GRABBED:
            if state == HandState.FIST:
                self._last_seen = now
                if self._last is not None:
                    dx, dy = wrist[0] - self._last[0], wrist[1] - self._last[1]
                    if abs(dx) > cfg.deadzone or abs(dy) > cfg.deadzone:
                        out.actions.append(WindowMove(dx, dy))
                        self._last = wrist
            elif state == HandState.PALM:
                self._release(out, self._snap_for(wrist))
            elif now - self._last_seen > cfg.lost_timeout:
                self._release(out, None)             # misclassified too long

    def on_lost(self, now: float, out: Output) -> None:
        if self._phase == _Phase.GRABBED and now - self._last_seen > self._cfg.lost_timeout:
            self._release(out, None)

    def _snap_for(self, wrist: Point):
        if self._origin is None:
            return None
        dx, dy = wrist[0] - self._origin[0], wrist[1] - self._origin[1]
        thr = self._cfg.snap_threshold
        if abs(dx) > thr and abs(dx) >= abs(dy):
            return "right" if dx > 0 else "left"
        if dy < -thr:
            return "maximize"
        return None

    def _release(self, out: Output, snap) -> None:
        out.emit(GestureEvent.GRAB_WINDOW_RELEASED, WindowRelease(snap))
        self.reset()

    def reset(self) -> None:
        self._phase:      str             = _Phase.IDLE
        self._arm_start:  float           = 0.0
        self._fist_start: float           = 0.0
        self._origin:     Optional[Point] = None
        self._last:       Optional[Point] = None
        self._last_seen:  float           = 0.0
        self._filter.reset()
