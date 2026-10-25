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
    """The app closes our stdin to ask for a clean shutdown."""
    try:
        while sys.stdin and sys.stdin.buffer.read(4096):
            pass
    except (OSError, ValueError):
        pass
    on_eof()


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

    engine.start()
    try:
        async with serve(handler, host, port, origins=ALLOWED_ORIGINS, max_size=2**20):
            log(f"[ENGINE] ws://{host}:{port}")
            await stop
            log("[ENGINE] stopping")
    finally:
        engine.stop()
