
from __future__ import annotations
import time
from typing import Dict


class CooldownManager:
   
    def __init__(self, default_cooldown: float = 0.6) -> None:
        self._default = default_cooldown
        self._last: Dict[str, float] = {}

    def ok(self, name: str, cooldown: float | None = None) -> bool:
      
        now = time.time()
        threshold = cooldown if cooldown is not None else self._default
        if now - self._last.get(name, 0.0) > threshold:
            self._last[name] = now
            return True
        return False

    def reset(self, name: str) -> None:
        
        self._last.pop(name, None)

    def reset_all(self) -> None:
        self._last.clear()