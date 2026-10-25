"""
Window drag physics, independent of Windows (testable anywhere).

The camera delivers ~30 hand positions per second; moving a window only then
looks like stepping. Instead the window *follows a target* at display rate
(~120 Hz) with a critically-damped approach, so it glides between camera
frames. On release it keeps its velocity and decays (a flick), and where it
lands decides what happens:

  - lands mostly on another monitor   → settles fully inside that monitor
  - thrown against a desktop edge with no monitor beyond → snaps to that half
  - ends with its top at the top of a monitor            → maximizes there
  - otherwise                                             → stays where it landed
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

Rect = Tuple[int, int, int, int]            # left, top, right, bottom
Monitor = Tuple[Rect, Rect]                  # full rect, work area


@dataclass
class Landing:
    x: float
    y: float
    action: Optional[str] = None             # None | "left" | "right" | "maximize"


@dataclass
class PhysicsConfig:
    follow_tau:     float = 0.035   # s: how tightly the window follows the hand
    glide_tau:      float = 0.18    # s: flick decay; travel = speed × glide_tau
    settle_tau:     float = 0.06    # s: approach to the landing spot
    max_glide:      float = 1.0     # flick travels at most this many monitor widths
    top_margin:     int   = 10      # px: top this close to a monitor's top → maximize
    edge_margin:    int   = 8       # px: title bar this close to the desktop's outer edge → snap
    keep_visible:   int   = 120     # px of the window that always stay on screen
    snap_halves:    bool  = False   # desktop edge → half of the monitor; off: maximize (nobody
                                    # keeps a half window, per the user's testing)


def _contains(rect: Rect, x: float, y: float) -> bool:
    return rect[0] <= x < rect[2] and rect[1] <= y < rect[3]


def _approach(pos: float, target: float, dt: float, tau: float) -> float:
    return target + (pos - target) * math.exp(-dt / tau)


class WindowAnimator:
    def __init__(self, monitors: List[Monitor], cfg: Optional[PhysicsConfig] = None) -> None:
        self.monitors = monitors
        self.cfg = cfg or PhysicsConfig()
        self.active = False
        self._landing: Optional[Landing] = None

    # ── drag ─────────────────────────────────────────────────────────────────

    def start(self, rect: Rect) -> None:
        left, top, right, bottom = rect
        self.w, self.h = right - left, bottom - top
        self.x = self.tx = float(left)
        self.y = self.ty = float(top)
        self.active, self._landing = True, None
        self._pushed_top = False
        self.start_monitor = self.monitor_at(left + self.w / 2, top + self.h / 2)

    @property
    def px_per_unit(self) -> float:
        """Hand travel is scaled to the monitor the drag started on."""
        (l, _, r, _), _work = self.start_monitor
        return float(r - l)

    def move(self, dx: float, dy: float) -> None:
        if self._landing is None:
            want_y = self.ty + dy
            self.tx, self.ty = self._clamp(self.tx + dx, want_y)
            if want_y < self.ty:                       # pushed against the top of the desktop
                self._pushed_top = True
            elif self.ty > self._top_of(self.tx) + self.cfg.top_margin:
                self._pushed_top = False

    def step(self, dt: float) -> Optional[Tuple[int, int]]:
        """Advance; returns the new integer position when it changed."""
        if not self.active:
            return None
        tau = self.cfg.follow_tau if self._landing is None else self.cfg.settle_tau
        before = (round(self.x), round(self.y))
        self.x = _approach(self.x, self.tx, dt, tau)
        self.y = _approach(self.y, self.ty, dt, tau)
        now = (round(self.x), round(self.y))
        return now if now != before else None

    def send(self, direction: str) -> str:
        """
        Jump to the neighbouring monitor (animated), keeping the window's relative
        position in the work area. Returns "moved", or "edge" when there is no
        monitor that way.
        """
        here = self.monitor_at(self.tx + self.w / 2, self.ty + self.h / 2)
        hl, ht, hr, hb = here[0]
        hcx = (hl + hr) / 2
        sign = 1 if direction == "right" else -1
        candidates = [m for m in self.monitors
                      if m is not here
                      and sign * ((m[0][0] + m[0][2]) / 2 - hcx) > 0          # that way
                      and m[0][1] < hb and m[0][3] > ht]                      # overlaps vertically
        if not candidates:
            return "edge"
        target = min(candidates, key=lambda m: abs((m[0][0] + m[0][2]) / 2 - hcx))
        (wl, wt, wr, wb), (nl, nt, nr, nb) = here[1], target[1]
        rx = (self.tx - wl) / max(1.0, (wr - wl) - self.w)
        ry = (self.ty - wt) / max(1.0, (wb - wt) - self.h)
        x = nl + max(0.0, min(1.0, rx)) * max(0.0, (nr - nl) - self.w)
        y = nt + max(0.0, min(1.0, ry)) * max(0.0, (nb - nt) - self.h)
        self.tx, self.ty = self._fit(x, y, target)
        self._pushed_top = False
        return "moved"

    # ── release ──────────────────────────────────────────────────────────────

    def release(self, vx: float, vy: float, throw: bool) -> Landing:
        """vx, vy in px/s at the moment the hand opened. Starts the settle animation."""
        cfg = self.cfg
        zone = self.zone
        if zone is not None:                          # dropped in a snap zone: no glide
            x, y = self._fit(self.tx, self.ty, self.monitor_at(self.tx + self.w / 2, self.ty + 15))
            self.tx, self.ty = (self.tx, self.ty) if zone == "maximize" else (x, y)
            self._landing = Landing(self.tx, self.ty, zone)
            return self._landing
        cap = cfg.max_glide * self.px_per_unit
        gx = max(-cap, min(cap, vx * cfg.glide_tau))
        gy = max(-cap, min(cap, vy * cfg.glide_tau))
        raw_x, raw_y = self.tx + gx, self.ty + gy
        cx, cy = raw_x + self.w / 2, raw_y + self.h / 2

        landed_on = self._monitor_containing(cx, cy)
        here = self.monitor_at(self.tx + self.w / 2, self.ty + self.h / 2)
        action = None

        if landed_on is None:
            # flung past the edge of the desktop: no monitor there
            if throw and abs(vx) >= abs(vy):
                action = "right" if vx > 0 else "left"
            x, y = self._fit(raw_x, raw_y, here)
        elif landed_on != here:
            x, y = self._fit(raw_x, raw_y, landed_on)   # moved to another monitor: fully inside it
        else:
            x, y = self._clamp(raw_x, raw_y)

        target_monitor = landed_on or here
        at_top = y <= target_monitor[1][1] + cfg.top_margin
        # like Windows: only when the window was *taken* to the top, not merely left there
        if action is None and at_top and (self._pushed_top or (throw and vy < 0)):
            action = "maximize"

        self.tx, self.ty = x, y
        self._landing = Landing(x, y, action)
        return self._landing

    @property
    def zone(self) -> Optional[str]:
        """
        Where letting go *now* would put the window, like Windows' snap preview:
        "maximize" when taken to the top of a monitor, "left"/"right" when its
        title bar is pushed against the outer edge of the desktop. None otherwise.
        """
        if not self.active or self._landing is not None:
            return None
        cx, cy = self.tx + self.w / 2, self.ty + 15          # a point on the title bar
        work = self.monitor_at(cx, max(cy, self.ty))[1]
        if self._pushed_top and self.ty <= work[1] + self.cfg.top_margin:
            return "maximize"
        left = min(m[0][0] for m in self.monitors)
        right = max(m[0][2] for m in self.monitors)
        edge = "left" if cx <= left + self.cfg.edge_margin else "right" if cx >= right - self.cfg.edge_margin else None
        if edge and not self.cfg.snap_halves:
            return "maximize"
        return edge

    def land(self, action: Optional[str]) -> Landing:
        """End the drag here (after any send): settle at the target, then `action`."""
        self._landing = Landing(self.tx, self.ty, action)
        return self._landing

    @property
    def settled(self) -> bool:
        return (self._landing is not None
                and abs(self.x - self.tx) < 0.5 and abs(self.y - self.ty) < 0.5)

    def finish(self) -> Optional[Landing]:
        landing, self.active, self._landing = self._landing, False, None
        if landing and landing.action in ("left", "right") and not self.cfg.snap_halves:
            landing.action = "maximize"
        return landing

    # ── geometry ─────────────────────────────────────────────────────────────

    def _monitor_containing(self, x: float, y: float) -> Optional[Monitor]:
        for m in self.monitors:
            if _contains(m[0], x, y):
                return m
        return None

    def monitor_at(self, x: float, y: float) -> Monitor:
        """Monitor containing the point, or the nearest one."""
        found = self._monitor_containing(x, y)
        if found:
            return found

        def distance(m: Monitor) -> float:
            l, t, r, b = m[0]
            return math.hypot(max(l - x, 0, x - r), max(t - y, 0, y - b))
        return min(self.monitors, key=distance)

    def _top_of(self, x: float) -> int:
        return self.monitor_at(x + self.w / 2, self.ty)[1][1]

    def _fit(self, x: float, y: float, monitor: Monitor) -> Tuple[float, float]:
        l, t, r, b = monitor[1]
        x = max(l, min(x, r - self.w)) if self.w <= r - l else l
        y = max(t, min(y, b - self.h)) if self.h <= b - t else t
        return x, y

    def _clamp(self, x: float, y: float) -> Tuple[float, float]:
        """Anywhere on the desktop, as long as part of the window stays visible."""
        k = self.cfg.keep_visible
        left = min(m[0][0] for m in self.monitors)
        right = max(m[0][2] for m in self.monitors)
        top = min(m[0][1] for m in self.monitors)
        bottom = max(m[0][3] for m in self.monitors)
        x = max(left - self.w + k, min(right - k, x))
        y = max(top, min(bottom - k, y))
        return x, y
