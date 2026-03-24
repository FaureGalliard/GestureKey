from __future__ import annotations
import json
import sys
import os
from dataclasses import dataclass, asdict, fields
from pathlib import Path



def get_resource_path(relative_path: str) -> Path:
    if hasattr(sys, "frozen"):
        base = Path(sys.executable).parent
    else:
        base = Path(os.path.abspath("."))
    return base / relative_path

def get_settings_path() -> Path:
   
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path.home() / ".config"

    settings_dir = base / "GestureKey"
    settings_dir.mkdir(parents=True, exist_ok=True)
    return settings_dir / "settings.json"
@dataclass
class AppConfig:
    model_path: Path = None  # type: ignore[assignment]  — set in __post_init__

    camera_device: int = 0
    fps_limit:     int = 30

    min_confidence: float = 0.60
    state_window:   int   = 4
    state_consensus: int  = 2

    cooldown: float = 0.6

    scroll_arm_time: float = 0.18
    scroll_max_time: float = 3.0

    volume_arm_time: float = 0.20

    zoom_arm_time: float = 0.18

    pause_min_time:  float = 0.20
    pause_max_time:  float = 1.50
    pause_cooldown:  float = 0.50

    mute_max_time: float = 1.0

    task_view_arm_time:     float = 0.15
    task_view_min_approach: float = 0.15
    task_view_cooldown:     float = 1.5

    intent_z_enter: float = -0.045
    intent_z_exit:  float = -0.005

    deadzone:    float = 0.015
    smoothing:   float = 0.7
    scroll_sens: float = 1.2
    volume_sens: float = 1.0
    zoom_sens:   float = 1.5

    def __post_init__(self) -> None:
        if self.model_path is None:
            self.model_path = get_resource_path("models/hand_state_rf.pkl")

    _PERSISTENT: tuple[str, ...] = (
        "camera_device",
    )

    def save(self) -> None:
        path = get_settings_path()
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}

        for key in self._PERSISTENT:
            existing[key] = getattr(self, key)

        path.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    def load(self) -> None:
        """Read persistent fields from the user settings JSON file, if it exists."""
        path = get_settings_path()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return  # first run or corrupt file — silently use defaults

        for key in self._PERSISTENT:
            if key in data:
                # Coerce to the declared type of the field.
                field_type = next(
                    (f.type for f in fields(self) if f.name == key), None
                )
                try:
                    if field_type is int or field_type == "int":
                        setattr(self, key, int(data[key]))
                    elif field_type is float or field_type == "float":
                        setattr(self, key, float(data[key]))
                    else:
                        setattr(self, key, data[key])
                except (ValueError, TypeError):
                    pass  # ignore malformed values, keep default


default_config = AppConfig()
default_config.load()           # populate from JSON on import