from __future__ import annotations
import asyncio
import json

import pytest
from websockets.asyncio.client import connect
from websockets.exceptions import InvalidStatus

from gesturekey.config import AppConfig
from gesturekey.runtime import server


class FakeEngine:
    """Stands in for the real pipeline: no camera, no model."""

    def __init__(self, config, sink, persist=True):
        self.sink, self.commands = sink, []

    def start(self):
        self.sink({"type": "status", "level": "info", "message": "Pipeline started"})

    def stop(self):
        pass

    def hello(self):
        return {"type": "hello", "version": "test", "config": {}, "enabled": True}

    def command(self, msg):
        self.commands.append(msg)
        self.sink({"type": "enabled", "enabled": msg.get("enabled")})


def _run_server(monkeypatch, port):
    monkeypatch.setattr(server, "Engine", FakeEngine)
    return asyncio.ensure_future(server.serve_engine(AppConfig(), port=port))


def test_hello_and_command_roundtrip(monkeypatch, unused_port):
    async def scenario():
        task = _run_server(monkeypatch, unused_port)
        await asyncio.sleep(0.2)
        async with connect(f"ws://127.0.0.1:{unused_port}") as ws:
            assert json.loads(await ws.recv())["type"] == "hello"
            await ws.send(json.dumps({"cmd": "set_enabled", "enabled": False}))
            assert json.loads(await ws.recv()) == {"type": "enabled", "enabled": False}
        task.cancel()

    asyncio.run(scenario())


def test_rejects_foreign_origin(monkeypatch, unused_port):
    async def scenario():
        task = _run_server(monkeypatch, unused_port)
        await asyncio.sleep(0.2)
        with pytest.raises(InvalidStatus):
            async with connect(f"ws://127.0.0.1:{unused_port}", origin="https://evil.example"):
                pass
        task.cancel()

    asyncio.run(scenario())


@pytest.fixture
def unused_port():
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
