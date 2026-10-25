"""
Actions are plain data returned by gestures. Only the executor turns them
into OS input, so gestures stay pure and testable.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Optional, Tuple, Union


@dataclass(frozen=True)
class Hotkey:
    keys: Tuple[str, ...]     # e.g. ("win", "tab"); see actions.win32.VK
    times: int = 1


@dataclass(frozen=True)
class Scroll:
    amount: int               # raw wheel delta, positive = up


@dataclass(frozen=True)
class WindowGrab:
    """Capture the foreground window (restoring it if maximized)."""


@dataclass(frozen=True)
class WindowMove:
    dx: float                 # normalised: 1.0 = full screen width
    dy: float


@dataclass(frozen=True)
class WindowRelease:
    snap: Optional[Literal["left", "right", "maximize"]] = None


Action = Union[Hotkey, Scroll, WindowGrab, WindowMove, WindowRelease]
