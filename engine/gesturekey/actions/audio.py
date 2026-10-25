"""System master volume through Core Audio (pycaw). Windows only."""
from __future__ import annotations
import sys
from typing import Any, Optional

AVAILABLE = sys.platform == "win32"


class MasterVolume:
    """Lazily bound to the default speakers; must live on one thread (COM)."""

    def __init__(self) -> None:
        self._endpoint: Optional[Any] = None

    def _bind(self) -> Any:
        if self._endpoint is None:
            import comtypes
            from pycaw.pycaw import AudioUtilities
            comtypes.CoInitialize()
            self._endpoint = AudioUtilities.GetSpeakers().EndpointVolume
        return self._endpoint

    def get(self) -> float:
        return float(self._bind().GetMasterVolumeLevelScalar())

    def set(self, level: float) -> float:
        level = max(0.0, min(1.0, level))
        self._bind().SetMasterVolumeLevelScalar(level, None)
        return level
