from __future__ import annotations

import pytest

from gesturekey.actions.types import Hotkey, WindowGrab, WindowMove, WindowRelease
from gesturekey.core.types import HandState

PALM, FIST = HandState.PALM, HandState.FIST


def _release(actions):
    return [a for a in actions if isinstance(a, WindowRelease)]


def owner(clock):
    return clock.arbiter.owner.NAME if clock.arbiter.owner else None


def test_grab_drag_and_release_in_place(clock):
    clock.run(PALM, 0.3).run(FIST, 0.2)
    assert clock.events == ["GRAB_WINDOW_START"]
    assert any(isinstance(a, WindowGrab) for a in clock.actions)
    assert owner(clock) == "GRAB_WINDOW"

    clock.run(FIST, 0.3, wrist=(0.5, 0.7), to=(0.55, 0.65))
    moves = [a for a in clock.actions if isinstance(a, WindowMove)]
    assert moves and sum(m.dx for m in moves) > 0.02      # x grows to the user's right

    clock.run(PALM, 0.05, wrist=(0.55, 0.65))
    assert clock.events[-1] == "GRAB_WINDOW_RELEASED"
    assert _release(clock.actions)[-1].snap is None          # stays where it was dropped
    assert owner(clock) is None


def test_grab_wide_throw_snaps(clock):
    clock.run(PALM, 0.3).run(FIST, 0.2)
    clock.run(FIST, 0.15, wrist=(0.5, 0.7), to=(0.8, 0.7))   # a throw: 2 image widths/s
    clock.run(PALM, 0.05, wrist=(0.8, 0.7))
    release = _release(clock.actions)[-1]
    assert release.throw and release.vx > 0 and release.snap is None   # physics decides where it lands


def test_dragging_down_does_not_close_window(clock):
    clock.run(PALM, 0.3).run(FIST, 0.2)
    clock.run(FIST, 0.1, wrist=(0.5, 0.4), to=(0.5, 0.9))
    assert "CLOSE_WINDOW" not in clock.events


def test_quick_blink_is_mute_not_grab():
    from conftest import Clock
    from gesturekey.config import GesturesConfig
    from gesturekey.gestures.arbiter import GestureArbiter
    cfg = GesturesConfig()
    cfg.mute.enabled = True                     # off by default until it moves to 👎
    clock = Clock(GestureArbiter(cfg))
    clock.run(PALM, 0.3)
    clock.run(FIST, 1 / 60)   # one stable frame
    clock.run(PALM, 1 / 60)
    assert "MUTE_TOGGLE" in clock.events
    assert "GRAB_WINDOW_START" not in clock.events
    assert any(isinstance(a, Hotkey) and a.keys == ("volume_mute",) for a in clock.actions)


def test_grab_releases_when_hand_lost(clock):
    clock.run(PALM, 0.3).run(FIST, 0.2)
    assert owner(clock) == "GRAB_WINDOW"
    clock.run(HandState.NO_HANDS, 0.3)
    assert owner(clock) == "GRAB_WINDOW"          # a blur-length loss is tolerated
    clock.run(HandState.NO_HANDS, 0.5)
    assert clock.events[-1] == "GRAB_WINDOW_RELEASED"
    assert owner(clock) is None


def test_screenshot_on_palm_push(clock):
    clock.run(PALM, 0.4, scale=1.0)                            # steady first: armed
    clock.run(PALM, 0.15, scale=1.0, scale_to=0.6)
    assert "SCREENSHOT" in clock.events


def test_steady_palm_takes_no_screenshot(clock):
    clock.run(PALM, 1.0)
    assert "SCREENSHOT" not in clock.events


def test_four_fingers_then_fist_is_media_play_pause(clock):
    clock.run(HandState.FOUR_FINGERS, 0.4).run(FIST, 1 / 60)
    assert clock.events == ["MEDIA_PLAY_PAUSE"]
    assert any(isinstance(a, Hotkey) and a.keys == ("media_play_pause",) for a in clock.actions)


