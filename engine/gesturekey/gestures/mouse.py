from __future__ import annotations
import math
from collections import deque
from typing import Any, Deque, Dict, Optional, Tuple

from gesturekey.actions.types import CursorBegin, CursorJump, CursorMove, MouseButton
from gesturekey.config import ContinuousConfig, MouseConfig
from gesturekey.core.geometry import dist, palm_center, palm_length
from gesturekey.core.types import GestureEvent, Hand, HandState, Point
from gesturekey.gestures.base import Output
from gesturekey.gestures.continuous import ContinuousGesture

TILT_FRAMES = 2      # consecutive tilted frames before the cursor jumps
TILT_UNDO   = 0.30   # s of cursor motion taken back on a jump (tilting moves the palm a bit)
POINTING_REACH = 1.30   # index tip ↔ wrist (palm lengths) to count as ☝️: fists stay below ~0.95, pointing ~1.96


def pinch_gap(hand: Hand) -> float:
    """Thumb tip ↔ index tip, in palm lengths."""
    return dist(hand.img[4], hand.img[8]) / palm_length(hand)


def index_tilt(hand: Hand) -> float:
    """Degrees the index (knuckle → tip) leans from straight up: + = towards the user's right."""
    (x5, y5), (x8, y8) = hand.img[5], hand.img[8]
    return math.degrees(math.atan2(x8 - x5, -(y8 - y5)))


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
    Pointing *towards a side* (index leaning ≥ `jump_tilt`) jumps the cursor to
    the monitor that way, like opening the hand tilted sends a window there
    (same relative spot on the new monitor). Straighten it to go on pointing.
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
        if self._tilt_jump(hand, now, out):
            return None
        self._move(dx, dy, dt, out)
        return None

    def _tilt_jump(self, hand: Hand, now: float, out: Output) -> bool:
        """True while the index leans to a side: the cursor jumped (or will) and stays put."""
        cfg = self._cfg
        tilt = index_tilt(hand)
        if not self._jump_ready:
            self._jump_ready = abs(tilt) < cfg.rearm_tilt         # straightened: point again
            return not self._jump_ready
        if abs(tilt) < cfg.jump_tilt:
            self._tilted = 0
            return False
        self._tilted += 1
        if self._tilted < TILT_FRAMES:
            return True
        undo = [m for t, m in self._sent if now - t <= TILT_UNDO]  # leaning nudged the cursor
        out.emit(GestureEvent.MOUSE_TO_MONITOR,
                 CursorJump("right" if tilt > 0 else "left",
                            -sum(m[0] for m in undo), -sum(m[1] for m in undo)))
        self._sent.clear()
        self._jump_ready, self._tilted = False, 0
        return True

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
        self._jump_ready = True
        self._tilted = 0
        self._sent: Deque[Tuple[float, Tuple[float, float]]] = deque(maxlen=120)


class MouseGesture(ContinuousGesture):
    """
    ☝️ point with the index → the hand is the mouse (see Pointer). It lasts
    while the hand keeps pointing or pinching; open the hand, show another
    pose or put it down to let go of the cursor.

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
        super().update(frame, out)

    def end(self, now: float, reason: str, out: Output) -> None:
        self.pointer.end(now, out)

    def reset(self) -> None:
        super().reset()
        self._state = HandState.UNKNOWN
