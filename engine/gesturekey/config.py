from __future__ import annotations
import json
import os
import sys
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any, Dict


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
    device: int  = 0
    width:  int  = 1280
    height: int  = 720
    fps:    int  = 60
    mirror: bool = True     # selfie view: moving right moves things right


@dataclass
class TrackingConfig:
    model_complexity:         int   = 1
    min_detection_confidence: float = 0.5
    min_tracking_confidence:  float = 0.5


@dataclass
class StabilizerConfig:
    window:         int   = 4
    consensus:      int   = 2
    min_confidence: float = 0.60


@dataclass
class ScrollConfig:
    enabled:  bool  = True
    arm_time: float = 0.18


@dataclass
class VolumeConfig:
    enabled:  bool  = True
    arm_time: float = 0.20


@dataclass
class ZoomConfig:
    enabled:  bool  = True
    arm_time: float = 0.18


@dataclass
class PauseConfig:
    enabled:  bool  = True
    min_time: float = 0.20
    max_time: float = 1.50
    cooldown: float = 0.50


@dataclass
class MuteConfig:
    enabled:  bool  = True
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
    enabled: bool = True


@dataclass
class GrabWindowConfig:
    enabled:        bool  = True
    min_arm_time:   float = 0.20   # PALM held before the FIST counts
    hold_time:      float = 0.15   # FIST held before grabbing (a quick blink is MUTE)
    speed:          float = 1.0    # full camera width ≙ full screen width × speed
    deadzone:       float = 0.002
    snap_threshold: float = 0.18   # horizontal throw that snaps left/right
    lost_timeout:   float = 0.35   # release if the fist is lost this long
    cooldown:       float = 0.40


@dataclass
class GesturesConfig:
    cooldown:     float             = 0.6
    scroll:       ScrollConfig      = field(default_factory=ScrollConfig)
    volume:       VolumeConfig      = field(default_factory=VolumeConfig)
    zoom:         ZoomConfig        = field(default_factory=ZoomConfig)
    pause:        PauseConfig       = field(default_factory=PauseConfig)
    mute:         MuteConfig        = field(default_factory=MuteConfig)
    task_view:    TaskViewConfig    = field(default_factory=TaskViewConfig)
    screenshot:   ScreenshotConfig  = field(default_factory=ScreenshotConfig)
    close_window: CloseWindowConfig = field(default_factory=CloseWindowConfig)
    grab_window:  GrabWindowConfig  = field(default_factory=GrabWindowConfig)


@dataclass
class AppConfig:
    camera:     CameraConfig     = field(default_factory=CameraConfig)
    tracking:   TrackingConfig   = field(default_factory=TrackingConfig)
    stabilizer: StabilizerConfig = field(default_factory=StabilizerConfig)
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
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path | None = None) -> "AppConfig":
        cfg = cls()
        try:
            data = json.loads((path or settings_path()).read_text(encoding="utf-8"))
        except Exception:
            return cfg  # first run or corrupt file — defaults
        if isinstance(data, dict):
            cfg.merge(data)
        return cfg


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