def test_closing_hand_through_four_fingers_is_not_pause(clock):
    # PALM → FIST often passes through a short FOUR_FINGERS
    clock.run(PALM, 0.3).run(HandState.FOUR_FINGERS, 0.15).run(FIST, 0.1)
    assert "MEDIA_PLAY_PAUSE" not in clock.events


# ── power (two palms held still) ───────────────────────────────────────────────

def _two_palms(t, left=(0.3, 0.6), right=(0.7, 0.6)):
    from conftest import make_frame, make_hand
    return make_frame(PALM, t, hands={"Left": make_hand(left, side="Left"), "Right": make_hand(right)})


def _power(hold=1.5):
    from gesturekey.config import PowerConfig
    from gesturekey.gestures.power import PowerToggleGesture
    return PowerToggleGesture(PowerConfig(hold_time=hold))


def _run_power(gesture, seconds, t0=0.0, enabled=True, move=0.0):
    from gesturekey.gestures.base import Output
    events, t, n = [], t0, round(seconds * 60)
    for i in range(n):
        out = Output()
        dx = move * i / n
        gesture.update(_two_palms(t, left=(0.3 + dx, 0.6), right=(0.7 - dx, 0.6)), out, enabled=enabled)
        events += [e.value for e in out.events]
        t += 1 / 60
    return events, t


def test_two_still_palms_toggle_power_once():
    g = _power()
    events, _ = _run_power(g, 1.4)
    assert events == [] and 0.8 < g.progress < 1.0       # ring is filling
    events, _ = _run_power(g, 1.0, t0=1.4)
    assert events == ["POWER_OFF"]                        # fires once, then latches


def test_power_turns_back_on_while_disabled():
    events, _ = _run_power(_power(), 1.6, enabled=False)
    assert events == ["POWER_ON"]


def test_approaching_palms_are_task_view_not_power():
    events, _ = _run_power(_power(), 2.0, move=0.15)      # hands come together
    assert events == []


# ── close window / task view (image space) ────────────────────────────────────

def test_close_window_needs_a_still_fist_then_a_drop():
    clock = _clock_with(lambda cfg: setattr(cfg.close_window, "enabled", True))   # off by default
    clock.run(FIST, 0.4, wrist=(0.5, 0.5))                     # held still → armed
    clock.run(FIST, 0.15, wrist=(0.5, 0.5), to=(0.5, 0.72))    # two palm lengths down, fast
    assert "CLOSE_WINDOW" in clock.events


def test_moving_fist_without_holding_does_not_close():
    clock = _clock_with(lambda cfg: setattr(cfg.close_window, "enabled", True))
    clock.run(FIST, 0.3, wrist=(0.5, 0.3), to=(0.5, 0.9))      # never still
    assert "CLOSE_WINDOW" not in clock.events


def test_task_view_when_palms_come_together():
    from conftest import make_frame, make_hand
    from gesturekey.config import TaskViewConfig
    from gesturekey.core.cooldown import CooldownManager
    from gesturekey.gestures.base import Output
    from gesturekey.gestures.task_view import TaskViewGesture
    g, events, t = TaskViewGesture(CooldownManager(), TaskViewConfig()), [], 0.0
    for i in range(60):                                         # 1 s: hold apart, then approach
        k = max(0.0, (i - 20) / 40)
        left, right = (0.2 + 0.15 * k, 0.6), (0.8 - 0.15 * k, 0.6)
        out = Output()
        g.update(make_frame(PALM, t, hands={"Left": make_hand(left, side="Left"), "Right": make_hand(right)}), out)
        events += [e.value for e in out.events]
        t += 1 / 60
    assert events == ["TASK_VIEW"]


def _clock_with(tweak):
    from conftest import Clock
    from gesturekey.config import GesturesConfig
    from gesturekey.gestures.arbiter import GestureArbiter
    cfg = GesturesConfig()
    tweak(cfg)
    return Clock(GestureArbiter(cfg))


# ── window physics: acceleration and throws ───────────────────────────────────

