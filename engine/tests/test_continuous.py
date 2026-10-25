"""Scroll, volume and zoom: how they start, act, and — above all — end."""
from __future__ import annotations

from conftest import make_frame, make_hand

from gesturekey.actions.types import Hotkey, Scroll, VolumeBegin, VolumeSet
from gesturekey.config import ContinuousConfig, ScrollConfig, StatesConfig, VolumeConfig, ZoomConfig
from gesturekey.core.types import FrameData, Hand, HandState
from gesturekey.gestures.base import Output
from gesturekey.gestures.scroll import ScrollGesture
from gesturekey.gestures.volume import VolumeGesture
from gesturekey.gestures.zoom import PinchZoomGesture
from gesturekey.vision.states import StateFilter

TWO, THREE, PINCH = HandState.TWO_FINGERS, HandState.THREE_FINGERS, HandState.PINCH
FPS = 30


class Driver:
    """Feeds one gesture directly, collecting what it outputs."""

    def __init__(self, gesture, t: float = 0.0) -> None:
        self.g, self.t = gesture, t
        self.actions: list = []

    def run(self, state, seconds, y=0.7, to=None, raw=None, hand=None):
        n = max(1, round(seconds * FPS))
        for i in range(n):
            yy = y if to is None else y + (to - y) * (i + 1) / n
            h = hand(i, n) if hand else make_hand((0.5, yy))
            out = Output()
            self.g.update(FrameData(state=state, hands={"Right": h}, timestamp=self.t, raw_state=raw or state), out)
            self.actions += out.actions
            self.t += 1 / FPS
        return self

    def of(self, kind):
        return [a for a in self.actions if isinstance(a, kind)]


# palm length of make_hand ≈ 0.11 image units (wrist → middle MCP)
PALM = 0.11


# ── states ───────────────────────────────────────────────────────────────────

def _filter():
    return StateFilter(["PALM", "FIST", "FOUR_FINGERS"], StatesConfig())


def test_one_doubtful_frame_does_not_switch_state():
    f, t = _filter(), 0.0
    for _ in range(10):
        f.update({"PALM": 0.9, "FIST": 0.05, "FOUR_FINGERS": 0.05}, t); t += 1 / FPS
    f.update({"PALM": 0.35, "FIST": 0.05, "FOUR_FINGERS": 0.6}, t); t += 1 / FPS
    assert f.current == HandState.PALM


def test_confident_frames_switch_quickly():
    f, t = _filter(), 0.0
    for _ in range(10):
        f.update({"PALM": 0.9, "FIST": 0.05, "FOUR_FINGERS": 0.05}, t); t += 1 / FPS
    frames = 0
    while f.current != HandState.FIST:
        f.update({"PALM": 0.05, "FIST": 0.9, "FOUR_FINGERS": 0.05}, t); t += 1 / FPS
        frames += 1
    assert frames <= 3   # ≤ 100 ms at 30 fps


def test_hand_gone_is_instant():
    f = _filter()
    f.update({"PALM": 0.9, "FIST": 0.05, "FOUR_FINGERS": 0.05}, 0.0)
    assert f.update(None, 0.03) == HandState.NO_HANDS


# ── scroll: joystick ─────────────────────────────────────────────────────────

def _scroll():
    return Driver(ScrollGesture(ScrollConfig(), ContinuousConfig()))


def _wheel(d):
    return sum(a.amount for a in d.of(Scroll))


def test_scroll_inside_deadzone_does_nothing():
    d = _scroll().run(TWO, 0.3).run(TWO, 1.0, y=0.7 + 0.2 * PALM)
    assert _wheel(d) == 0


def test_holding_an_offset_scrolls_at_a_steady_rate():
    d = _scroll().run(TWO, 0.3).run(TWO, 0.2, to=0.7 + 1.0 * PALM)   # hand one palm lower
    before = _wheel(d)
    d.run(TWO, 1.0, y=0.7 + 1.0 * PALM)
    per_second = _wheel(d) - before
    assert per_second < -500                       # scrolls down, steadily
    d2 = _scroll().run(TWO, 0.3).run(TWO, 0.2, to=0.7 + 2.0 * PALM).run(TWO, 1.0, y=0.7 + 2.0 * PALM)
    assert _wheel(d2) < _wheel(d)                  # further from the anchor → faster


