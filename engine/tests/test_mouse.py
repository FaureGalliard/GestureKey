from __future__ import annotations

from gesturekey.actions.types import CursorBegin, CursorMove, MouseButton
from gesturekey.core.types import HandState

POINT, PINCH, FIST, PALM = HandState.POINT, HandState.PINCH, HandState.FIST, HandState.PALM


def _point(clock, seconds=0.2, **kw):
    return clock.run(POINT, seconds, pose="point", **kw)


def _buttons(clock):
    return [(a.button, a.down) for a in clock.actions if isinstance(a, MouseButton)]


def _moved(clock):
    moves = [a for a in clock.actions if isinstance(a, CursorMove)]
    return sum(m.dx for m in moves), sum(m.dy for m in moves)


def test_pointing_moves_the_cursor(clock):
    _point(clock)
    _point(clock, 0.3, wrist=(0.5, 0.7), to=(0.6, 0.65))
    assert clock.arbiter.owner.NAME == "MOUSE"
    assert any(isinstance(a, CursorBegin) for a in clock.actions)
    dx, dy = _moved(clock)
    assert dx > 0.1 and dy < 0


def test_pinch_and_let_go_clicks_where_the_cursor_is(clock):
    _point(clock, 0.3)
    before = len(clock.actions)
    clock.run(PINCH, 0.15, pose="pinch").run(POINT, 0.1, pose="point")
    assert _buttons(clock) == [("left", True), ("left", False)]
    assert "MOUSE_CLICK" in clock.events
    assert not [a for a in clock.actions[before:] if isinstance(a, CursorMove)]


def test_pinch_and_move_drags(clock):
    _point(clock, 0.3)
    clock.run(PINCH, 0.1, pose="pinch")
    clock.run(PINCH, 0.3, pose="pinch", wrist=(0.5, 0.7), to=(0.6, 0.7))
    clock.run(POINT, 0.1, pose="point", wrist=(0.6, 0.7))
    assert _buttons(clock) == [("left", True), ("left", False)]
    assert "MOUSE_DRAG" in clock.events and "MOUSE_CLICK" not in clock.events


def test_still_pinch_is_a_right_click(clock):
    _point(clock, 0.3)
    clock.run(PINCH, 0.9, pose="pinch").run(POINT, 0.1, pose="point")
    assert _buttons(clock) == [("right", True), ("right", False)]


def test_a_fist_while_pointing_never_clicks(clock):
    _point(clock, 0.3)
    clock.run(FIST, 0.3, pose="fist")
    assert _buttons(clock) == []


def test_opening_the_hand_lets_go_of_the_cursor(clock):
    _point(clock, 0.3)
    clock.run(PALM, 0.1)
    assert clock.arbiter.owner is None


def _jumps(clock):
    from gesturekey.actions.types import CursorJump
    return [a.direction for a in clock.actions if isinstance(a, CursorJump)]


def test_opening_the_hand_tilted_sends_the_cursor_to_that_monitor(clock):
    _point(clock, 0.3)
    clock.run(PALM, 0.1, tilt=40)                                 # like sweeping a window
    assert _jumps(clock) == ["right"]
    assert "MOUSE_TO_MONITOR" in clock.events and clock.arbiter.owner is None


def test_opening_the_hand_upright_just_lets_go(clock):
    _point(clock, 0.3)
    clock.run(PALM, 0.1, tilt=-8)
    assert _jumps(clock) == [] and clock.arbiter.owner is None


def test_moving_fast_never_jumps(clock):
    _point(clock, 0.3)
    _point(clock, 0.1, wrist=(0.5, 0.7), to=(0.75, 0.7))          # 2.5 image widths/s
    assert _jumps(clock) == []


def test_leaning_the_index_towards_a_corner_does_not_jump(clock):
    _point(clock, 0.3)
    _point(clock, 0.4, tilt=55)
    assert _jumps(clock) == []


def test_hand_parked_at_the_edge_keeps_the_cursor_going(clock):
    _point(clock, 0.3, wrist=(0.5, 0.7))
    _point(clock, 0.3, wrist=(0.5, 0.7), to=(0.95, 0.7))          # slowly to the camera's right edge
    before = _moved(clock)[0]
    _point(clock, 1.0, wrist=(0.95, 0.7))                          # and keep it there
    assert _moved(clock)[0] - before > 0.5                         # glided most of a monitor further
    assert _jumps(clock) == []


def test_jump_target_keeps_the_relative_spot():
    from gesturekey.actions.executor import cursor_jump_target
    mons = [((0, 0, 1366, 768), None), ((1366, 0, 2732, 768), None), ((-1366, 0, 0, 768), None)]
    assert cursor_jump_target(mons, (683, 384), "right") == (2049, 384)
    assert cursor_jump_target(mons, (683, 384), "left") == (-683, 384)
    assert cursor_jump_target(mons, (2000, 100), "right") == (2000, 100)   # no monitor beyond
