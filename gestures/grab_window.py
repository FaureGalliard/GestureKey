from __future__ import annotations
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


# ── helpers ───────────────────────────────────────────────────────────────────
def _get_screen_size() -> Tuple[int, int]:
    if _HAS_WIN32:
        return (
            win32api.GetSystemMetrics(win32con.SM_CXSCREEN),
            win32api.GetSystemMetrics(win32con.SM_CYSCREEN),
        )
    return (1920, 1080)  # fallback


def _get_wrist(frame_data: FrameData) -> Optional[Tuple[float, float]]:
    """Return the wrist normalised position of the dominant (Right-first) hand."""
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
    """Return True if the window is currently maximized."""
    try:
        placement = win32gui.GetWindowPlacement(hwnd)
        # placement[1] is showCmd; SW_SHOWMAXIMIZED == 3
        return placement[1] == win32con.SW_SHOWMAXIMIZED
    except Exception:
        return False


def _restore_if_maximized(hwnd: int) -> None:
    """Restore a maximized window to its normal rect before dragging."""
    try:
        if _is_maximized(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.06)   # let Windows finish the restore
    except Exception as exc:
        print(f"[GRAB] Restore error: {exc}")


def _move_window_ctypes(hwnd: int, dx_norm: float, dy_norm: float,
                        screen_w: int, screen_h: int) -> None:
    """
    Translate window using ctypes SetWindowPos.

    Unlike pywin32's MoveWindow, SetWindowPos works across process
    boundaries — including elevated (admin-run) windows like VSCode.
    """
    import ctypes

    SWP_NOSIZE     = 0x0001
    SWP_NOZORDER   = 0x0004
    SWP_NOACTIVATE = 0x0010

    try:
        rect  = win32gui.GetWindowRect(hwnd)
        new_x = rect[0] + int(dx_norm * screen_w)
        new_y = rect[1] + int(dy_norm * screen_h)

        ctypes.windll.user32.SetWindowPos(
            hwnd, 0,
            new_x, new_y, 0, 0,
            SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE,
        )
    except Exception as exc:
        print(f"[GRAB] SetWindowPos error: {exc}")


def _snap_left(hwnd: int) -> None:
    win32api.keybd_event(win32con.VK_LWIN,  0, 0, 0)
    win32api.keybd_event(win32con.VK_LEFT,  0, 0, 0)
    time.sleep(0.05)
    win32api.keybd_event(win32con.VK_LEFT,  0, win32con.KEYEVENTF_KEYUP, 0)
    win32api.keybd_event(win32con.VK_LWIN,  0, win32con.KEYEVENTF_KEYUP, 0)


def _snap_right(hwnd: int) -> None:
    win32api.keybd_event(win32con.VK_LWIN,  0, 0, 0)
    win32api.keybd_event(win32con.VK_RIGHT, 0, 0, 0)
    time.sleep(0.05)
    win32api.keybd_event(win32con.VK_RIGHT, 0, win32con.KEYEVENTF_KEYUP, 0)
    win32api.keybd_event(win32con.VK_LWIN,  0, win32con.KEYEVENTF_KEYUP, 0)


def _maximize(hwnd: int) -> None:
    win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)


# ── states ────────────────────────────────────────────────────────────────────

class _State:
    IDLE    = "IDLE"
    ARMING  = "ARMING"    # PALM held, waiting min_arm_time
    GRABBED = "GRABBED"   # FIST — dragging


# ── gesture ───────────────────────────────────────────────────────────────────

class GrabWindowGesture(Gesture):
    """
    PALM (held ≥ min_arm_time) → FIST  : grab foreground window
                                          (auto-restores if maximized)
    FIST + hand movement               : drag via ctypes SetWindowPos
                                          (works with admin-elevated windows)
    FIST → PALM                        : release; Win+Left/Right if total X
                                          displacement > snap_threshold,
                                          otherwise maximize
    """

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
        self._cooldown       = cooldown
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
            if state == HandState.PALM:
                pass  # hold steady — wait for FIST

            elif state == HandState.FIST:
                if (now - self._arm_start >= self._min_arm_time
                        and self._cooldown.ok(self.NAME, self._grab_cooldown)):
                    hwnd = _foreground_hwnd()
                    if hwnd:
                        _restore_if_maximized(hwnd)   # must restore BEFORE reading rect
                        self._phase       = _State.GRABBED
                        self._hwnd        = hwnd
                        self._last_wrist  = wrist
                        self._grab_origin = wrist
                        self._last_drag   = now
                    else:
                        self._phase = _State.IDLE
                else:
                    self._phase = _State.IDLE

            else:
                self._phase = _State.IDLE   # any other state cancels arming

        # ── GRABBED ───────────────────────────────────────────────────────────
        elif self._phase == _State.GRABBED:
            if state == HandState.FIST and wrist is not None and self._hwnd:
                # throttled to ~30 Hz to avoid flooding SetWindowPos
                if now - self._last_drag >= 0.033 and self._last_wrist is not None:
                    dx = wrist[0] - self._last_wrist[0]
                    dy = wrist[1] - self._last_wrist[1]
                    if abs(dx) > 0.002 or abs(dy) > 0.002:   # dead-zone vs jitter
                        _move_window_ctypes(
                            self._hwnd, dx, dy,
                            self._screen_w, self._screen_h,
                        )
                    self._last_wrist = wrist
                    self._last_drag  = now

            elif state == HandState.PALM:
                # ── RELEASE ───────────────────────────────────────────────────
                total_dx = (
                    wrist[0] - self._grab_origin[0]
                    if wrist and self._grab_origin else 0.0
                )
                if self._hwnd:
                    if total_dx < -self._snap_threshold:
                        _snap_left(self._hwnd)
                    elif total_dx > self._snap_threshold:
                        _snap_right(self._hwnd)
                    else:
                        _maximize(self._hwnd)

                events.append(GestureEvent.GRAB_WINDOW_RELEASED)
                self._phase = _State.IDLE
                self._hwnd  = None

            else:
                # unexpected state — abort grab silently
                self._phase = _State.IDLE
                self._hwnd  = None

        return events

    def reset(self) -> None:
        self._phase:        str                          = _State.IDLE
        self._arm_start:    float                        = 0.0
        self._hwnd:         Optional[int]                = None
        self._last_wrist:   Optional[Tuple[float,float]] = None
        self._grab_origin:  Optional[Tuple[float,float]] = None
        self._last_drag:    float                        = 0.0