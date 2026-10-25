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
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args()

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
