from __future__ import annotations
import math
from collections import deque
from typing import Deque, Optional, Tuple

from gesturekey.actions.types import WindowGrab, WindowMove, WindowRelease, WindowSendTo
from gesturekey.config import GrabWindowConfig
from gesturekey.core.cooldown import CooldownManager
from gesturekey.core.geometry import palm_center
from gesturekey.core.types import FrameData, GestureEvent, HandState, Point
from gesturekey.gestures.base import Gesture, Output

THROW_WINDOW = 0.15   # seconds of motion before the release that define the throw
THROW_SPAN   = 0.05   # velocity is measured over spans this long, and the peak wins
DOMINANCE    = 1.5    # a flick's main axis must be this much faster than the other
FLICK_BLOCK  = 0.35   # s: after a flick, the rest of that same motion does not drag
CLOSE_WINDOW = 0.5    # s: after a downward flick, opening the hand this soon closes
OPEN_FRAMES  = 2      # consecutive open-hand frames that agree before deciding
OPEN_DECIDE  = 0.25   # s: if they never agree, just let go


class _Phase:
    IDLE    = "IDLE"
    ARMING  = "ARMING"    # PALM shown, waiting min_arm_time
    HOLDING = "HOLDING"   # FIST shown, waiting hold_time
    GRABBED = "GRABBED"   # dragging — owns the hand