def test_fast_drag_moves_the_window_further_than_slow(clock):
    from conftest import Clock
    slow = Clock(clock.arbiter.__class__(__import__("gesturekey.config", fromlist=["x"]).GesturesConfig()))
    slow.run(PALM, 0.3, wrist=(0.3, 0.7)).run(FIST, 0.2, wrist=(0.3, 0.7)).run(FIST, 1.0, wrist=(0.3, 0.7), to=(0.5, 0.7))
    fast = Clock(clock.arbiter.__class__(__import__("gesturekey.config", fromlist=["x"]).GesturesConfig()))
    # fast, but below the flick speed (≈ 1.2 image units/s): accelerated drag, not a flick
    fast.run(PALM, 0.3, wrist=(0.3, 0.7)).run(FIST, 0.2, wrist=(0.3, 0.7)).run(FIST, 0.17, wrist=(0.3, 0.7), to=(0.5, 0.7))
    travel = lambda c: sum(a.dx for a in c.actions if isinstance(a, WindowMove))
    assert travel(slow) == pytest.approx(0.2, rel=0.15)      # slow: 1:1
    assert travel(fast) > 1.8 * travel(slow)                 # fast: accelerated


def _grab(clock, at=(0.5, 0.5)):
    clock.run(PALM, 0.3, wrist=at).run(FIST, 0.2, wrist=at)


def test_flick_sideways_sends_the_window_to_the_next_monitor(clock):
    from gesturekey.actions.types import WindowSendTo
    _grab(clock)
    clock.run(FIST, 0.1, wrist=(0.5, 0.5), to=(0.75, 0.5))   # 2.5 image widths/s to the right
    sends = [a for a in clock.actions if isinstance(a, WindowSendTo)]
    assert [a.direction for a in sends] == ["right"]          # once, not once per frame
    assert owner(clock) == "GRAB_WINDOW"                      # still holding: can flick again
    clock.run(FIST, 0.4, wrist=(0.75, 0.5))                   # hand stops…
    clock.run(FIST, 0.1, wrist=(0.75, 0.5), to=(0.5, 0.5))    # …and flicks back
    sends = [a for a in clock.actions if isinstance(a, WindowSendTo)]
    assert [a.direction for a in sends] == ["right", "left"]


def test_flick_up_maximizes(clock):
    from gesturekey.actions.types import WindowSendTo
    _grab(clock, at=(0.5, 0.7))
    clock.run(FIST, 0.1, wrist=(0.5, 0.7), to=(0.5, 0.45))
    assert [a.direction for a in clock.actions if isinstance(a, WindowSendTo)] == ["up"]
    assert "WINDOW_MAXIMIZED" in clock.events


def test_flick_down_then_open_closes(clock):
    _grab(clock, at=(0.5, 0.4))
    clock.run(FIST, 0.1, wrist=(0.5, 0.4), to=(0.5, 0.65))   # fast, downwards: arms closing
    clock.run(PALM, 0.05, wrist=(0.5, 0.65))
    assert _release(clock.actions)[-1].snap == "close"
    assert "CLOSE_WINDOW" in clock.events


def test_dragging_down_calmly_never_closes(clock):
    _grab(clock, at=(0.5, 0.3))
    clock.run(FIST, 1.0, wrist=(0.5, 0.3), to=(0.5, 0.8))    # 0.5 image heights/s
    clock.run(PALM, 0.05, wrist=(0.5, 0.8))
    assert "CLOSE_WINDOW" not in clock.events
    assert _release(clock.actions)[-1].snap is None


def test_flick_down_without_opening_does_not_close(clock):
    _grab(clock, at=(0.5, 0.4))
    clock.run(FIST, 0.1, wrist=(0.5, 0.4), to=(0.5, 0.65))
    clock.run(FIST, 0.8, wrist=(0.5, 0.65))                   # keeps the fist: changed its mind
    clock.run(PALM, 0.05, wrist=(0.5, 0.65))
    assert "CLOSE_WINDOW" not in clock.events


