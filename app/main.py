"""
main.py — Application entry point.

Clean pipeline, no globals, no mixed concerns:

    Camera → HandTracker → StateClassifier → StateStabilizer
          → GestureManager → events → print/dispatch

Each component is independently testable and replaceable.
"""
from __future__ import annotations
import time

from app.config import AppConfig, default_config
from app.ui import OpenCVUI
from core.camera import Camera
from core.hand_tracker import HandTracker
from core.state_classifier import StateClassifier
from core.state_stabilizer import StateStabilizer
from core.gesture_manager import GestureManager
from core.cooldown_manager import CooldownManager
from domain.enums import HandState
from domain.models import FrameData


def run(config: AppConfig = default_config) -> None:
    print("="*55)
    print("  GESTURE CONTROL — refactored pipeline")
    print("="*55)
    print(f"  Model   : {config.model_path}")
    print(f"  FPS cap : {config.fps_limit}")
    print(f"  Conf ≥  : {config.min_confidence:.0%}")
    print("  Press ESC to quit")
    print("="*55 + "\n")

    camera     = Camera(config.camera_device, config.fps_limit)
    tracker    = HandTracker()
    classifier = StateClassifier(config.model_path)
    stabilizer = StateStabilizer(
        window=config.state_window,
        consensus=config.state_consensus,
        min_confidence=config.min_confidence,
    )
    cooldown   = CooldownManager(default_cooldown=config.cooldown)
    manager    = GestureManager(cooldown)
    ui         = OpenCVUI(config)

    prev_stable: HandState | None = None

    try:
        while True:
            # 1. Capture
            frame = camera.read()
            if frame is None:
                break

            # 2. Track hands
            hands_data, hands_raw = tracker.process(frame)

            # 3. Classify raw state
            if hands_data:
                raw_state, confidence = classifier.predict(hands_data)
            else:
                raw_state, confidence = HandState.NO_HANDS, 1.0

            # 4. Stabilise
            stable_state = stabilizer.update(raw_state, confidence)

            # Log state changes
            current = stabilizer.current or HandState.NO_HANDS
            if current != prev_stable:
                print(f"[STATE] {prev_stable} → {current}")
                prev_stable = current

            # 5. Build FrameData
            frame_data = FrameData(
                state=current,
                hands=hands_data,
                hands_raw=hands_raw,
                timestamp=time.time(),
            )

            # 6. Process gestures
            if current not in (HandState.NO_HANDS, HandState.UNKNOWN):
                events = manager.process(frame_data)
                for event in events:
                    print(f"[EVENT] {event.value}")

            # 7. Render UI
            ui.render(
                frame=frame,
                stable_state=stabilizer.current,
                raw_state=raw_state,
                confidence=confidence,
                state_buffer=stabilizer._buffer,   # expose for debug overlay
            )

            if ui.should_quit():
                break

    finally:
        camera.release()
        tracker.release()
        ui.close()
        print("\n✓ Application closed cleanly")


if __name__ == "__main__":
    run()