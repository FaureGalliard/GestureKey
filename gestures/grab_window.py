from __future__ import annotations
import ctypes
import time
from typing import List, Optional, Tuple

try:
    import win32api
    import win32con
    import win32gui
    _HAS_WIN32 = True
except ImportError:
    _HAS_WIN32 = False

from utils.enums import GestureEvent, HandState
from utils.models import FrameData
from gestures.base import Gesture
from pipeline.cooldown import CooldownManager

# ── ctypes flags ──────────────────────────────────────────────────────────────

_SWP_NOSIZE     = 0x0001
_SWP_NOZORDER   = 0x0004
_SWP_NOACTIVATE = 0x0010
_SetWindowPos   = ctypes.windll.user32.SetWindowPos if _HAS_WIN32 else None


# ── helpers ───────────────────────────────────────────────────────────────────

def _get_screen_size() -> Tuple[int, int]:
    if _HAS_WIN32:
        return (
            win32api.GetSystemMetrics(win32con.SM_CXSCREEN),
            win32api.GetSystemMetrics(win32con.SM_CYSCREEN),
        )
    return (1920, 1080)


def _get_wrist(frame_data: FrameData) -> Optional[Tuple[float, float]]:
    for side in ("Right", "Left"):
        raw = frame_data.hands_raw.get(side)
        if raw is not None:
            lm = raw.landmark[0]
            return lm.x, lm.y
    return None


def _foreground_hwnd() -> Optional[int]:
    if not _HAS_WIN32:
        return None
    hwnd = win32gui.GetForegroundWindow()
    return hwnd if hwnd else None


def _is_maximized(hwnd: int) -> bool:
    try:
        return win32gui.GetWindowPlacement(hwnd)[1] == win32con.SW_SHOWMAXIMIZED
    except Exception:
        return False


def _restore_if_maximized(hwnd: int) -> None:
    try:
        if _is_maximized(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.06)
    except Exception as exc:
        print(f"[GRAB] Restore error: {exc}")


def _move_window(hwnd: int, dx_px: int, dy_px: int) -> None:
    try:
        rect = win32gui.GetWindowRect(hwnd)
        _SetWindowPos(
            hwnd, 0,
            rect[0] + dx_px, rect[1] + dy_px, 0, 0,
            _SWP_NOSIZE | _SWP_NOZORDER | _SWP_NOACTIVATE,
        )
    except Exception as exc:
        print(f"[GRAB] SetWindowPos error: {exc}")


def _snap_left() -> None:
    win32api.keybd_event(win32con.VK_LWIN, 0, 0, 0)
    win32api.keybd_event(win32con.VK_LEFT, 0, 0, 0)
    time.sleep(0.05)
    win32api.keybd_event(win32con.VK_LEFT, 0, win32con.KEYEVENTF_KEYUP, 0)
    win32api.keybd_event(win32con.VK_LWIN, 0, win32con.KEYEVENTF_KEYUP, 0)


def _snap_right() -> None:
    win32api.keybd_event(win32con.VK_LWIN, 0, 0, 0)
    win32api.keybd_event(win32con.VK_RIGHT, 0, 0, 0)
    time.sleep(0.05)
    win32api.keybd_event(win32con.VK_RIGHT, 0, win32con.KEYEVENTF_KEYUP, 0)
    win32api.keybd_event(win32con.VK_LWIN, 0, win32con.KEYEVENTF_KEYUP, 0)


def _maximize(hwnd: int) -> None:
    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)


# ── states ────────────────────────────────────────────────────────────────────

class _State:
    IDLE    = "IDLE"
    ARMING  = "ARMING"
    GRABBED = "GRABBED"


# ── gesture ───────────────────────────────────────────────────────────────────

