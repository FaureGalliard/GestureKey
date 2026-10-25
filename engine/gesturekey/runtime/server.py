from __future__ import annotations
import asyncio
import json
import signal
import sys
import threading
from typing import Any, Callable, Dict, Set

from websockets.asyncio.server import ServerConnection, broadcast, serve

from gesturekey.config import AppConfig
from gesturekey.runtime.engine import Engine
from gesturekey.runtime.log import log

# Only the Tauri webview and the Vite dev server may connect from a browser.
# `None` admits clients that send no Origin header (CLI tools, tests).
ALLOWED_ORIGINS = [
    "http://tauri.localhost",
    "https://tauri.localhost",
    "tauri://localhost",
    "http://localhost:1420",
    None,
]


def _wait_for_stdin_eof(on_eof: Callable[[], None]) -> None:
    """
    The app closes our stdin to ask for a clean shutdown.

    Never *read* stdin on Windows: while a synchronous ReadFile is pending on a
    pipe, GetFileInformationByHandle on it blocks, and so does loading a new DLL
    (measured) — MSMF loads DLLs when the camera opens, so the camera hung until
    the app quit. Instead poll the pipe without blocking.
    """
    if sys.platform == "win32":
        _poll_pipe_closed()
    else:
        try:
            while sys.stdin and sys.stdin.buffer.read(4096):
                pass
        except (OSError, ValueError):
            pass
    on_eof()


def _poll_pipe_closed(interval: float = 0.1) -> None:
    import ctypes
    import msvcrt
    import time
    from ctypes import wintypes

    FILE_TYPE_PIPE = 3
    try:
        handle = msvcrt.get_osfhandle(sys.stdin.fileno())
    except (AttributeError, OSError, ValueError):
        handle = None
    # safe here: nothing is reading the pipe, so GetFileType can't block
    if handle is None or ctypes.windll.kernel32.GetFileType(wintypes.HANDLE(handle)) != FILE_TYPE_PIPE:
        while True:                              # not launched by the app: never treat as EOF
            time.sleep(3600)
    peek = ctypes.windll.kernel32.PeekNamedPipe
    peek.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p,
                     ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
    available = wintypes.DWORD(0)
    while True:
        if not peek(handle, None, 0, None, ctypes.byref(available), None):
            return                               # broken pipe: the app closed it (or it isn't a pipe)
        time.sleep(interval)


async def serve_engine(config: AppConfig, host: str = "127.0.0.1", port: int = 8765,
                       stop_on_stdin_eof: bool = False) -> None:
    loop    = asyncio.get_running_loop()
    clients: Set[ServerConnection] = set()

    def sink(msg: Dict[str, Any]) -> None:
        data = json.dumps(msg, separators=(",", ":"))
        loop.call_soon_threadsafe(broadcast, set(clients), data)

    engine = Engine(config, sink)

    async def handler(ws: ServerConnection) -> None:
        clients.add(ws)
        try:
            await ws.send(json.dumps(engine.hello()))
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if isinstance(msg, dict) and "cmd" in msg:
                    engine.command(msg)
        finally:
            clients.discard(ws)

    stop = loop.create_future()

    def request_stop() -> None:
        if not stop.done():
            stop.set_result(None)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, request_stop)
        except (NotImplementedError, RuntimeError):
            pass   # Windows: Ctrl+C arrives as KeyboardInterrupt instead
    if stop_on_stdin_eof:
        threading.Thread(target=_wait_for_stdin_eof, name="stdin-watch", daemon=True,
                         args=(lambda: loop.call_soon_threadsafe(request_stop),)).start()

    server = await _bind(handler, host, port)   # before the engine grabs the camera
    engine.start()
    try:
        async with server:
            log(f"[ENGINE] ws://{host}:{port}")
            await stop
            log("[ENGINE] stopping")
    finally:
        engine.stop()


async def _bind(handler, host: str, port: int, wait_s: float = 6.0):
    """A previous engine may still be releasing the port after a quick restart: wait for it."""
    deadline = asyncio.get_running_loop().time() + wait_s
    while True:
        try:
            return await serve(handler, host, port, origins=ALLOWED_ORIGINS, max_size=2**20)
        except OSError:
            if asyncio.get_running_loop().time() >= deadline:
                log(f"[ENGINE] port {port} is still in use: is another GestureKey running?")
                raise
            await asyncio.sleep(0.25)
