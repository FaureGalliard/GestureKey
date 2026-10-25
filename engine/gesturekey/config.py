from __future__ import annotations
import json
import os
import sys
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any, Dict


#: Bump when tuning defaults change meaning, so old settings files don't pin stale values.
SCHEMA = 5


def resource_path(relative: str) -> Path:
    """Path to a bundled resource, both from source and from a PyInstaller build."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return base / relative


def settings_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path.home() / ".config"
    return base / "GestureKey" / "settings.json"


# ── sections ──────────────────────────────────────────────────────────────────

@dataclass
class CameraConfig:
    name:   str  = ""   # remembered by name: indexes shift when devices are plugged in
    device: int  = 0
    width:  int  = 1280
    height: int  = 720
    fps:    int  = 60
    mirror: bool = True     # selfie view: moving right moves things right


# Units: times in seconds, distances in image units (0..1) or in *palm lengths*
# (wrist → middle-finger knuckle in the image), so gestures feel the same at any
# distance from the camera and at any frame rate.

@dataclass
class TrackingConfig:
    min_detection_confidence: float = 0.5
    min_presence_confidence:  float = 0.5   # below this the hand is considered gone
    min_tracking_confidence:  float = 0.5
    # One Euro filter on every landmark: still hand → smooth, fast hand → no lag
    filter_min_cutoff:        float = 1.5    # Hz; lower = smoother at rest
    filter_beta:              float = 10.0   # higher = less lag when moving


@dataclass
class StatesConfig:
    """Probabilistic filter over the classifier's probabilities (sticky HMM)."""
    switch_rate:    float = 6.0    # expected pose changes per second (prior); lower = stickier
    enter:          float = 0.65   # belief needed to switch to a new state
    floor:          float = 0.02   # minimum probability per class, so no frame is absolute


@dataclass
class ContinuousConfig:
    """Shared by scroll, volume and zoom."""
    arm_time:   float = 0.10   # pose held before it starts acting
    exit_speed: float = 2.2    # wrist faster than this (image units/s) = dropping the hand
    doubt_time: float = 0.15   # classifier disagrees this long → the gesture ends


@dataclass
class ScrollConfig:
    """Drag-style, like two fingers on a touchpad: the page follows the hand."""
    enabled:   bool  = True
    per_palm:  float = 600.0   # wheel units per palm length moved slowly (120 = one notch)
    accel:     float = 0.9     # extra gain per palm-length/s above accel_from
    accel_from: float = 1.0    # palm lengths/s; slower than this is 1:1
    max_gain:  float = 6.0
    min_speed: float = 0.20    # palm lengths/s; slower is jitter, ignored
    rollback:  float = 0.20    # on exit, undo this many seconds (the hand going to rest)
    natural:   bool  = False   # True: hand down scrolls up, like touchpad "natural" scrolling


@dataclass
class VolumeConfig:
    enabled:     bool  = True
    per_palm:    float = 0.30   # volume change per palm length of vertical travel
    deadzone:    float = 0.10   # palm lengths before the level starts moving
    rollback:    float = 0.25   # on a fast exit, undo the last this-many seconds


@dataclass
class ZoomConfig:
    enabled:     bool  = True
    step_ratio:  float = 1.20   # pinch must open/close by this factor per zoom step


@dataclass
class PauseConfig:
    enabled:  bool  = True
    min_time: float = 0.35   # longer than the FOUR_FINGERS a closing hand passes through
    max_time: float = 1.50
    cooldown: float = 0.50


@dataclass
class MuteConfig:
    enabled:  bool  = False   # palm→fist→palm collides with grabbing; returns as 👎 after retraining
    max_time: float = 1.0


@dataclass
class TaskViewConfig:
    enabled:      bool  = True
    arm_time:     float = 0.15
    min_approach: float = 0.15   # image units the palms close (to open) or open (to leave)
    cooldown:     float = 1.5
    nav_step:     float = 0.8    # palm lengths of ✌️ travel per selection step (arrow key)
    select_hold:  float = 0.15   # fist held this long opens the selected window (Enter)
    idle_timeout: float = 20.0   # no gesture this long: stop driving task view
    lost_timeout: float = 3.0    # hand gone this long: stop driving task view


@dataclass
class ScreenshotConfig:
    enabled: bool = True


@dataclass
class CloseWindowConfig:
    # off by default: grabbing a window and throwing it down closes it (grab_window.close_speed)
    enabled:   bool  = False
    arm_time:  float = 0.30   # fist held still before the jerk counts (it's destructive)
    distance:  float = 1.2    # palm lengths the fist must drop…
    within:    float = 0.30   # …in this many seconds


