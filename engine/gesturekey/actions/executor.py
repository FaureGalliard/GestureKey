from __future__ import annotations
import queue
import threading
from typing import Callable, Iterable, Optional

from gesturekey.actions import win32
from gesturekey.actions.audio import MasterVolume
from gesturekey.actions.types import (
    Action, Hotkey, Scroll, VolumeBegin, VolumeSet, WindowGrab, WindowMove, WindowRelease,
)

_STOP = object()


class ActionExecutor:
    """
    Runs actions on its own thread so key presses and window sleeps never
    stall the vision pipeline. Consecutive WindowMove actions are coalesced.
    """

    def __init__(self, on_error: Callable[[str], None] = print, speed: float = 1.0) -> None:
        self._queue: "queue.Queue[object]" = queue.Queue()
        self._on_error = on_error
        self.speed = speed
        self._hwnd: Optional[int] = None
        self._screen = win32.screen_size()
        self._volume = MasterVolume()
        self._volume_ref = 0.0
        #: last level set by a volume gesture, read by the engine for the overlay
        self.volume_level: Optional[float] = None
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
        while True:
            item = pending if pending is not None else self._queue.get()
            pending = None
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
            try:
                self._run(item)  # type: ignore[arg-type]
            except Exception as exc:
                self._on_error(f"[ACTION] {type(item).__name__} failed: {exc}")

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
        elif isinstance(action, WindowMove):
            if self._hwnd:
                w, h = self._screen
                win32.move_window_by(self._hwnd, round(action.dx * w * self.speed),
                                     round(action.dy * h * self.speed))
        elif isinstance(action, VolumeBegin):
            self._volume_ref = self.volume_level = self._volume.get()
        elif isinstance(action, VolumeSet):
            self.volume_level = self._volume.set(self._volume_ref + action.delta)
        elif isinstance(action, WindowRelease):
            hwnd, self._hwnd = self._hwnd, None
            if hwnd is None:
                return
            if action.snap == "left":
                win32.hotkey(("win", "left"))
            elif action.snap == "right":
                win32.hotkey(("win", "right"))
            elif action.snap == "maximize":
                win32.maximize(hwnd)
            elif action.snap == "close":
                win32.close_window(hwnd)