class GrabWindowGesture(Gesture):
    """
    PALM (≥ min_arm_time) → FIST (≥ hold_time) : grab the foreground window
    FIST + move                                : drag it (pointer acceleration)
    open the hand tilted sideways (a sweep)    : send it to the monitor that way and
                                                 maximize it there — the natural way to
                                                 say "over there"; upright = let go here
    hand held at the camera's left/right edge  : "keep going that way" → next monitor
                                                 (like dragging a mouse past the screen edge)
    flick → / ← while holding                  : send it to the next monitor that way
                                                 (at the desktop edge: snap to that half)
    flick ↑ while holding                      : maximize
    flick ↓, then open the hand within 0.5 s   : close
    FIST → PALM                                : release where it is
    fist lost ≥ lost_timeout                   : release in place

    Flicks are detected *while* holding, every frame, from the last ~50 ms of
    motion. Judging them at release missed them: the hand slows down as it
    opens and the open palm is confirmed a few frames later, after the peak.

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
        # Once the palm has armed a grab, a "pointing" hand is almost surely a fist the
        # 2D features misread (loose index): count it as one. POINT stays free otherwise.
        fist = state == HandState.FIST or (state == HandState.POINT and self._phase != _Phase.IDLE)

        if self._phase == _Phase.IDLE:
            if state == HandState.PALM:
                self._phase, self._arm_start = _Phase.ARMING, now

        elif self._phase == _Phase.ARMING:
            if fist:
                if now - self._arm_start >= cfg.min_arm_time:
                    self._phase, self._fist_start = _Phase.HOLDING, now
                else:
                    self._phase = _Phase.IDLE
            elif state not in (HandState.PALM, HandState.FOUR_FINGERS):   # closing hand passes through four
                self._phase = _Phase.IDLE

        elif self._phase == _Phase.HOLDING:
            if fist:
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
            if state in (HandState.PALM, HandState.FOUR_FINGERS):
                return self._opening(hand, now, out)
            self._open_votes.clear()
            if fist:
                self._last_seen = now
            elif now - self._last_seen > cfg.lost_timeout:
                return self._drop(out)
            if self._flick(now, out):
                return
            self._edge_push(hand, now, out)
            if now < self._block_until:              # still inside a flick: do not drag with it
                self._last, self._last_t = wrist, now
                return
            # keep following the wrist even through a blurred frame
            if self._last is not None:
                dx, dy = wrist[0] - self._last[0], wrist[1] - self._last[1]
                if abs(dx) > cfg.deadzone or abs(dy) > cfg.deadzone:
                    gain = self._gain(math.hypot(dx, dy), now - self._last_t)
                    out.actions.append(WindowMove(dx * gain, dy * gain))
                    self._last, self._last_t = wrist, now

    def _velocity(self, now: float) -> Tuple[float, float]:
        """Wrist velocity (image units/s) over the last ~THROW_SPAN."""
        last_t, last_p = self._trail[-1]
        for t, p in reversed(self._trail):
            if last_t - t >= THROW_SPAN:
                return (last_p[0] - p[0]) / (last_t - t), (last_p[1] - p[1]) / (last_t - t)
        return 0.0, 0.0

    def _opening(self, hand, now: float, out: Output) -> None:
        """
        The hand opened. Upright = let go here; tilted sideways = a sweep towards
        that side. A couple of frames must agree, since the first open frames
        are often mid-transition.
        """
        if now <= self._close_until:
            return self._let_go(now, out)                 # flicked down then opened: close
        (x0, y0), (x9, y9) = hand.img[0], hand.img[9]
        tilt = math.degrees(math.atan2(x9 - x0, -(y9 - y0)))   # 0 = fingers up, + = towards the user's right
        vote = ("right" if tilt > 0 else "left") if abs(tilt) >= self._cfg.sweep_tilt else "here"
        if not self._open_votes:
            self._open_since = now
        self._open_votes.append(vote)
        recent = self._open_votes[-OPEN_FRAMES:]
        if len(recent) == OPEN_FRAMES and len(set(recent)) == 1:
            if vote == "here":
                return self._let_go(now, out)
            out.emit(GestureEvent.WINDOW_TO_MONITOR,
                     WindowSendTo(vote, release=self._cfg.maximize_on_move))
            if not self._cfg.maximize_on_move:
                out.emit(GestureEvent.GRAB_WINDOW_RELEASED, WindowRelease())
            return self.reset()
        if now - self._open_since >= OPEN_DECIDE:
            return self._let_go(now, out)

    def _edge_push(self, hand, now: float, out: Output) -> None:
        """Hand parked at the edge of the camera's view: the user wants to go beyond it."""
        cfg = self._cfg
        x = palm_center(hand)[0]
        side = "right" if x >= 1 - cfg.edge_zone else "left" if x <= cfg.edge_zone else None
        if side is None:
            self._edge_since = None
            if 1.5 * cfg.edge_zone < x < 1 - 1.5 * cfg.edge_zone:
                self._edge_ready = True                  # came back inwards: may push again
            return
        if not self._edge_ready:
            return
        if self._edge_since is None or self._edge_side != side:
            self._edge_since, self._edge_side = now, side
        elif now - self._edge_since >= cfg.edge_dwell:
            out.emit(GestureEvent.WINDOW_TO_MONITOR, WindowSendTo(side))
            self._edge_ready, self._edge_since = False, None

    def _flick(self, now: float, out: Output) -> bool:
        """Returns True when the grab ended because of the flick."""
        cfg = self._cfg
        vx, vy = self._velocity(now)
        speed = math.hypot(vx, vy)
        if not self._flick_ready:
            self._flick_ready = speed < 0.5 * cfg.flick_speed     # the previous flick is over
            return False
        if abs(vx) >= cfg.flick_speed and abs(vx) >= DOMINANCE * abs(vy):
            out.emit(GestureEvent.WINDOW_TO_MONITOR, WindowSendTo("right" if vx > 0 else "left"))
        elif vy <= -cfg.flick_speed and abs(vy) >= DOMINANCE * abs(vx):
            out.emit(GestureEvent.WINDOW_MAXIMIZED, WindowSendTo("up"))
            self.reset()                              # maximized: nothing left to drag
            return True
        elif vy >= cfg.close_speed and vy >= DOMINANCE * abs(vx):
            self._close_until = now + CLOSE_WINDOW    # armed; opening the hand now closes
        else:
            return False
        self._flick_ready = False
        self._block_until = now + FLICK_BLOCK
        return False

    def on_lost(self, now: float, out: Output) -> None:
        if self._phase == _Phase.GRABBED:
            if now - self._last_seen > self._cfg.lost_timeout:
                self._drop(out)
        elif self._phase != _Phase.IDLE:
            self.reset()

    def _throw(self, now: float) -> Tuple[float, float]:
        """
        Peak velocity (image units/s) in the moments before the hand opened.
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
        return vx, vy

    def _let_go(self, now: float, out: Output) -> None:
        if now <= self._close_until:                  # flicked down, then opened: throw it away
            out.emit(GestureEvent.CLOSE_WINDOW, WindowRelease("close"))
            return self.reset()
        vx, vy = self._throw(now)
        speed = math.hypot(vx, vy)
        # a small glide with the release velocity; the window physics also maximizes
        # a window that was dragged into the top of a monitor
        gain = self._gain(speed, 1.0)
        out.emit(GestureEvent.GRAB_WINDOW_RELEASED,
                 WindowRelease(None, vx * gain, vy * gain, throw=speed >= self._cfg.throw_speed))
        self.reset()

    def _gain(self, step: float, dt: float) -> float:
        """Pointer ballistics: slow = precise 1:1, fast = covers more screen (multi-monitor)."""
        if dt <= 0:
            return 1.0
        cfg = self._cfg
        speed = step / dt
        return min(cfg.max_gain, 1.0 + cfg.accel * max(0.0, speed - cfg.accel_from))

    def _drop(self, out: Output) -> None:
        """Fist lost for too long: let go where it is, no glide."""
        out.emit(GestureEvent.GRAB_WINDOW_RELEASED, WindowRelease())
        self.reset()

    def reset(self) -> None:
        self._phase:      str             = _Phase.IDLE
        self._arm_start:  float           = 0.0
        self._fist_start: float           = 0.0
        self._last:       Optional[Point] = None
        self._last_t:     float           = 0.0
        self._last_seen:  float           = 0.0
        self._trail: Deque[Tuple[float, Point]] = deque(maxlen=30)
        self._flick_ready = True
        self._open_votes: list = []
        self._open_since = 0.0
        self._edge_ready = True
        self._edge_since: Optional[float] = None
        self._edge_side = ""
        self._block_until = 0.0
        self._close_until = float("-inf")