def test_back_to_anchor_stops_scrolling():
    d = _scroll().run(TWO, 0.3).run(TWO, 0.3, to=0.7 + PALM).run(TWO, 0.3, y=0.7 + PALM, to=0.7)
    before = _wheel(d)
    d.run(TWO, 1.0, y=0.7)
    assert _wheel(d) == before


def test_dropping_the_hand_ends_scroll_without_a_burst():
    d = _scroll().run(TWO, 0.3)
    assert d.g.engaged
    d.run(TWO, 0.1, y=0.7, to=1.0)                 # fast drop: 3 image units/s
    assert not d.g.engaged
    assert abs(_wheel(d)) < 120                    # at most a notch slipped out


def test_doubt_freezes_then_ends():
    d = _scroll().run(TWO, 0.3).run(TWO, 0.2, to=0.7 + PALM)
    before = _wheel(d)
    d.run(TWO, 0.1, y=0.7 + PALM, raw=HandState.THREE_FINGERS)   # classifier unsure
    assert _wheel(d) == before and d.g.engaged                    # frozen, not ended
    d.run(TWO, 0.1, y=0.7 + PALM, raw=HandState.THREE_FINGERS)
    assert not d.g.engaged                                        # doubt lasted → ended


# ── volume: absolute and forgiving ───────────────────────────────────────────

def _volume():
    return Driver(VolumeGesture(VolumeConfig(), ContinuousConfig()))


def test_volume_up_and_back_returns_to_start():
    d = _volume().run(THREE, 0.3)
    assert d.of(VolumeBegin)
    d.run(THREE, 0.5, to=0.7 - 2 * PALM)            # up two palms
    assert d.of(VolumeSet)[-1].delta > 0.4
    d.run(THREE, 0.5, y=0.7 - 2 * PALM, to=0.7)     # and back
    assert abs(d.of(VolumeSet)[-1].delta) < 0.01


def test_volume_rolls_back_the_drop_to_rest():
    d = _volume().run(THREE, 0.3).run(THREE, 0.4, to=0.7 - PALM).run(THREE, 0.5, y=0.7 - PALM)
    held = d.of(VolumeSet)[-1].delta
    # leaving: hand drifts down a bit while the pose changes
    d.run(THREE, 0.15, y=0.7 - PALM, to=0.7 - 0.4 * PALM).run(HandState.FIST, 0.05, y=0.7 - 0.4 * PALM)
    assert not d.g.engaged
    assert abs(d.of(VolumeSet)[-1].delta - held) < 0.01   # the level held before leaving


# ── zoom: reversible steps ───────────────────────────────────────────────────

def _pinch_hand(gap: float) -> Hand:
    base = make_hand((0.5, 0.7))
    img = list(base.img)
    cx, cy = (img[4][0] + img[8][0]) / 2, (img[4][1] + img[8][1]) / 2
    img[4], img[8] = (cx - gap / 2, cy), (cx + gap / 2, cy)
    return Hand(side="Right", norm=base.norm, img=img, z=base.z)


def _zoom_keys(d):
    return sum(a.times * (1 if a.keys[1] == "plus" else -1) for a in d.of(Hotkey))


def test_zoom_follows_the_pinch_and_is_reversible():
    d = Driver(PinchZoomGesture(ZoomConfig(), ContinuousConfig()))
    d.run(PINCH, 0.3, hand=lambda i, n: _pinch_hand(0.02))
    d.run(PINCH, 0.4, hand=lambda i, n: _pinch_hand(0.02 + 0.04 * (i + 1) / n))   # open ×3
    assert _zoom_keys(d) >= 4
    d.run(TWO, 0.4, hand=lambda i, n: _pinch_hand(0.06 - 0.04 * (i + 1) / n))     # close (pose drifts)
    assert d.g.engaged and _zoom_keys(d) == 0