class GrabWindowGesture(Gesture):

    NAME = "GRAB_WINDOW"

    def __init__(
        self,
        cooldown: CooldownManager,
        *,
        screen_w: Optional[int] = None,
        screen_h: Optional[int] = None,
        min_arm_time: float = 0.20,
        snap_threshold: float = 0.18,
        grab_cooldown: float = 0.40,
    ) -> None:
        self._cooldown = cooldown
        self._screen_w, self._screen_h = (
            (screen_w, screen_h)
            if screen_w is not None and screen_h is not None
            else _get_screen_size()
        )
        self._min_arm_time   = min_arm_time
        self._snap_threshold = snap_threshold
        self._grab_cooldown  = grab_cooldown
        self.reset()

    # ── Gesture ABC ───────────────────────────────────────────────────────────

    def detect(self, frame_data: FrameData) -> List[GestureEvent]:
        events: List[GestureEvent] = []
        state  = frame_data.state
        now    = frame_data.timestamp
        wrist  = _get_wrist(frame_data)

        # ── IDLE ──────────────────────────────────────────────────────────────
        if self._phase == _State.IDLE:
            if state == HandState.PALM and wrist is not None:
                self._phase     = _State.ARMING
                self._arm_start = now

        # ── ARMING ────────────────────────────────────────────────────────────
        elif self._phase == _State.ARMING:
            if state == HandState.FIST:
                armed = (now - self._arm_start >= self._min_arm_time
                         and self._cooldown.ok(self.NAME, self._grab_cooldown))
                if armed:
                    hwnd = _foreground_hwnd()
                    if hwnd:
                        _restore_if_maximized(hwnd)
                        self._phase        = _State.GRABBED
                        self._hwnd         = hwnd
                        self._last_wrist   = wrist
                        self._grab_origin  = wrist
                        self._last_drag    = now

                        # NUEVO: velocidades
                        self._vel_x = 0.0
                        self._vel_y = 0.0
                    else:
                        self._phase = _State.IDLE
                else:
                    self._phase = _State.IDLE
            elif state != HandState.PALM:
                self._phase = _State.IDLE

        # ── GRABBED ───────────────────────────────────────────────────────────
        elif self._phase == _State.GRABBED:
            if state == HandState.FIST and wrist is not None and self._hwnd:
                dt = now - self._last_drag

                if dt >= 0.02 and self._last_wrist is not None:  # ~50 FPS
                    raw_dx = wrist[0] - self._last_wrist[0]
                    raw_dy = wrist[1] - self._last_wrist[1]

                    # 🔴 1. eliminar jitter pequeño
                    if abs(raw_dx) + abs(raw_dy) < 0.0015:
                        raw_dx = 0.0
                        raw_dy = 0.0

                    # 🔵 2. spring smoothing
                    k = 0.25
                    d = 0.75

                    target_dx = raw_dx * self._screen_w
                    target_dy = raw_dy * self._screen_h

                    self._vel_x += k * (target_dx - self._vel_x)
                    self._vel_y += k * (target_dy - self._vel_y)

                    self._vel_x *= d
                    self._vel_y *= d

                    dx_px = int(self._vel_x)
                    dy_px = int(self._vel_y)

                    # 🟢 3. cuantización anti-vibración
                    if abs(dx_px) < 2:
                        dx_px = 0
                    if abs(dy_px) < 2:
                        dy_px = 0

                    if dx_px != 0 or dy_px != 0:
                        _move_window(self._hwnd, dx_px, dy_px)

                    self._last_wrist = wrist
                    self._last_drag  = now

            elif state == HandState.PALM:
                total_dx = (
                    wrist[0] - self._grab_origin[0]
                    if wrist and self._grab_origin else 0.0
                )

                if self._hwnd:
                    if total_dx < -self._snap_threshold:
                        _snap_left()
                    elif total_dx > self._snap_threshold:
                        _snap_right()
                    else:
                        _maximize(self._hwnd)

                events.append(GestureEvent.GRAB_WINDOW_RELEASED)
                self._phase = _State.IDLE
                self._hwnd  = None

            else:
                self._phase = _State.IDLE
                self._hwnd  = None

        return events

    def reset(self) -> None:
        self._phase       = _State.IDLE
        self._arm_start   = 0.0
        self._hwnd        = None
        self._last_wrist  = None
        self._grab_origin = None
        self._last_drag   = 0.0

        # NUEVO
        self._vel_x = 0.0
        self._vel_y = 0.0