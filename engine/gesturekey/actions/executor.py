from __future__ import annotations
import queue
import threading
import time
from typing import Callable, Iterable, Optional

from gesturekey.actions import win32
from gesturekey.actions.audio import MasterVolume
from gesturekey.actions.types import (
    Action, Hotkey, Scroll, VolumeBegin, VolumeSet, WindowGrab, WindowMove, WindowRelease, WindowSendTo,
)
from gesturekey.actions.window_physics import WindowAnimator

_STOP = object()
FRAME_S = 1 / 120   # window animation rate, independent of the camera's ~30 fps


class ActionExecutor:
    """
    Runs actions on its own thread so key presses and window sleeps never
    stall the vision pipeline. Consecutive WindowMove actions are coalesced.

    While a window is being dragged or is gliding after a flick, the loop
    also animates it at FRAME_S (see window_physics), so it moves at display
    rate instead of stepping with each camera frame.
    """

    def __init__(self, on_error: Callable[[str], None] = print, speed: float = 1.0) -> None:
        self._queue: "queue.Queue[object]" = queue.Queue()
        self._on_error = on_error
        self.speed = speed
        self._hwnd: Optional[int] = None
        self._anim: Optional[WindowAnimator] = None
        self._volume = MasterVolume()
        self._volume_ref = 0.0
        #: last level set by a volume gesture, read by the engine for the overlay
        self.volume_level: Optional[float] = None
        #: snap zone of the window being dragged (see window_physics), for the overlay
        self.window_zone: Optional[str] = None
        self._thread = threading.Thread(target=self._loop, name="actions", daemon=True)
        self._thread.start()

    def submit(self, actions: Iterable[Action]) -> None:
        for action in actions:
            self._queue.put(action)

    def stop(self) -> None:
        self._queue.put(_STOP)
        self._thread.join(timeout=1.0)

    # ── worker ────────────────────────────────────────────────────────────────

    def _loop(self) -> None:
        pending: Optional[object] = None
        last = time.perf_counter()
        while True:
            animating = self._anim is not None and self._anim.active
            if pending is not None:
                item, pending = pending, None
            else:
                try:
                    item = self._queue.get(timeout=FRAME_S if animating else None)
                except queue.Empty:
                    item = None
            if item is _STOP:
                return
            if isinstance(item, WindowMove):
                dx, dy = item.dx, item.dy
                while True:
                    try:
                        nxt = self._queue.get_nowait()
                    except queue.Empty:
                        break
                    if isinstance(nxt, WindowMove):
                        dx, dy = dx + nxt.dx, dy + nxt.dy
                    else:
                        pending = nxt
                        break
                item = WindowMove(dx, dy)
            if item is not None:
                try:
                    self._run(item)  # type: ignore[arg-type]
                except Exception as exc:
                    self._on_error(f"[ACTION] {type(item).__name__} failed: {exc}")

            now = time.perf_counter()
            if self._anim is not None and self._anim.active:
                try:
                    self._animate(now - last)
                except Exception as exc:
                    self._on_error(f"[ACTION] window animation failed: {exc}")
                    self._anim = None
            last = now

    def _animate(self, dt: float) -> None:
        anim, hwnd = self._anim, self._hwnd
        if anim is None or hwnd is None:
            return
        pos = anim.step(min(dt, 0.05))
        if pos:
            win32.set_window_pos(hwnd, *pos)
        self.window_zone = anim.zone
        if anim.settled:
            landing = anim.finish()
            self._hwnd = None
            self.window_zone = None
            if landing and landing.action == "maximize":
                win32.maximize(hwnd)
            elif landing and landing.action in ("left", "right"):
                win32.hotkey(("win", landing.action))

    def _run(self, action: Action) -> None:
        if not win32.AVAILABLE:
            return
        if isinstance(action, Hotkey):
            for _ in range(action.times):
                win32.hotkey(action.keys)
        elif isinstance(action, Scroll):
            win32.scroll(action.amount)
        elif isinstance(action, WindowGrab):
            self._hwnd = win32.foreground_window()
            if self._hwnd:
                win32.restore_if_maximized(self._hwnd)
                self._anim = WindowAnimator(win32.monitors())
                self._anim.start(win32.window_rect(self._hwnd))
        elif isinstance(action, WindowMove):
            if self._anim and self._anim.active:
                (l, t, r, b), _work = self._anim.start_monitor
                self._anim.move(action.dx * (r - l) * self.speed, action.dy * (b - t) * self.speed)
        elif isinstance(action, WindowSendTo):
            hwnd, anim = self._hwnd, self._anim
            if hwnd is None or anim is None or not anim.active:
                return
            if action.direction == "up":
                anim.finish()
                self._hwnd = None
                win32.maximize(hwnd)
                return
            moved = anim.send(action.direction) == "moved"
            if action.release:
                anim.land("maximize")         # glide over, then maximize there
            elif not moved:
                # no monitor that way while still holding: maximize here and let go
                anim.finish()
                self._hwnd = None
                win32.maximize(hwnd)
        elif isinstance(action, VolumeBegin):
            self._volume_ref = self.volume_level = self._volume.get()
        elif isinstance(action, VolumeSet):
            self.volume_level = self._volume.set(self._volume_ref + action.delta)
        elif isinstance(action, WindowRelease):
            if self._hwnd is None or self._anim is None:
                return
            if action.snap == "close":
                win32.close_window(self._hwnd)
                self._anim.finish()
                self._hwnd = None
                return
            (l, t, r, b), _work = self._anim.start_monitor
            self._anim.release(action.vx * (r - l) * self.speed, action.vy * (b - t) * self.speed,
                               action.throw)
            # the animation loop glides it to the landing spot and applies the result
