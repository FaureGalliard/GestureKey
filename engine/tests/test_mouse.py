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
