from __future__ import annotations
import math
from collections import deque
from typing import Any, Deque, Dict, Optional, Tuple

from gesturekey.actions.types import CursorBegin, CursorJump, CursorMove, MouseButton
from gesturekey.config import ContinuousConfig, MouseConfig
from gesturekey.core.geometry import dist, hand_tilt, openness, palm_center, palm_length
from gesturekey.core.types import GestureEvent, Hand, HandState, Point
from gesturekey.gestures.base import Output
from gesturekey.gestures.continuous import ContinuousGesture

OPEN_REACH  = 1.30   # openness() above this = an open hand (fist ~0.7, pointing ~1.1, palm ~1.8)
OPEN_FRAMES = 2      # consecutive open-hand frames that agree before deciding
OPEN_DECIDE = 0.25   # s: if they never agree, just let go
JUMP_UNDO   = 0.30   # s of cursor motion taken back on a jump (opening the hand moves the palm)
POINTING_REACH = 1.30   # index tip ↔ wrist (palm lengths) to count as ☝️: fists stay below ~0.95, pointing ~1.96


def pinch_gap(hand: Hand) -> float:
    """Thumb tip ↔ index tip, in palm lengths."""
    return dist(hand.img[4], hand.img[8]) / palm_length(hand)


def index_reach(hand: Hand) -> float:
    """
    Index tip ↔ wrist, in palm lengths. Thumb and index touch in a fist too, so
    the gap alone cannot tell a pinch; how far the index tip is can. Measured on
    the recorded sessions: fist ≤ 0.94 (95 %), closed pinch ~1.07, pointing ~1.96.
    """
    return dist(hand.img[8], hand.img[0]) / palm_length(hand)


class Pointer:
    """
    ☝️ the hand moves the cursor like a touchpad, 🤏 bringing thumb and index
    together clicks. Shared by the mouse gesture and task view.

    The cursor follows the palm, not the fingertip, so the pinch itself does
    not drag it. Pointer ballistics as for windows: slow = precise, fast = far
    (all monitors). Clicks like on a touch screen:
      pinch and let go                 → left click (twice quickly = double click)
      pinch and move                   → drag (left button held)
      pinch held still `right_hold`    → right click
    Corners: the camera's view ends before the screens
    do, so a hand parked at the edge of the view keeps the cursor gliding
    that way, like pushing a joystick.
    """

    def __init__(self, cfg: MouseConfig) -> None:
        self._cfg = cfg
        self.reset()

    @property
    def progress(self) -> Optional[float]:
        """0..1 towards a right click while a still pinch is held."""
        if self._pinch_at is None or self._dragging or self._consumed:
            return None
        return min(1.0, (self._now - self._pinch_at) / self._cfg.right_hold)

    def begin(self, hand: Hand, now: float, out: Output) -> None:
        self.reset()
        self._last, self._now = palm_center(hand), now
        out.actions.append(CursorBegin())

    def update(self, hand: Hand, state: HandState, now: float, out: Output) -> Optional[str]:
        """Feed one frame; returns "click" / "right" when a click was sent, else None."""
        cfg, dt = self._cfg, now - self._now
        self._now = now
        here = palm_center(hand)
        dx, dy = here[0] - self._last[0], here[1] - self._last[1]
        self._last = here

        gap = pinch_gap(hand)
        pinching = self._pinch_at is not None
        closing = gap <= cfg.pinch_on and index_reach(hand) >= cfg.pinch_reach and state != HandState.FIST
        if not pinching:
            self._closing = self._closing + 1 if closing else 0
            if self._closing >= 2:                                # two frames: one bad frame is no click
                self._pinch_at, self._pinch_from, self._consumed = now, here, False
                return None                                       # this frame's motion is the pinch
        if pinching and gap >= cfg.pinch_off:
            return self._let_go(out)

        if pinching and not self._dragging:
            if dist(here, self._pinch_from) / palm_length(hand) >= cfg.drag_start:
                self._dragging = True
                out.emit(GestureEvent.MOUSE_DRAG, MouseButton("left", True))
            elif not self._consumed and now - self._pinch_at >= cfg.right_hold:
                self._consumed = True
                out.emit(GestureEvent.MOUSE_RIGHT_CLICK, MouseButton("right", True), MouseButton("right", False))
                return "right"
            else:
                return None                                       # held still: the cursor stays put
        self._move(dx, dy, dt, out)
        self._edge_glide(here, now, dt, out)
        return None

    def jump(self, direction: str, now: float, out: Output) -> None:
        """Hop to the monitor that way, after taking back the motion of opening the hand."""
        undo = [m for t, m in self._sent if now - t <= JUMP_UNDO]
        out.emit(GestureEvent.MOUSE_TO_MONITOR,
                 CursorJump(direction, -sum(m[0] for m in undo), -sum(m[1] for m in undo)))
        self._sent.clear()

    def _edge_glide(self, here: Point, now: float, dt: float, out: Output) -> None:
        """Hand parked at the edge of the camera's view: keep the cursor going that way."""
        cfg, (x, y) = self._cfg, here
        e = cfg.edge_zone
        sx = 1 if x >= 1 - e else -1 if x <= e else 0
        sy = 1 if y >= 1 - e else -1 if y <= e else 0
        if not (sx or sy):
            self._edge_since, self._edge_ok = None, True
            return
        if not self._edge_ok or dt <= 0:
            return
        self._edge_since = self._edge_since or now
        if now - self._edge_since >= cfg.edge_dwell:
            step = cfg.edge_speed * dt
            out.actions.append(CursorMove(sx * step, sy * step))

    def end(self, now: float, out: Output) -> None:
        """The hand is done: release a drag and undo the moment of putting the hand down."""
        if self._dragging:
            out.actions.append(MouseButton("left", False))
        undo = [m for t, m in self._sent if now - t <= self._cfg.rollback]
        if undo and not self._dragging:
            out.actions.append(CursorMove(-sum(m[0] for m in undo), -sum(m[1] for m in undo)))
        self.reset()

    def _let_go(self, out: Output) -> Optional[str]:
        was = "drag" if self._dragging else None if self._consumed else "click"
        if self._dragging:
            out.actions.append(MouseButton("left", False))
        elif was == "click":
            out.emit(GestureEvent.MOUSE_CLICK, MouseButton("left", True), MouseButton("left", False))
        self._pinch_at, self._dragging = None, False
        self._sent.clear()                                        # a click is not undone later
        return was if was != "drag" else None

    def _move(self, dx: float, dy: float, dt: float, out: Output) -> None:
        cfg = self._cfg
        step = math.hypot(dx, dy)
        if step < cfg.deadzone or dt <= 0:
            return
        gain = min(cfg.max_gain, 1.0 + cfg.accel * max(0.0, step / dt - cfg.accel_from))
        move = (dx * gain, dy * gain)
        self._sent.append((self._now, move))
        out.actions.append(CursorMove(*move))

    def reset(self) -> None:
        self._last: Point = (0.0, 0.0)
        self._now = 0.0
        self._pinch_at: Optional[float] = None
        self._pinch_from: Point = (0.0, 0.0)
        self._dragging = False
        self._consumed = False
        self._closing = 0
        self._edge_since: Optional[float] = None
        self._edge_ok = True
        self._sent: Deque[Tuple[float, Tuple[float, float]]] = deque(maxlen=120)


