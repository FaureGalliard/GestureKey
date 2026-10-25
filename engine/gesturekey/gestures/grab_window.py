from __future__ import annotations
import math
from collections import deque
from typing import Deque, Optional, Tuple

from gesturekey.actions.types import WindowGrab, WindowMove, WindowRelease
from gesturekey.config import GrabWindowConfig
from gesturekey.core.cooldown import CooldownManager
from gesturekey.core.types import FrameData, GestureEvent, HandState, Point
from gesturekey.gestures.base import Gesture, Output

THROW_WINDOW = 0.15   # seconds of motion before the release that define the throw
THROW_SPAN   = 0.05   # velocity is measured over spans this long, and the peak wins


class _Phase:
    IDLE    = "IDLE"
    ARMING  = "ARMING"    # PALM shown, waiting min_arm_time
    HOLDING = "HOLDING"   # FIST shown, waiting hold_time
    GRABBED = "GRABBED"   # dragging — owns the hand


class GrabWindowGesture(Gesture):
    """
    PALM (≥ min_arm_time) → FIST (≥ hold_time) : grab the foreground window
    FIST + move                                : drag it
    FIST → PALM                                : release where it is — or, if the
                                                 hand was thrown fast, snap to that
                                                 side, maximize (up) or close (down)

    Drag uses pointer-style acceleration: slow moves are 1:1 with one screen,
    fast moves go further, so a window crosses several monitors without the
    camera having to see the whole desktop.
    fist lost ≥ lost_timeout                   : release in place

    Landmarks arrive already smoothed by the tracker. Fast moves blur the fist
    and the classifier briefly loses it, so only a clear PALM releases at
    once; anything else is tolerated for `lost_timeout`.
    """

    NAME = "GRAB_WINDOW"

    def __init__(self, cooldown: CooldownManager, cfg: GrabWindowConfig) -> None:
        self._cooldown = cooldown
        self._cfg      = cfg
        self.reset()

    @property
    def engaged(self) -> bool:
        return self._phase == _Phase.GRABBED

    def update(self, frame: FrameData, out: Output) -> None:
        hand, state, now = frame.main_hand, frame.state, frame.timestamp
        cfg = self._cfg
        if hand is None:
            return self.on_lost(now, out)
        wrist = hand.wrist

        if self._phase == _Phase.IDLE:
            if state == HandState.PALM:
                self._phase, self._arm_start = _Phase.ARMING, now

        elif self._phase == _Phase.ARMING:
            if state == HandState.FIST:
                if now - self._arm_start >= cfg.min_arm_time:
                    self._phase, self._fist_start = _Phase.HOLDING, now
                else:
                    self._phase = _Phase.IDLE
            elif state not in (HandState.PALM, HandState.FOUR_FINGERS):   # closing hand passes through four
                self._phase = _Phase.IDLE

        elif self._phase == _Phase.HOLDING:
            if state == HandState.FIST:
                if now - self._fist_start >= cfg.hold_time and self._cooldown.ok(self.NAME, now, cfg.cooldown):
                    self._phase     = _Phase.GRABBED
                    self._last      = wrist
                    self._last_t    = now
                    self._last_seen = now
                    self._trail.clear()
                    out.emit(GestureEvent.GRAB_WINDOW_START, WindowGrab())
            elif state == HandState.PALM:
                self._phase = _Phase.ARMING
            elif state != HandState.FOUR_FINGERS:
                self._phase = _Phase.IDLE

        elif self._phase == _Phase.GRABBED:
            self._trail.append((now, wrist))
            if state == HandState.PALM:
                return self._release(out, self._throw(now))
            if state == HandState.FIST:
                self._last_seen = now
            elif now - self._last_seen > cfg.lost_timeout:
                return self._release(out, None)
            # keep following the wrist even through a blurred frame
            if self._last is not None:
                dx, dy = wrist[0] - self._last[0], wrist[1] - self._last[1]
                if abs(dx) > cfg.deadzone or abs(dy) > cfg.deadzone:
                    gain = self._gain(math.hypot(dx, dy), now - self._last_t)
                    out.actions.append(WindowMove(dx * gain, dy * gain))
                    self._last, self._last_t = wrist, now

    def on_lost(self, now: float, out: Output) -> None:
        if self._phase == _Phase.GRABBED:
            if now - self._last_seen > self._cfg.lost_timeout:
                self._release(out, None)
        elif self._phase != _Phase.IDLE:
            self.reset()

    def _throw(self, now: float):
        """
        Peak velocity in the moments before the hand opened decides a snap.
        Peak, not average: the still frames before the throw and while the
        palm opens would otherwise dilute it.
        """
        recent = [(t, p) for t, p in self._trail if now - t <= THROW_WINDOW + 0.1]
        best, vx, vy = 0.0, 0.0, 0.0
        for i, (t0, p0) in enumerate(recent):
            for t1, p1 in recent[i + 1:]:
                if t1 - t0 >= THROW_SPAN:              # ~3 frames: smooth, still short
                    wx, wy = (p1[0] - p0[0]) / (t1 - t0), (p1[1] - p0[1]) / (t1 - t0)
                    if wx * wx + wy * wy > best:
                        best, vx, vy = wx * wx + wy * wy, wx, wy
                    break
        if best == 0.0:
            return None
        fast = self._cfg.throw_speed
        if abs(vx) >= fast and abs(vx) >= abs(vy):
            return "right" if vx > 0 else "left"
        if vy <= -fast:
            return "maximize"
        if vy >= self._cfg.close_speed and vy >= abs(vx):
            return "close"                       # thrown away downwards
        return None

    def _gain(self, step: float, dt: float) -> float:
        """Pointer ballistics: slow = precise 1:1, fast = covers more screen (multi-monitor)."""
        if dt <= 0:
            return 1.0
        cfg = self._cfg
        speed = step / dt
        return min(cfg.max_gain, 1.0 + cfg.accel * max(0.0, speed - cfg.accel_from))

    def _release(self, out: Output, snap) -> None:
        event = GestureEvent.CLOSE_WINDOW if snap == "close" else GestureEvent.GRAB_WINDOW_RELEASED
        out.emit(event, WindowRelease(snap))
        self.reset()

    def reset(self) -> None:
        self._phase:      str             = _Phase.IDLE
        self._arm_start:  float           = 0.0
        self._fist_start: float           = 0.0
        self._last:       Optional[Point] = None
        self._last_t:     float           = 0.0
        self._last_seen:  float           = 0.0
        self._trail: Deque[Tuple[float, Point]] = deque(maxlen=30)
