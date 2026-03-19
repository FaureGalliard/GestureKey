from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AppConfig:
    model_path: Path = Path("models/hand_state_rf.pkl")

    camera_device: int = 0
    fps_limit: int = 30

    min_confidence: float = 0.60
    state_window: int = 4
    state_consensus: int = 2

    cooldown: float = 0.6

    scroll_arm_time: float = 0.18

    volume_arm_time: float = 0.20

    zoom_arm_time: float = 0.18

    pause_min_time: float = 0.20
    pause_max_time: float = 1.50
    pause_cooldown: float = 0.50

    mute_max_time: float = 1.0

    task_view_arm_time: float = 0.15
    task_view_min_approach: float = 0.15
    task_view_cooldown: float = 1.5

    intent_z_enter: float = -0.045
    intent_z_exit: float = -0.005


default_config = AppConfig()