class MouseGesture(ContinuousGesture):
    """
    ☝️ point with the index → the hand is the mouse (see Pointer). It lasts
    while the hand keeps pointing or pinching. Opening the hand ends it, the
    same way as letting go of a window:
      open it upright             → let go of the cursor where it is
      open it tilted to a side    → the cursor jumps to the monitor that way
    Another pose, or putting the hand down, lets go too.

    Scrolling follows: point at the text on any monitor, then ✌️ — Windows
    scrolls whatever is under the cursor, no click needed.
    """

    NAME = "MOUSE"
    POSE = HandState.POINT
    # a pinching hand reads as PINCH / OTHER, sometimes FIST (index curled to the thumb)
    KEEP = frozenset({HandState.PINCH, HandState.OTHER, HandState.FIST, HandState.UNKNOWN})
    EXIT_ON_SPEED = False

    def __init__(self, cfg: MouseConfig, cc: ContinuousConfig) -> None:
        self.pointer = Pointer(cfg)
        self._sweep_tilt = cfg.sweep_tilt
        super().__init__(cc)

    @property
    def readout(self) -> Optional[Dict[str, Any]]:
        """While a still pinch heads for a right click, how far it got (overlay bar)."""
        p = self.pointer.progress if self._active else None
        return {"hold": round(p, 2)} if p is not None and p >= 0.25 else None

    def begin(self, hand: Hand, now: float, out: Output) -> None:
        self.pointer.begin(hand, now, out)

    def act(self, hand: Hand, now: float, dt: float, out: Output) -> None:
        self.pointer.update(hand, self._state, now, out)

    def update(self, frame, out: Output) -> None:
        self._state = frame.state
        hand = frame.main_hand
        if not self._active and hand is not None and (index_reach(hand) < POINTING_REACH or frame.has_both_hands):
            self.reset()                       # a misread fist (grab's), or two hands (a frame, task view)
            return
        if self._active and hand is not None and (
                frame.state in (HandState.PALM, HandState.FOUR_FINGERS) or openness(hand) >= OPEN_REACH):
            return self._opening(hand, frame.timestamp, out)
        self._votes.clear()
        super().update(frame, out)

    def _opening(self, hand: Hand, now: float, out: Output) -> None:
        """Like letting go of a window: upright = stay, tilted = that monitor. Frames must agree."""
        tilt = hand_tilt(hand)
        vote = ("right" if tilt > 0 else "left") if abs(tilt) >= self._sweep_tilt else "here"
        if not self._votes:
            self._open_since = now
        self._votes.append(vote)
        recent = self._votes[-OPEN_FRAMES:]
        if len(recent) == OPEN_FRAMES and len(set(recent)) == 1:
            if vote != "here":
                self.pointer.jump(vote, now, out)
            return self._finish(now, "open", out)
        if now - self._open_since >= OPEN_DECIDE:
            self._finish(now, "open", out)

    def end(self, now: float, reason: str, out: Output) -> None:
        self.pointer.end(now, out)

    def reset(self) -> None:
        super().reset()
        self._state = HandState.UNKNOWN
        self._votes: list = []
        self._open_since = 0.0
