"""Window drag physics with the user's real layout: three 1366×768 monitors side by side."""
from __future__ import annotations

from gesturekey.actions.window_physics import WindowAnimator

LEFT   = ((-1366, 0, 0, 768),    (-1366, 0, 0, 720))
CENTER = ((0, 0, 1366, 768),     (0, 0, 1366, 720))
RIGHT  = ((1366, 0, 2732, 768),  (1366, 0, 2732, 720))
LAYOUT = [CENTER, RIGHT, LEFT]
DT = 1 / 120


def _anim(rect=(400, 200, 1000, 600)):
    a = WindowAnimator(LAYOUT)
    a.start(rect)
    return a


def _settle(a, seconds=2.0):
    for _ in range(int(seconds / DT)):
        a.step(DT)
        if a.settled:
            break
    return a.finish()


def test_window_follows_smoothly_between_camera_frames():
    a = _anim()
    a.move(120, 0)                         # one camera frame worth of hand motion
    xs = []
    for _ in range(4):                     # the 4 display frames until the next camera frame
        pos = a.step(DT)
        xs.append(pos[0] if pos else xs[-1])
    assert 400 < xs[0] < xs[1] < xs[2] < xs[3] <= 520   # glides, doesn't jump


def test_flick_right_lands_fully_inside_the_right_monitor():
    a = _anim()
    a.release(9000, 0, throw=True)
    landing = _settle(a)
    assert landing.action is None
    assert 1366 <= landing.x and landing.x + 600 <= 2732


def test_flick_past_the_desktop_edge_snaps_to_that_half():
    a = _anim((1800, 200, 2400, 600))     # already on the rightmost monitor
    a.release(9000, 0, throw=True)
    assert _settle(a).action == "right"


def test_gentle_release_stays_where_it_is():
    a = _anim()
    a.release(40, 0, throw=False)
    landing = _settle(a)
    assert landing.action is None and abs(landing.x - 400) < 20


def test_taken_to_the_top_maximizes():
    a = _anim()
    for _ in range(10):
        a.move(0, -60)                     # dragged up into the top edge
    assert _settle_after_release(a).action == "maximize"


def test_already_at_the_top_does_not_maximize():
    a = _anim((400, 0, 1000, 400))        # window that simply lives at y = 0
    a.move(30, 0)
    assert _settle_after_release(a).action is None


def test_upward_throw_maximizes():
    a = _anim()
    a.release(0, -6000, throw=True)
    assert _settle(a).action == "maximize"


def test_send_right_and_back_keeps_the_relative_position():
    a = _anim()                                          # x = 400 on the centre monitor
    assert a.send("right") == "moved"
    assert 1366 <= a.tx and a.tx + 600 <= 2732
    assert abs((a.tx - 1366) - 400) < 2                  # same spot on the new monitor
    assert a.send("left") == "moved" and abs(a.tx - 400) < 2
    assert a.send("left") == "moved" and -1366 <= a.tx < 0


def test_send_past_the_last_monitor_is_an_edge():
    a = _anim((1800, 200, 2400, 600))
    assert a.send("right") == "edge"


def test_window_never_leaves_the_desktop():
    a = _anim()
    for _ in range(100):
        a.move(5000, 5000)
    a.release(0, 0, throw=False)
    landing = _settle(a)
    assert landing.x <= 2732 - 120 and landing.y <= 768 - 120


def _settle_after_release(a):
    a.release(0, 0, throw=False)
    return _settle(a)


def test_executor_animates_the_window_at_display_rate(monkeypatch):
    import time
    from gesturekey.actions import executor as ex_mod
    from gesturekey.actions.types import WindowGrab, WindowMove, WindowRelease

    calls, rect = [], [400, 200, 1000, 600]
    fake = ex_mod.win32
    monkeypatch.setattr(fake, "AVAILABLE", True)
    monkeypatch.setattr(fake, "foreground_window", lambda: 42)
    monkeypatch.setattr(fake, "restore_if_maximized", lambda h: None)
    monkeypatch.setattr(fake, "monitors", lambda: LAYOUT)
    monkeypatch.setattr(fake, "window_rect", lambda h: tuple(rect))
    monkeypatch.setattr(fake, "set_window_pos", lambda h, x, y: calls.append((time.perf_counter(), x, y)))
    monkeypatch.setattr(fake, "maximize", lambda h: calls.append(("max",)))
    monkeypatch.setattr(fake, "hotkey", lambda keys: calls.append(("key", keys)))

    ex = ex_mod.ActionExecutor()
    ex.submit([WindowGrab()])
    for _ in range(10):                                   # 10 camera frames at 30 fps
        ex.submit([WindowMove(0.02, 0.0)])
        time.sleep(1 / 30)
    ex.submit([WindowRelease(None, 6.0, 0.0, throw=True)])  # flick right
    time.sleep(1.0)
    ex.stop()

    moves = [c for c in calls if len(c) == 3]
    assert len(moves) > 30                                # many more updates than camera frames
    assert 1366 <= moves[-1][1] <= 2732 - 600             # landed inside the right monitor


def test_executor_sends_the_held_window_to_the_next_monitor(monkeypatch):
    import time
    from gesturekey.actions import executor as ex_mod
    from gesturekey.actions.types import WindowGrab, WindowSendTo

    calls = []
    fake = ex_mod.win32
    monkeypatch.setattr(fake, "AVAILABLE", True)
    monkeypatch.setattr(fake, "foreground_window", lambda: 42)
    monkeypatch.setattr(fake, "restore_if_maximized", lambda h: None)
    monkeypatch.setattr(fake, "monitors", lambda: LAYOUT)
    monkeypatch.setattr(fake, "window_rect", lambda h: (400, 200, 1000, 600))
    monkeypatch.setattr(fake, "set_window_pos", lambda h, x, y: calls.append((x, y)))
    monkeypatch.setattr(fake, "hotkey", lambda keys: calls.append(keys))

    ex = ex_mod.ActionExecutor()
    ex.submit([WindowGrab(), WindowSendTo("right")])
    time.sleep(0.5)
    ex.stop()
    assert calls and 1366 <= calls[-1][0] <= 2732 - 600     # animated into the right monitor
