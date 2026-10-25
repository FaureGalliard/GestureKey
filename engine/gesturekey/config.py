from __future__ import annotations
import json
import os
import sys
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any, Dict


#: Bump when tuning defaults change meaning, so old settings files don't pin stale values.
SCHEMA = 2


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
    model_complexity:         int   = 1
    min_detection_confidence: float = 0.5
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
    enabled:  bool  = True
    deadzone: float = 0.25     # palm lengths around the anchor that don't scroll
    gain:     float = 2400.0   # wheel units/s at one palm length past the deadzone
    max_rate: float = 9000.0   # wheel units/s


@dataclass
class VolumeConfig:
    enabled:     bool  = True
    per_palm:    float = 0.30   # volume change per palm length of vertical travel
    deadzone:    float = 0.10   # palm lengths before the level starts moving
    rollback:    float = 0.25   # on a fast exit, undo the last this-many seconds


@dataclass
class ZoomConfig:
    enabled:     bool  = True
    step_ratio:  float = 1.25   # pinch must open/close by this factor per zoom step


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
    min_approach: float = 0.15
    cooldown:     float = 1.5


@dataclass
class ScreenshotConfig:
    enabled: bool = True


@dataclass
class CloseWindowConfig:
    enabled:   bool  = True
    arm_time:  float = 0.30   # fist held still before the jerk counts (it's destructive)
    distance:  float = 1.2    # palm lengths the fist must drop…
    within:    float = 0.30   # …in this many seconds


@dataclass
class GrabWindowConfig:
    enabled:      bool  = True
    min_arm_time: float = 0.15   # PALM held before the FIST counts
    hold_time:    float = 0.12   # FIST held before grabbing
    speed:        float = 1.0    # full camera width ≙ full screen width × speed
    deadzone:     float = 0.0015
    throw_speed:  float = 1.4    # release velocity (image units/s) that snaps / maximizes
    lost_timeout: float = 0.60   # release if the fist is lost this long (motion blur)
    cooldown:     float = 0.40


@dataclass
class PowerConfig:
    enabled:   bool  = True
    hold_time: float = 1.5     # both palms still this long toggles GestureKey
    max_drift: float = 0.05    # how far (image units) a wrist may wander while holding


@dataclass
class GesturesConfig:
    cooldown:     float             = 0.6
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
class AppConfig:
    camera:     CameraConfig     = field(default_factory=CameraConfig)
    tracking:   TrackingConfig   = field(default_factory=TrackingConfig)
    states:     StatesConfig     = field(default_factory=StatesConfig)
    gestures:   GesturesConfig   = field(default_factory=GesturesConfig)

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
