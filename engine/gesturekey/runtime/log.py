"""Logging that never crashes the engine when its stdio is gone (the app is exiting)."""
from __future__ import annotations
import os
import sys


def log(message: str) -> None:
    try:
        print(message, flush=True)
    except (OSError, ValueError):
        pass


def silence_stdio() -> None:
    """Point stdio at devnull so interpreter shutdown can't fail flushing a closed pipe."""
    for name in ("stdout", "stderr"):
        try:
            getattr(sys, name).flush()
        except (AttributeError, OSError, ValueError):
            pass
        setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))


def ensure_writable_stdio() -> None:
    """A process without a console can inherit dead stdio handles; swap them for devnull."""
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name)
        try:
            stream.write("")
            stream.flush()
        except (AttributeError, OSError, ValueError):
            setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))
