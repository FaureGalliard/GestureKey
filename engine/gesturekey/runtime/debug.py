"""`python -m gesturekey --debug`: run the engine with an OpenCV window, no server."""
from __future__ import annotations
import base64
import threading
from typing import Any, Dict, Optional

import cv2
import numpy as np

from gesturekey.config import AppConfig
from gesturekey.runtime.engine import Engine

_BONES = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10),
          (10, 11), (11, 12), (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (0, 17),
          (17, 18), (18, 19), (19, 20)]


def run_debug(config: AppConfig) -> None:
    lock = threading.Lock()
    last: Dict[str, Optional[Dict[str, Any]]] = {"frame": None, "preview": None}

    def sink(msg: Dict[str, Any]) -> None:
        kind = msg.get("type")
        if kind in ("frame", "preview"):
            with lock:
                last[kind] = msg
        if kind in ("event", "status"):
            print(f"[{kind.upper()}] {msg.get('event') or msg.get('message')}", flush=True)

    engine = Engine(config, sink, persist=False)
    engine.start()
    engine.command({"cmd": "preview", "on": True})
    try:
        while True:
            with lock:
                frame_msg, preview = last["frame"], last["preview"]
            if preview and preview.get("jpeg"):
                img = cv2.imdecode(np.frombuffer(base64.b64decode(preview["jpeg"]), np.uint8), cv2.IMREAD_COLOR)
                if img is not None and frame_msg:
                    _draw(img, frame_msg)
                    cv2.imshow("GestureKey debug (q to quit)", img)
            if cv2.waitKey(15) & 0xFF == ord("q"):
                break
    except KeyboardInterrupt:
        pass
    finally:
        engine.stop()
        cv2.destroyAllWindows()


def _draw(img: np.ndarray, msg: Dict[str, Any]) -> None:
    h, w = img.shape[:2]
    for hand in msg["hands"]:
        pts = [(int(x * w), int(y * h)) for x, y in hand["landmarks"]]
        for a, b in _BONES:
            cv2.line(img, pts[a], pts[b], (200, 200, 200), 1, cv2.LINE_AA)
        for p in pts:
            cv2.circle(img, p, 2, (52, 211, 153), -1, cv2.LINE_AA)
        cv2.putText(img, hand["side"], (pts[0][0] + 6, pts[0][1] + 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
    label = f"{msg['state']}  ({msg['raw_state']} {msg['confidence']:.2f})  {msg['fps']:.0f} fps"
    if msg.get("owner"):
        label += f"  owner={msg['owner']}"
    if not msg.get("enabled", True):
        label += "  OFF"
    cv2.putText(img, label, (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
