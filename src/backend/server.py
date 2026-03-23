from __future__ import annotations
import asyncio
import base64
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import cv2
import websockets
from websockets import serve

from config import AppConfig
from vision.camera import Camera
from vision.hand_tracker import HandTracker
from vision.state_classifier import StateClassifier
from pipeline.state_stabilizer import StateStabilizer
from pipeline.gesture_manager import GestureManager
from pipeline.cooldown_manager import CooldownManager
from enums import HandState
from models import FrameData

CONFIG = AppConfig(model_path=ROOT / "models" / "hand_state_rf.pkl")

connected_clients: set = set()


async def broadcast(msg: dict) -> None:
    if not connected_clients:
        return
    data = json.dumps(msg)
    await asyncio.gather(
        *[ws.send(data) for ws in connected_clients],
        return_exceptions=True,
    )


async def handler(ws) -> None:
    connected_clients.add(ws)
    print(f"[WS] Client connected — {len(connected_clients)} total")
    try:
        async for message in ws:
            try:
                msg = json.loads(message)
                print(f"[WS] Received: {msg}")
            except Exception:
                pass
    finally:
        connected_clients.discard(ws)
        print(f"[WS] Client disconnected — {len(connected_clients)} total")


async def pipeline_loop() -> None:
    cfg = CONFIG

    camera     = Camera(cfg.camera_device, cfg.fps_limit)
    tracker    = HandTracker()
    classifier = StateClassifier(cfg.model_path)
    stabilizer = StateStabilizer(
        window=cfg.state_window,
        consensus=cfg.state_consensus,
        min_confidence=cfg.min_confidence,
    )
    cooldown = CooldownManager(default_cooldown=cfg.cooldown)
    manager  = GestureManager(cooldown)

    print("[PIPELINE] Started")
    prev_stable: HandState | None = None

    try:
        while True:
            frame = camera.read()
            if frame is None:
                await asyncio.sleep(0.05)
                continue

            hands_data, hands_raw = tracker.process(frame)

            if hands_data:
                raw_state, confidence = classifier.predict(hands_data)
            else:
                raw_state, confidence = HandState.NO_HANDS, 1.0

            stabilizer.update(raw_state, confidence)
            current = stabilizer.current or HandState.NO_HANDS

            events = []
            if current not in (HandState.NO_HANDS, HandState.UNKNOWN):
                frame_data = FrameData(
                    state=current,
                    hands=hands_data,
                    hands_raw=hands_raw,
                    timestamp=time.time(),
                )
                events = manager.process(frame_data)

            # detected hands list e.g. ["Right"], ["Left", "Right"], []
            detected_hands = list(hands_data.keys())

            msg: dict = {
                "state":      current.value,
                "raw_state":  raw_state.value,
                "confidence": round(confidence, 4),
                "timestamp":  round(time.time(), 3),
                "paused":     manager._pause.is_paused(),
                "hands":      detected_hands,
            }

            if current != prev_stable:
                prev_stable = current

            if events:
                msg["event"] = events[0].value

            await broadcast(msg)

            if connected_clients:
                frame_flipped = cv2.flip(frame, 1)
                _, buf = cv2.imencode(".jpg", frame_flipped, [cv2.IMWRITE_JPEG_QUALITY, 70])
                await broadcast({
                    "type": "frame",
                    "data": base64.b64encode(buf).decode(),
                })

            await asyncio.sleep(0)

    finally:
        camera.release()
        tracker.release()
        print("[PIPELINE] Stopped")


async def main() -> None:
    async with serve(handler, "localhost", 8765):
        print("[WS] Server listening on ws://localhost:8765")
        await pipeline_loop()


if __name__ == "__main__":
    asyncio.run(main())