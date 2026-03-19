"""
CooldownManager — centralises all cooldown state so gesture classes
don't need to track time themselves.
"""
from __future__ import annotations
import time
from typing import Dict


class CooldownManager:
    """
    Thread-safe (GIL-safe) per-event cooldown tracker.

    Usage
    -----
    cm = CooldownManager(default_cooldown=0.6)
    if cm.ok("SCROLL"):
        ...  # fire the event
    """

    def __init__(self, default_cooldown: float = 0.6) -> None:
        self._default = default_cooldown
        self._last: Dict[str, float] = {}

    def ok(self, name: str, cooldown: float | None = None) -> bool:
        """
        Return True (and record the timestamp) if the cooldown has elapsed
        since the last accepted event of this name.
        """
        now = time.time()
        threshold = cooldown if cooldown is not None else self._default
        if now - self._last.get(name, 0.0) > threshold:
            self._last[name] = now
            return True
        return False

    def reset(self, name: str) -> None:
        """Force-reset a specific cooldown (next call to ok() will succeed)."""
        self._last.pop(name, None)

    def reset_all(self) -> None:
        self._last.clear()