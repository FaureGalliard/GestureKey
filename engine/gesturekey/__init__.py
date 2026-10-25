"""GestureKey engine."""
import os

# Must be set before OpenCV's MSMF backend is first used (see vision/camera.py).
os.environ.setdefault("OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS", "0")

__version__ = "3.0.0-beta.1"