@dataclass
class GrabWindowConfig:
    enabled:      bool  = True
    min_arm_time: float = 0.15   # PALM held before the FIST counts
    hold_time:    float = 0.12   # FIST held before grabbing
    speed:        float = 1.0    # slow moves: full camera width ≙ one screen width × speed
    # pointer-style acceleration, so fast moves travel further (across several monitors)
    # without the camera's field of view having to cover all of them
    accel:        float = 1.6    # extra gain per image-unit/s above accel_from
    accel_from:   float = 0.35   # image units/s; slower than this moves 1:1
    max_gain:     float = 5.0
    deadzone:     float = 0.0015
    flick_speed:  float = 1.5    # image units/s: a flick while holding sends to a monitor / maximizes
    sweep_tilt:   float = 28.0   # degrees: opening the hand tilted this far sideways = send that way
    maximize_on_move: bool = True   # a window sent to another monitor / an edge is maximized there
    edge_zone:    float = 0.12   # hand within this fraction of the camera's left/right edge…
    edge_dwell:   float = 0.25   # …for this long = "keep going that way": next monitor
    throw_speed:  float = 1.4    # release velocity that counts as a throw for the glide
    close_speed:  float = 1.8    # a downward flick this fast arms closing (destructive: higher)
    lost_timeout: float = 0.60   # release if the fist is lost this long (motion blur)
    cooldown:     float = 0.40


@dataclass
class PowerConfig:
    enabled:   bool  = True
    hold_time: float = 1.0     # both palms still this long toggles GestureKey
    max_drift: float = 0.05    # how far (image units) a wrist may wander while holding


@dataclass
class GesturesConfig:
    cooldown:     float             = 0.6
    refractory:   float             = 0.8    # after a gesture ends, nothing new starts for this long
    continuous:   ContinuousConfig  = field(default_factory=ContinuousConfig)
    scroll:       ScrollConfig      = field(default_factory=ScrollConfig)
    volume:       VolumeConfig      = field(default_factory=VolumeConfig)
    zoom:         ZoomConfig        = field(default_factory=ZoomConfig)
    pause:        PauseConfig       = field(default_factory=PauseConfig)
    mute:         MuteConfig        = field(default_factory=MuteConfig)
    task_view:    TaskViewConfig    = field(default_factory=TaskViewConfig)
    screenshot:   ScreenshotConfig  = field(default_factory=ScreenshotConfig)
    close_window: CloseWindowConfig = field(default_factory=CloseWindowConfig)
    grab_window:  GrabWindowConfig  = field(default_factory=GrabWindowConfig)
    power:        PowerConfig       = field(default_factory=PowerConfig)


@dataclass
class UIConfig:
    language: str = "auto"   # "auto" (system) | "en" | "es" | "fr" | "ko" — read by the app and overlay


@dataclass
class AppConfig:
    camera:     CameraConfig     = field(default_factory=CameraConfig)
    tracking:   TrackingConfig   = field(default_factory=TrackingConfig)
    states:     StatesConfig     = field(default_factory=StatesConfig)
    gestures:   GesturesConfig   = field(default_factory=GesturesConfig)
    ui:         UIConfig         = field(default_factory=UIConfig)

    # ── (de)serialisation ────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def merge(self, patch: Dict[str, Any]) -> None:
        """Apply a (partial, nested) dict. Unknown keys and bad types are ignored."""
        _merge(self, patch)

    def save(self, path: Path | None = None) -> None:
        path = path or settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {"schema": SCHEMA, **self.to_dict()}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path | None = None) -> "AppConfig":
        cfg = cls()
        try:
            data = json.loads((path or settings_path()).read_text(encoding="utf-8"))
        except Exception:
            return cfg  # first run or corrupt file — defaults
        if not isinstance(data, dict):
            return cfg
        if data.get("schema") == SCHEMA:
            cfg.merge(data)
        else:
            # Older file: keep the user's choices, let tuning values take the new defaults.
            cfg.merge(_choices_only(data))
        return cfg


def _choices_only(data: Dict[str, Any]) -> Dict[str, Any]:
    gestures = data.get("gestures") if isinstance(data.get("gestures"), dict) else {}
    return {
        "camera": data.get("camera") if isinstance(data.get("camera"), dict) else {},
        "ui": data.get("ui") if isinstance(data.get("ui"), dict) else {},
        "gestures": {name: {"enabled": section["enabled"]}
                     for name, section in gestures.items()
                     if isinstance(section, dict) and "enabled" in section},
    }


def _merge(target: Any, patch: Dict[str, Any]) -> None:
    for f in fields(target):
        if f.name not in patch:
            continue
        current, value = getattr(target, f.name), patch[f.name]
        if is_dataclass(current):
            if isinstance(value, dict):
                _merge(current, value)
            continue
        kind = type(current)
        if isinstance(value, bool) != (kind is bool):
            continue   # never coerce between bool and numbers
        try:
            setattr(target, f.name, kind(value) if kind in (int, float) else value)
        except (TypeError, ValueError):
            pass
