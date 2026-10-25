from __future__ import annotations
from typing import Dict, Optional


class CooldownManager:
    """Per-gesture cooldowns keyed by name; time comes from the frame clock."""

    def __init__(self, default_cooldown: float = 0.6) -> None:
        self._default = default_cooldown
        self._last: Dict[str, float] = {}

    def ok(self, name: str, now: float, cooldown: Optional[float] = None) -> bool:
        threshold = cooldown if cooldown is not None else self._default
        if now - self._last.get(name, float("-inf")) > threshold:
            self._last[name] = now
            return True
        return False

    def reset(self, name: str) -> None:
        self._last.pop(name, None)

    def reset_all(self) -> None:
        self._last.clear()
