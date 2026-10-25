"""Thin ctypes wrappers over user32 — no pywin32 / pyautogui needed."""
from __future__ import annotations
import ctypes
import sys
import time
from ctypes import wintypes
from typing import Optional, Sequence, Tuple

AVAILABLE = sys.platform == "win32"

VK = {
    "ctrl": 0x11, "shift": 0x10, "alt": 0x12, "win": 0x5B,
    "tab": 0x09, "esc": 0x1B, "enter": 0x0D, "f4": 0x73,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "printscreen": 0x2C,
    "plus": 0xBB, "minus": 0xBD,              # VK_OEM_PLUS / VK_OEM_MINUS (= and -)
    "volume_mute": 0xAD, "volume_down": 0xAE, "volume_up": 0xAF,
    "media_play_pause": 0xB3,
}

_EXTENDED = {0x25, 0x26, 0x27, 0x28, 0x5B, 0x2C}
_KEYEVENTF_EXTENDEDKEY = 0x0001
_KEYEVENTF_KEYUP       = 0x0002
_MOUSEEVENTF_WHEEL     = 0x0800
_SWP_NOSIZE, _SWP_NOZORDER, _SWP_NOACTIVATE = 0x0001, 0x0004, 0x0010
_SW_RESTORE, _SW_MAXIMIZE = 9, 3

if AVAILABLE:
    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _user32.GetForegroundWindow.restype = wintypes.HWND
    _user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    _user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                     ctypes.c_int, ctypes.c_int, ctypes.c_uint]
    _user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    _user32.IsZoomed.argtypes = [wintypes.HWND]
    _user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    _user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_size_t]
    _user32.mouse_event.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
                                    wintypes.DWORD, ctypes.c_size_t]


def enable_dpi_awareness() -> None:
    """Make window coordinates real pixels on scaled (125 %, 150 %…) displays."""
    if not AVAILABLE:
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)   # per-monitor
    except Exception:
        try:
            _user32.SetProcessDPIAware()
        except Exception:
            pass


def _key(vk: int, up: bool) -> None:
    flags = (_KEYEVENTF_KEYUP if up else 0) | (_KEYEVENTF_EXTENDEDKEY if vk in _EXTENDED else 0)
    _user32.keybd_event(vk, 0, flags, 0)


def hotkey(keys: Sequence[str]) -> None:
    codes = [VK[k] for k in keys]
    for vk in codes:
        _key(vk, up=False)
    time.sleep(0.02)
    for vk in reversed(codes):
        _key(vk, up=True)


def scroll(amount: int) -> None:
    _user32.mouse_event(_MOUSEEVENTF_WHEEL, 0, 0, amount & 0xFFFFFFFF, 0)   # signed delta as DWORD


def screen_size() -> Tuple[int, int]:
    if not AVAILABLE:
        return (1920, 1080)
    return (_user32.GetSystemMetrics(0), _user32.GetSystemMetrics(1))


def foreground_window() -> Optional[int]:
    hwnd = _user32.GetForegroundWindow()
    return hwnd or None


def window_rect(hwnd: int) -> Tuple[int, int, int, int]:
    r = wintypes.RECT()
    if not _user32.GetWindowRect(hwnd, ctypes.byref(r)):
        raise ctypes.WinError(ctypes.get_last_error())
    return (r.left, r.top, r.right, r.bottom)


def virtual_screen() -> Tuple[int, int, int, int]:
    """(left, top, width, height) of the desktop spanning every monitor."""
    if not AVAILABLE:
        return (0, 0, 1920, 1080)
    m = _user32.GetSystemMetrics
    return (m(76), m(77), m(78), m(79))   # SM_X/YVIRTUALSCREEN, SM_CX/CYVIRTUALSCREEN


KEEP_VISIBLE = 120   # px of a dragged window that always stay on some screen


def move_window_by(hwnd: int, dx: int, dy: int) -> None:
    """Move across all monitors, but never so far that the window is lost off-screen."""
    left, top, right, bottom = window_rect(hwnd)
    vx, vy, vw, vh = virtual_screen()
    x = max(vx - (right - left) + KEEP_VISIBLE, min(vx + vw - KEEP_VISIBLE, left + dx))
    y = max(vy, min(vy + vh - KEEP_VISIBLE, top + dy))   # title bar never above the top
    _user32.SetWindowPos(hwnd, None, x, y, 0, 0, _SWP_NOSIZE | _SWP_NOZORDER | _SWP_NOACTIVATE)


def restore_if_maximized(hwnd: int) -> None:
    if _user32.IsZoomed(hwnd):
        _user32.ShowWindow(hwnd, _SW_RESTORE)
        time.sleep(0.06)   # let Windows finish the restore animation


def maximize(hwnd: int) -> None:
    _user32.ShowWindow(hwnd, _SW_MAXIMIZE)


def close_window(hwnd: int) -> None:
    """Like clicking its X: the app may still ask to save. Targets this window, not the focus."""
    _user32.PostMessageW(hwnd, 0x0010, 0, 0)   # WM_CLOSE
