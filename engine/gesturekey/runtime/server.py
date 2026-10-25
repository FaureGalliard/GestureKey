from __future__ import annotations
import asyncio
import json
import signal
from typing import Any, Dict, Set

from websockets.asyncio.server import ServerConnection, broadcast, serve

from gesturekey.config import AppConfig
from gesturekey.runtime.engine import Engine

# Only the Tauri webview and the Vite dev server may connect from a browser.
# `None` admits clients that send no Origin header (CLI tools, tests).
ALLOWED_ORIGINS = [
    "http://tauri.localhost",
    "https://tauri.localhost",
    "tauri://localhost",
    "http://localhost:1420",
    None,
]


async def serve_engine(config: AppConfig, host: str = "127.0.0.1", port: int = 8765) -> None:
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
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set_result, None)
        except (NotImplementedError, RuntimeError):
            pass   # Windows: Ctrl+C arrives as KeyboardInterrupt instead

    engine.start()
    try:
        async with serve(handler, host, port, origins=ALLOWED_ORIGINS, max_size=2**20):
            print(f"[ENGINE] ws://{host}:{port}", flush=True)
            await stop
    finally:
        engine.stop()
