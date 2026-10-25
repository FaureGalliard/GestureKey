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
    """
    Let go of the grabbed window. `vx, vy` (normalised units/s, already
    accelerated) let it glide; where it lands decides monitor / snap / maximize
    (actions.window_physics). `snap="close"` closes it instead.
    """
    snap: Optional[Literal["close"]] = None
    vx: float = 0.0
    vy: float = 0.0
    throw: bool = False


@dataclass(frozen=True)
class WindowSendTo:
    """
    Jump to the neighbouring monitor (left/right) or maximize (up). With
    `release`, the grab ends and the window is maximized where it arrives
    (or on this monitor, if there is none that way).
    """
    direction: Literal["left", "right", "up"]
    release: bool = False


@dataclass(frozen=True)
class VolumeBegin:
    """Remember the current system volume as the reference for VolumeSet."""


@dataclass(frozen=True)
class VolumeSet:
    delta: float              # level = reference ± delta, clamped to 0..1


@dataclass(frozen=True)
class CursorBegin:
    """Start driving the mouse cursor from where it is now."""


@dataclass(frozen=True)
class CursorMove:
    dx: float                 # normalised like WindowMove: 1.0 = width of the cursor's monitor
    dy: float


@dataclass(frozen=True)
class MouseButton:
    """Press / release a button where the cursor is shown (the glide is finished first)."""
    button: Literal["left", "right"]
    down: bool


Action = Union[Hotkey, Scroll, WindowGrab, WindowMove, WindowRelease, WindowSendTo, VolumeBegin, VolumeSet,
               CursorBegin, CursorMove, MouseButton]
