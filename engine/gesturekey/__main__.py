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


def main() -> None:
    parser = argparse.ArgumentParser(prog="gesturekey", description="GestureKey engine")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--debug", action="store_true", help="show an OpenCV window instead of serving")
    parser.add_argument("--parent-pid", type=int, help="exit when this process dies (set by the Tauri app)")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args()

    if args.parent_pid:
        _exit_with_parent(args.parent_pid)
    enable_dpi_awareness()
    config = AppConfig.load()

    if args.debug:
        from gesturekey.runtime.debug import run_debug
        run_debug(config)
        return

    from gesturekey.runtime.server import serve_engine
    try:
        asyncio.run(serve_engine(config, args.host, args.port))
    except KeyboardInterrupt:
        pass
    except OSError as exc:
        print(f"[ENGINE] {exc}", file=sys.stderr)
        sys.exit(1)


def _exit_with_parent(pid: int) -> None:
    """Never outlive the app: an orphaned engine would keep the camera busy."""
    import os
    import threading

    def watch() -> None:
        if sys.platform == "win32":
            import ctypes
            SYNCHRONIZE, INFINITE = 0x00100000, 0xFFFFFFFF
            handle = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
            if handle:
                ctypes.windll.kernel32.WaitForSingleObject(handle, INFINITE)
        else:
            import time
            while os.getppid() == pid:
                time.sleep(1.0)
        os._exit(0)

    threading.Thread(target=watch, name="parent-watch", daemon=True).start()


if __name__ == "__main__":
    main()
