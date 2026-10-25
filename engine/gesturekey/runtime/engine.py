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
from gesturekey.vision.camera import Camera, CameraError, device_names, list_cameras, resolve_device
from gesturekey.vision.classifier import StateClassifier
from gesturekey.vision.states import StateFilter
from gesturekey.vision.tracker import HandTracker

Message = Dict[str, Any]
Sink    = Callable[[Message], None]

MODEL_PATH       = resource_path("models/hand_state_rf.pkl")
RETRY_S          = 3.0    # retry a missing/busy camera this often
RETRY_GAP_S      = 0.75   # between attempts when opening
STALL_S          = 2.5    # no frame for this long → reconnect
LOW_FPS          = 15.0   # below this the camera is probably starved of light

_CAMERA_HELP = {
    "busy":    "Otra aplicación está usando la cámara (Zoom, Discord, Teams, OBS…). Ciérrala y se conectará sola.",
    "missing": "No encontramos la cámara. Conéctala y se conectará sola.",
}
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
        self._cam_status:  Optional[Message] = None
        self._next_attempt = 0.0
        self._reset_gestures = False
        self._low_light    = False
        self._thread: Optional[threading.Thread] = None
        self._recorder = Recorder.from_env()

        self._camera:     Optional[Camera]          = None
        self._tracker:    Optional[HandTracker]     = None
        self._classifier: Optional[StateClassifier] = None
        self._states:     Optional[StateFilter]     = None
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
        """
        Flags (on/off, preview) apply at once, even while the pipeline thread
        is busy opening a camera; everything else is queued for that thread.
        """
        cmd = msg.get("cmd")
        if cmd == "set_enabled":
            self._set_enabled(bool(msg.get("enabled", True)))
        elif cmd == "preview":
            self._preview = bool(msg.get("on", False))
        else:
            self._commands.put(msg)

    def hello(self) -> Message:
        return {
            "type":    "hello",
            "version": __version__,
            "config":  self._config.to_dict(),
            "enabled": self._enabled,
            "camera":  self._camera_info,
            "camera_status": self._cam_status,
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
        except Exception as exc:
            traceback.print_exc()
            self._status(f"No se pudo iniciar el motor: {exc}", "error")
            self._running = False
            return

        self._open_camera()   # never raises; retries on its own if the camera isn't there
        self._status("Pipeline started")
        if self._recorder:
            self._status(f"Grabando sesión en {self._recorder.path}")
        last_preview = 0.0
        fps, fps_t, fps_n = 0.0, time.time(), 0

        while self._running:
            self._drain_commands()
            if self._reset_gestures and self._arbiter:
                self._reset_gestures = False
                self._arbiter.reset_all()

            if self._camera is None:
                if time.time() >= self._next_attempt:
                    self._open_camera(attempts=1, reconnecting=True)
                else:
                    time.sleep(0.1)
                continue
            got = self._camera.read(timeout=0.5)
            if got is None:
                if time.time() - self._camera.last_frame_at > STALL_S:
                    self._status("La cámara dejó de enviar imagen; reconectando…", "warn")
                    self._open_camera(self._camera.device, attempts=2, reconnecting=True)
                continue
            frame, stamp = got

            assert self._tracker and self._classifier and self._states and self._arbiter and self._executor
            hands = self._tracker.process(frame, stamp)
            proba = self._classifier.predict_proba(hands) if hands else None
            if proba:
                best = max(proba, key=proba.__getitem__)
                raw_state, confidence = _as_state(best), proba[best]
            else:
                raw_state, confidence = HandState.NO_HANDS, 1.0
            state = self._states.update(proba, stamp)

            frame_data = FrameData(state=state, hands=hands, timestamp=stamp,
                                   raw_state=raw_state, raw_confidence=confidence)
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
                self._check_light(fps)

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
                "owner_info": self._owner_info(owner),
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
                names = device_names()
                if "device" in (msg.get("patch") or {}).get("camera", {}) and cam.device < len(names):
                    cam.name = names[cam.device]
                self._open_camera(cam.device, fallback=old_cam[0])
            self._emit({"type": "config", "config": self._config.to_dict()})
        elif cmd == "list_cameras":
            active = self._camera.device if self._camera else None
            self._emit({"type": "cameras", "devices": list_cameras(active=active), "active": self._config.camera.device})
        elif cmd == "reconnect_camera":
            self._open_camera(attempts=2, reconnecting=True)
        else:
            self._status(f"Comando desconocido: {cmd!r}", "warn")

    # ── helpers ───────────────────────────────────────────────────────────────

    def _set_enabled(self, enabled: bool) -> None:
        """Any thread. The arbiter itself is reset on the pipeline thread."""
        self._enabled = enabled
        self._reset_gestures = True
        self._emit({"type": "enabled", "enabled": self._enabled})

    def _owner_info(self, owner) -> Optional[Message]:
        if owner is None:
            return None
        info = dict(owner.readout or {})
        if owner.NAME == "VOLUME" and self._executor and self._executor.volume_level is not None:
            info["volume"] = round(self._executor.volume_level, 3)
        if owner.NAME == "GRAB_WINDOW" and self._executor and self._executor.window_zone:
            info["zone"] = self._executor.window_zone
        return info or None

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
        if self._classifier:
            self._states = StateFilter(self._classifier.classes, cfg.states)
        self._arbiter    = GestureArbiter(cfg.gestures)
        self._power      = PowerToggleGesture(cfg.gestures.power) if cfg.gestures.power.enabled else None
        if self._executor:
            self._executor.speed = cfg.gestures.grab_window.speed

    # ── camera lifecycle ──────────────────────────────────────────────────────
    #
    # opening → ok ⇄ reconnecting, or → busy / missing, from which the loop keeps
    # retrying every RETRY_S. Nothing here may raise: a camera problem must
    # never take the engine down, it must show up in the UI and heal itself.

    def _camera_status(self, status: str, device: int, message: str = "", **extra: Any) -> None:
        self._cam_status = {"type": "camera_status", "status": status, "device": device,
                            "name": self._config.camera.name, "message": message, **extra}
        self._emit(self._cam_status)

    def _open_camera(self, device: Optional[int] = None, attempts: int = 3,
                     reconnecting: bool = False, fallback: Optional[int] = None) -> bool:
        if self._camera:
            self._camera.release()
            self._camera = None
        cam_cfg = self._config.camera
        device = resolve_device(cam_cfg) if device is None else device
        self._camera_status("reconnecting" if reconnecting else "opening", device)

        error: Optional[CameraError] = None
        for attempt in range(attempts):
            try:
                self._camera = Camera(cam_cfg, device=device)
                break
            except CameraError as exc:
                error = exc
            except Exception as exc:              # anything from OpenCV
                error = CameraError(str(exc), "missing")
            if attempt < attempts - 1:
                time.sleep(RETRY_GAP_S)

        if self._camera is None and fallback is not None and fallback != device:
            return self._open_camera(fallback, attempts=1, reconnecting=reconnecting)

        if self._camera is None:
            assert error is not None
            self._next_attempt = time.time() + RETRY_S
            self._camera_status(error.reason, device, _CAMERA_HELP[error.reason])
            self._status(str(error), "warn")
        else:
            cam_cfg.device = device
            names = device_names()
            if device < len(names):
                cam_cfg.name = names[device]
            w, h, fps = self._camera.actual
            self._low_light = False
            self._status(f"Cámara {cam_cfg.name or device}: {w}×{h} @ {fps:.0f} fps ({self._camera.backend})")
            self._camera_info = {"type": "camera", "device": device, "width": w, "height": h, "fps": fps}
            self._emit(self._camera_info)
            self._camera_status("ok", device, width=w, height=h, fps=fps, backend=self._camera.backend)

        if self._states:
            self._states.reset()
        if self._arbiter:
            self._arbiter.reset_all()
        return self._camera is not None

    def _check_light(self, fps: float) -> None:
        """Low light makes the camera lengthen exposure and drop frames: tell the user."""
        low = 0 < fps < LOW_FPS
        if low != self._low_light and self._cam_status and self._cam_status.get("status") == "ok":
            self._low_light = low
            self._cam_status = {**self._cam_status, "low_light": low, "measured_fps": round(fps)}
            self._emit(self._cam_status)

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


def _as_state(name: str) -> HandState:
    try:
        return HandState(name)
    except ValueError:
        return HandState.UNKNOWN
