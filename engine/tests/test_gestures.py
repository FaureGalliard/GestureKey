from __future__ import annotations

from gesturekey.actions.types import Hotkey, WindowGrab, WindowMove, WindowRelease
from gesturekey.core.types import HandState

PALM, FIST = HandState.PALM, HandState.FIST


def _release(actions):
    return [a for a in actions if isinstance(a, WindowRelease)]


def test_grab_drag_and_release_in_place(clock):
    clock.run(PALM, 0.3).run(FIST, 0.2)
    assert clock.events == ["GRAB_WINDOW_START"]
    assert any(isinstance(a, WindowGrab) for a in clock.actions)
    assert clock.arbiter.owner == "GRAB_WINDOW"

    clock.run(FIST, 0.3, wrist=(0.5, 0.7), to=(0.55, 0.65))
    moves = [a for a in clock.actions if isinstance(a, WindowMove)]
    assert moves and sum(m.dx for m in moves) > 0.02      # x grows to the user's right

    clock.run(PALM, 0.05, wrist=(0.55, 0.65))
    assert clock.events[-1] == "GRAB_WINDOW_RELEASED"
    assert _release(clock.actions)[-1].snap is None          # stays where it was dropped
    assert clock.arbiter.owner is None


def test_grab_wide_throw_snaps(clock):
    clock.run(PALM, 0.3).run(FIST, 0.2)
    clock.run(FIST, 0.3, wrist=(0.5, 0.7), to=(0.8, 0.7))
    clock.run(PALM, 0.05, wrist=(0.8, 0.7))
    assert _release(clock.actions)[-1].snap == "right"


def test_dragging_down_does_not_close_window(clock):
    clock.run(PALM, 0.3).run(FIST, 0.2)
    clock.run(FIST, 0.1, wrist=(0.5, 0.4), to=(0.5, 0.9))
    assert "CLOSE_WINDOW" not in clock.events


def test_quick_blink_is_mute_not_grab(clock):
    clock.run(PALM, 0.3)
    clock.run(FIST, 1 / 60)   # one stable frame
    clock.run(PALM, 1 / 60)
    assert "MUTE_TOGGLE" in clock.events
    assert "GRAB_WINDOW_START" not in clock.events
    assert any(isinstance(a, Hotkey) and a.keys == ("volume_mute",) for a in clock.actions)


def test_grab_releases_when_hand_lost(clock):
    clock.run(PALM, 0.3).run(FIST, 0.2)
    assert clock.arbiter.owner == "GRAB_WINDOW"
    clock.run(HandState.NO_HANDS, 0.5)
    assert clock.events[-1] == "GRAB_WINDOW_RELEASED"
    assert clock.arbiter.owner is None


def test_screenshot_on_palm_push(clock):
    clock.run(PALM, 0.1, scale=1.0)
    clock.run(PALM, 0.15, scale=1.0, scale_to=0.6)
    assert "SCREENSHOT" in clock.events


def test_steady_palm_takes_no_screenshot(clock):
    clock.run(PALM, 1.0)
    assert "SCREENSHOT" not in clock.events


def test_pause_blocks_other_gestures(clock):
    clock.run(HandState.FOUR_FINGERS, 0.4).run(FIST, 1 / 60)
    assert clock.events == ["PAUSE_TOGGLE_PAUSED"]
    assert clock.arbiter.paused
    clock.run(PALM, 0.3).run(FIST, 0.3)
    assert "GRAB_WINDOW_START" not in clock.events
