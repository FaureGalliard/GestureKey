from __future__ import annotations
import base64
import queue
import threading
import time
import traceback
from typing import Any, Callable, Dict, List, Optional

import cv2
import numpy as np

from gesturekey import __version__
from gesturekey.actions.executor import ActionExecutor
from gesturekey.config import AppConfig, resource_path
from gesturekey.core.types import FrameData, GestureEvent, HandState
from gesturekey.gestures.arbiter import GestureArbiter
from gesturekey.gestures.base import Output
from gesturekey.gestures.power import PowerToggleGesture
from gesturekey.runtime.recorder import Recorder
from gesturekey.vision.camera import Camera, list_cameras
from gesturekey.vision.classifier import StateClassifier
from gesturekey.vision.stabilizer import StateStabilizer
from gesturekey.vision.tracker import HandTracker

Message = Dict[str, Any]
Sink    = Callable[[Message], None]

MODEL_PATH       = resource_path("models/hand_state_rf.pkl")
PREVIEW_WIDTH    = 480
PREVIEW_INTERVAL = 1 / 12


class Engine:
    """
    The vision → gesture → action pipeline on a background thread.

    Everything it has to say goes to `sink` as JSON-able dicts (see
    docs/protocol.md). Commands from other threads are queued and applied at
    the top of the loop, so pipeline state is only touched by its own thread.
    """

    def __init__(self, config: AppConfig, sink: Sink, persist: bool = True) -> None:
        self._config   = config
        self._sink     = sink
        self._persist  = persist
        self._commands: "queue.Queue[Message]" = queue.Queue()
        self._running  = False
        self._enabled  = True
        self._preview  = False
        self._camera_info: Optional[Message] = None
        self._thread: Optional[threading.Thread] = None
        self._recorder = Recorder.from_env()

        self._camera:     Optional[Camera]          = None
        self._tracker:    Optional[HandTracker]     = None
        self._classifier: Optional[StateClassifier] = None
        self._stabilizer: Optional[StateStabilizer] = None
        self._arbiter:    Optional[GestureArbiter]  = None
        self._power:      Optional[PowerToggleGesture] = None
        self._executor:   Optional[ActionExecutor]  = None

    # ── public API (any thread) ───────────────────────────────────────────────

    def start(self) -> None:
        self._running = True
        self._thread  = threading.Thread(target=self._run, name="engine", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)

    def command(self, msg: Message) -> None:
        self._commands.put(msg)

    def hello(self) -> Message:
        return {
            "type":    "hello",
            "version": __version__,
            "config":  self._config.to_dict(),
            "enabled": self._enabled,
            "camera":  self._camera_info,
        }

    # ── loop ──────────────────────────────────────────────────────────────────

    def _emit(self, msg: Message) -> None:
        try:
            self._sink(msg)
            if self._recorder:
                self._recorder.write(msg)
        except Exception:
            traceback.print_exc()

    def _status(self, message: str, level: str = "info") -> None:
        self._emit({"type": "status", "level": level, "message": message})

    def _run(self) -> None:
        try:
            self._classifier = StateClassifier(MODEL_PATH)
            self._executor   = ActionExecutor(on_error=lambda m: self._status(m, "warn"))
            self._rebuild()
            self._open_camera(self._config.camera.device)
        except Exception as exc:
            traceback.print_exc()
            self._status(f"No se pudo iniciar el motor: {exc}", "error")
            self._running = False
            return

        self._status("Pipeline started")
        if self._recorder:
            self._status(f"Grabando sesión en {self._recorder.path}")
        last_preview = 0.0
        fps, fps_t, fps_n = 0.0, time.time(), 0

        while self._running:
            self._drain_commands()

            if self._camera is None:
                time.sleep(0.1)
                continue
            got = self._camera.read(timeout=1.0)
            if got is None:
                continue
            frame, stamp = got

            assert self._tracker and self._classifier and self._stabilizer and self._arbiter and self._executor
            hands = self._tracker.process(frame)
            if hands:
                raw_state, confidence = self._classifier.predict(hands)
            else:
                raw_state, confidence = HandState.NO_HANDS, 1.0
            self._stabilizer.update(raw_state, confidence)
            state = self._stabilizer.current or HandState.NO_HANDS

            frame_data = FrameData(state=state, hands=hands, timestamp=stamp)
            events: List[str] = []

            # power runs even while off, so the same gesture turns GestureKey back on
            if self._power is not None:
                power_out = Output()
                self._power.update(frame_data, power_out, enabled=self._enabled)
                if power_out.events:
                    self._set_enabled(GestureEvent.POWER_ON in power_out.events)
                    events += [e.value for e in power_out.events]

            if self._enabled:
                out = self._arbiter.process(frame_data)
                self._executor.submit(out.actions)
                events += [e.value for e in out.events]

            owner = self._arbiter.owner if self._enabled else None
            fps_n += 1
            if stamp - fps_t >= 1.0:
                fps, fps_t, fps_n = fps_n / (stamp - fps_t), stamp, 0

            self._emit({
                "type":       "frame",
                "t":          round(stamp, 3),
                "state":      state.value,
                "raw_state":  raw_state.value,
                "confidence": round(confidence, 3),
                "hands": [
                    {"side": h.side, "score": round(h.score, 3),
                     "landmarks": [[round(x, 4), round(y, 4)] for x, y in h.img]}
                    for h in hands.values()
                ],
                "owner":      owner.NAME if owner else None,
                "owner_info": owner.readout if owner else None,
                "arming":     self._arming(),
                "enabled":    self._enabled,
                "fps":        round(fps, 1),
            })
            for event in events:
                self._emit({"type": "event", "event": event, "t": round(stamp, 3)})

            if self._preview and stamp - last_preview >= PREVIEW_INTERVAL:
                last_preview = stamp
                self._emit({"type": "preview", "jpeg": _encode_preview(frame)})

        self._cleanup()

    # ── commands ──────────────────────────────────────────────────────────────

    def _drain_commands(self) -> None:
        while True:
            try:
                msg = self._commands.get_nowait()
            except queue.Empty:
                return
            try:
                self._handle(msg)
            except Exception as exc:
                traceback.print_exc()
                self._status(f"Comando {msg.get('cmd')!r} falló: {exc}", "error")

    def _handle(self, msg: Message) -> None:
        cmd = msg.get("cmd")
        if cmd == "set_config":
            old_cam = (self._config.camera.device, self._config.camera.width,
                       self._config.camera.height, self._config.camera.fps, self._config.camera.mirror)
            old_tracking = dict(vars(self._config.tracking))
            self._config.merge(msg.get("patch") or {})
            if self._persist:
                self._config.save()
            cam = self._config.camera
            self._rebuild(tracker=vars(self._config.tracking) != old_tracking)
            if (cam.device, cam.width, cam.height, cam.fps, cam.mirror) != old_cam:
                self._open_camera(cam.device)
            self._emit({"type": "config", "config": self._config.to_dict()})
        elif cmd == "set_enabled":
            self._set_enabled(bool(msg.get("enabled", True)))
        elif cmd == "preview":
            self._preview = bool(msg.get("on", False))
        elif cmd == "list_cameras":
            self._emit({"type": "cameras", "devices": list_cameras(), "active": self._config.camera.device})
        else:
            self._status(f"Comando desconocido: {cmd!r}", "warn")

    # ── helpers ───────────────────────────────────────────────────────────────

    def _set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if self._arbiter:
            self._arbiter.reset_all()
        self._emit({"type": "enabled", "enabled": self._enabled})

    def _arming(self) -> Optional[Message]:
        """A deliberate hold in progress, for the overlay's progress ring."""
        p = self._power.progress if self._power else None
        if p is None or p < 0.1:   # don't flash the ring for a palm that's just passing
            return None
        return {"gesture": "POWER", "progress": round(p, 3), "action": "off" if self._enabled else "on"}

    def _rebuild(self, tracker: bool = True) -> None:
        cfg = self._config
        if tracker or self._tracker is None:
            if self._tracker:
                self._tracker.release()
            self._tracker = HandTracker(cfg.tracking)
        self._stabilizer = StateStabilizer(cfg.stabilizer)
        self._arbiter    = GestureArbiter(cfg.gestures)
        self._power      = PowerToggleGesture(cfg.gestures.power) if cfg.gestures.power.enabled else None
        if self._executor:
            self._executor.speed = cfg.gestures.grab_window.speed

    def _open_camera(self, device: int) -> None:
        previous = self._camera.device if self._camera else None
        if self._camera:
            self._camera.release()
            self._camera = None
        cam_cfg = self._config.camera
        try:
            cam_cfg.device = device
            self._camera = Camera(cam_cfg)
        except Exception as exc:
            self._status(f"No se pudo abrir la cámara {device}: {exc}", "error")
            if previous is not None and previous != device:
                cam_cfg.device = previous
                self._camera = Camera(cam_cfg)
        if self._camera:
            w, h, fps = self._camera.actual
            self._status(f"Cámara {self._camera.device}: {w}×{h} @ {fps:.0f} fps")
            self._camera_info = {"type": "camera", "device": self._camera.device,
                                 "width": w, "height": h, "fps": fps}
            self._emit(self._camera_info)
        if self._stabilizer:
            self._stabilizer.reset()
        if self._arbiter:
            self._arbiter.reset_all()

    def _cleanup(self) -> None:
        if self._camera:
            self._camera.release()
        if self._tracker:
            self._tracker.release()
        if self._executor:
            self._executor.stop()
        if self._recorder:
            self._recorder.close()
        self._status("Pipeline stopped")


def _encode_preview(frame: np.ndarray) -> str:
    h, w = frame.shape[:2]
    small = cv2.resize(frame, (PREVIEW_WIDTH, int(h * PREVIEW_WIDTH / w)))
    ok, buf = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 70])
    return base64.b64encode(buf.tobytes()).decode("ascii") if ok else ""
