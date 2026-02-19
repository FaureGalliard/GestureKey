from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AppConfig:
    """
    Central configuration injected into all components.
    No more scattered module-level constants.
    """
    # ---- paths ---------------------------------------------------------
    model_path: Path = Path("models/hand_state_rf.pkl")

    # ---- camera --------------------------------------------------------
    camera_device: int = 0
    fps_limit: int = 30

    # ---- classifier / stabilizer ---------------------------------------
    min_confidence: float = 0.60
    state_window: int = 4
    state_consensus: int = 2

    # ---- global cooldown (seconds) ------------------------------------
    cooldown: float = 0.6

    # ---- scroll --------------------------------------------------------
    scroll_arm_time: float = 0.18
    scroll_max_time: float = 3.0

    # ---- volume --------------------------------------------------------
    volume_arm_time: float = 0.20

    # ---- zoom ----------------------------------------------------------
    zoom_arm_time: float = 0.18

    # ---- pause/resume --------------------------------------------------
    pause_min_time: float = 0.20
    pause_max_time: float = 1.50
    pause_cooldown: float = 0.50

    # ---- mute ----------------------------------------------------------
    mute_max_time: float = 1.0

    # ---- task view -----------------------------------------------------
    task_view_arm_time: float = 0.15
    task_view_min_approach: float = 0.15
    task_view_cooldown: float = 1.5

    # ---- intent / depth gate ------------------------------------------
    intent_z_enter: float = -0.045
    intent_z_exit: float  = -0.005

    # ---- smoothing / deadzone -----------------------------------------
    deadzone: float = 0.015
    smoothing: float = 0.7
    scroll_sens: float = 1.2
    volume_sens: float = 1.0
    zoom_sens: float = 1.5


# Default singleton — import and use directly, or override in tests.
default_config = AppConfig()