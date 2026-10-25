"""
Usage:
    uv run python -m gesturekey                 # WebSocket engine (what the Tauri app spawns)
    uv run python -m gesturekey --port 9000
    uv run python -m gesturekey --debug         # OpenCV window, no server, for quick testing
"""
from __future__ import annotations
import argparse
import asyncio
import sys

from gesturekey import __version__
from gesturekey.actions.win32 import enable_dpi_awareness
from gesturekey.config import AppConfig
from gesturekey.runtime.log import ensure_writable_stdio, log, silence_stdio


def main() -> None:
    parser = argparse.ArgumentParser(prog="gesturekey", description="GestureKey engine")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--debug", action="store_true", help="show an OpenCV window instead of serving")
    parser.add_argument("--parent-pid", type=int,
                        help="set by the Tauri app: stop when stdin closes, exit if this process dies")
    parser.add_argument("--selftest", action="store_true",
                        help="check that every dependency loads (no camera stream); for packaged builds")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args()

    if args.selftest:
        sys.exit(_selftest())

    ensure_writable_stdio()
    if args.parent_pid:
        _exit_with_parent(args.parent_pid)
    enable_dpi_awareness()
    config = AppConfig.load()

    if args.debug:
        from gesturekey.runtime.debug import run_debug
        run_debug(config)
        return

    from gesturekey.runtime.server import serve_engine
    code = 0
    try:
        asyncio.run(serve_engine(config, args.host, args.port, stop_on_stdin_eof=bool(args.parent_pid)))
    except KeyboardInterrupt:
        pass
    except OSError as exc:
        log(f"[ENGINE] {exc}")
        code = 1
    finally:
        silence_stdio()
    sys.exit(code)


def _selftest() -> int:
    """Load every heavy dependency the way the engine does, without opening a camera stream."""
    checks = []

    def check(name, fn):
        try:
            detail = fn()
            checks.append(True)
            log(f"ok    {name}{f' — {detail}' if detail else ''}")
        except Exception as exc:
            checks.append(False)
            log(f"FAIL  {name} — {type(exc).__name__}: {exc}")

    from gesturekey.config import TrackingConfig

    def model():
        from gesturekey.runtime.engine import MODEL_PATH
        from gesturekey.vision.classifier import StateClassifier
        return ", ".join(StateClassifier(MODEL_PATH).classes)

    def mediapipe():
        from gesturekey.vision.tracker import HandTracker
        HandTracker(TrackingConfig()).release()

    def cameras():
        from gesturekey.vision.camera import device_names
        return ", ".join(device_names()) or "sin nombres"

    def volume():
        from gesturekey.actions.audio import MasterVolume
        return f"{MasterVolume().get():.2f}"

    def websockets_():
        import websockets
        return websockets.__version__

    check("modelo", model)
    check("mediapipe", mediapipe)
    check("nombres de cámaras", cameras)
    check("volumen del sistema", volume)
    check("websockets", websockets_)
    return 0 if all(checks) else 1


def _exit_with_parent(pid: int) -> None:
    """
    Fallback for when the app dies without closing our stdin: an orphaned
    engine would keep the camera busy. Normal shutdown goes through stdin EOF.
    """
    import os
    import threading
    import time

    def watch() -> None:
        if sys.platform == "win32":
            import ctypes
            SYNCHRONIZE, INFINITE = 0x00100000, 0xFFFFFFFF
            handle = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
            if handle:
                ctypes.windll.kernel32.WaitForSingleObject(handle, INFINITE)
        else:
            while os.getppid() == pid:
                time.sleep(1.0)
        time.sleep(3.0)      # give the graceful stdin path a chance first
        silence_stdio()
        os._exit(0)

    threading.Thread(target=watch, name="parent-watch", daemon=True).start()


if __name__ == "__main__":
    main()