def test_pause_tolerates_a_pose_in_passing(clock):
    clock.run(HandState.FOUR_FINGERS, 0.5).run(HandState.THREE_FINGERS, 1 / 30).run(FIST, 1 / 30)
    assert "MEDIA_PLAY_PAUSE" in clock.events


# ── after a gesture: calm, and the edge push ──────────────────────────────────

def test_putting_the_hand_down_after_a_grab_does_not_grab_again(clock):
    _grab(clock)
    clock.run(PALM, 0.1)                                       # let go…
    assert clock.events.count("GRAB_WINDOW_RELEASED") == 1
    clock.run(PALM, 0.2).run(FIST, 0.3)                        # …lowering the hand: palm → fist
    assert clock.events.count("GRAB_WINDOW_START") == 1        # no second grab
    clock.run(HandState.NO_HANDS, 0.5).run(PALM, 0.3).run(FIST, 0.2)
    assert clock.events.count("GRAB_WINDOW_START") == 2        # a deliberate new grab still works


def test_parking_the_hand_at_the_camera_edge_sends_the_window_on(clock):
    from gesturekey.actions.types import WindowSendTo
    _grab(clock, at=(0.6, 0.5))
    clock.run(FIST, 0.4, wrist=(0.6, 0.5), to=(0.95, 0.5))     # calm drag to the right edge
    clock.run(FIST, 0.4, wrist=(0.95, 0.5))                    # …and wait there
    sends = [a.direction for a in clock.actions if isinstance(a, WindowSendTo)]
    assert sends == ["right"]                                  # once
    clock.run(FIST, 0.5, wrist=(0.95, 0.5))
    assert [a.direction for a in clock.actions if isinstance(a, WindowSendTo)] == ["right"]
    clock.run(FIST, 0.4, wrist=(0.95, 0.5), to=(0.5, 0.5))     # back towards the centre…
    clock.run(FIST, 0.4, wrist=(0.5, 0.5), to=(0.95, 0.5)).run(FIST, 0.4, wrist=(0.95, 0.5))
    assert [a.direction for a in clock.actions if isinstance(a, WindowSendTo)] == ["right", "right"]


# ── the sweep (user's video): fist, then open the hand tilted towards a side ──

def test_opening_the_hand_tilted_left_sends_the_window_left_and_maximizes(clock):
    from gesturekey.actions.types import WindowSendTo
    _grab(clock, at=(0.67, 0.59))
    clock.run(FIST, 0.3, wrist=(0.67, 0.59), to=(0.5, 0.57))       # moving left with the fist
    clock.run(PALM, 0.15, wrist=(0.5, 0.57), tilt=-45)             # hand opens, leaning left
    sends = [a for a in clock.actions if isinstance(a, WindowSendTo)]
    assert [(a.direction, a.release) for a in sends] == [("left", True)]
    assert owner(clock) is None                                    # the grab is over
    clock.run(PALM, 0.4, wrist=(0.68, 0.59))                       # back to upright: nothing new
    assert len([a for a in clock.actions if isinstance(a, WindowSendTo)]) == 1


def test_opening_the_hand_upright_lets_go_in_place(clock):
    from gesturekey.actions.types import WindowSendTo
    _grab(clock)
    clock.run(PALM, 0.15, tilt=-8)                                 # a little lean is still upright
    assert not [a for a in clock.actions if isinstance(a, WindowSendTo)]
    assert _release(clock.actions)[-1].snap is None


def test_sweep_right(clock):
    from gesturekey.actions.types import WindowSendTo
    _grab(clock, at=(0.4, 0.6))
    clock.run(PALM, 0.15, wrist=(0.55, 0.6), tilt=40)
    assert [a.direction for a in clock.actions if isinstance(a, WindowSendTo)] == ["right"]


def test_a_fist_misread_as_pointing_still_grabs(clock):
    clock.run(PALM, 0.3).run(HandState.POINT, 0.2)               # the model says POINT, it's a fist
    assert "GRAB_WINDOW_START" in clock.events


def test_pointing_without_the_palm_first_does_not_grab(clock):
    clock.run(HandState.POINT, 1.0)
    assert "GRAB_WINDOW_START" not in clock.events
