"""
Session recorder: every frame/event/status message as one JSON line.

Enabled with the GESTUREKEY_RECORD environment variable:
    GESTUREKEY_RECORD=1            → %APPDATA%/GestureKey/recordings/session-<time>.jsonl
    GESTUREKEY_RECORD=path.jsonl   → that file

Analyse a recording with `uv run python -m gesturekey.tools.analyze <file>`.
"""
from __future__ import annotations
import json
import os
import time
from pathlib import Path
from typing import IO, Any, Dict, Optional

from gesturekey.config import settings_path

RECORDED = {"frame", "event", "status", "camera", "config", "enabled"}


class Recorder:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        # line-buffered: the app kills the engine on exit, so nothing may wait in a buffer
        self._file: Optional[IO[str]] = path.open("a", encoding="utf-8", buffering=1)

    @classmethod
    def from_env(cls) -> Optional["Recorder"]:
        value = os.environ.get("GESTUREKEY_RECORD", "").strip()
        if not value or value == "0":
            return None
        if value == "1":
            stamp = time.strftime("%Y%m%d-%H%M%S")
            return cls(settings_path().parent / "recordings" / f"session-{stamp}.jsonl")
        return cls(Path(value))

    def write(self, msg: Dict[str, Any]) -> None:
        if self._file and msg.get("type") in RECORDED:
            self._file.write(json.dumps(msg, separators=(",", ":")) + "\n")

    def close(self) -> None:
        if self._file:
            self._file.close()
            self._file = None
