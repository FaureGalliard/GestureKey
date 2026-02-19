"""
OpenCVUI — all rendering logic isolated from detection and business logic.

The pipeline never calls cv2 directly — it delegates to this class.
"""
from __future__ import annotations
from typing import Any, Optional

import cv2

from domain.enums import HandState
from app.config import AppConfig

_STATE_COLORS = {
    HandState.PALM:          (0,   255,  0),
    HandState.FIST:          (0,   0,  255),
    HandState.PINCH:         (255, 0,  255),
    HandState.TWO_FINGERS:   (255, 255,  0),
    HandState.THREE_FINGERS: (0,   255, 255),
    HandState.FOUR_FINGERS:  (255, 165,  0),
    HandState.UNKNOWN:       (128, 128, 128),
    HandState.NO_HANDS:      (64,  64,   64),
}
_DEFAULT_COLOR = (255, 255, 255)


class OpenCVUI:
    """Renders debug overlays onto the frame and shows it in a window."""

    def __init__(self, config: AppConfig, window_name: str = "Gesture Control") -> None:
        self._cfg  = config
        self._name = window_name

    def render(
        self,
        frame: Any,
        stable_state: Optional[HandState],
        raw_state: HandState,
        confidence: float,
        state_buffer: Any,      # deque / sequence of HandState
    ) -> None:
        """Flip frame, draw overlays, show window."""
        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]

        # Centre divider
        cv2.line(frame, (w // 2, 0), (w // 2, h), (255, 255, 255), 2)

        # Stable state label
        display_state = stable_state or HandState.NO_HANDS
        color = _STATE_COLORS.get(display_state, _DEFAULT_COLOR)
        cv2.putText(frame, f"State: {display_state.value}",
                    (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)

        # Raw prediction + confidence
        debug_color = (200, 200, 200) if confidence >= self._cfg.min_confidence else (100, 100, 100)
        cv2.putText(frame, f"Raw: {raw_state.value} ({confidence*100:.1f}%)",
                    (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, debug_color, 1)

        # Buffer contents
        if state_buffer:
            buf_str = " ".join(s.value[:3] for s in state_buffer)
            cv2.putText(frame, f"Buffer: [{buf_str}]",
                        (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)

        cv2.putText(frame, "ESC to quit",
                    (w - 200, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        cv2.imshow(self._name, frame)

    def should_quit(self) -> bool:
        """Returns True if the user pressed ESC."""
        return (cv2.waitKey(1) & 0xFF) == 27

    def close(self) -> None:
        cv2.destroyAllWindows()