from __future__ import annotations
import threading
import cv2
import numpy as np
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QWidget, QFrame,
)
from app.config import AppConfig

try:
    from ui.components.theme import TEXT_HIGH, TEXT_MED, TEXT_LOW, BASE_STYLE
except ImportError:
    TEXT_HIGH  = "rgba(255,255,255,0.90)"
    TEXT_MED   = "rgba(255,255,255,0.60)"
    TEXT_LOW   = "rgba(255,255,255,0.35)"
    BASE_STYLE = ""


# ── Camera detection worker (QThread so it never blocks the UI) ───────────────

class _DetectThread(QThread):
    """
    Probes camera indices 0-7 using CAP_DSHOW (Windows-fast).
    Emits results as soon as each camera responds — no waiting for stragglers.
    """
    camera_found    = pyqtSignal(int, str)   # index, name
    detection_done  = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._names: list[str] = []

    def run(self) -> None:
        # Try to get friendly names via pygrabber (optional)
        try:
            from pygrabber.dshow_graph import FilterGraph
            self._names = FilterGraph().get_input_devices()
        except Exception:
            self._names = []

        results: dict[int, str] = {}
        lock = threading.Lock()

        def probe(i: int) -> None:
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            opened = cap.isOpened()
            cap.release()
            if opened:
                name = self._names[i] if i < len(self._names) else f"Camera {i}"
                with lock:
                    results[i] = name
                # Emit immediately so UI updates as cameras are found
                self.camera_found.emit(i, name)

        threads = [
            threading.Thread(target=probe, args=(i,), daemon=True)
            for i in range(8)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=2.0)

        self.detection_done.emit()


# ── helpers ───────────────────────────────────────────────────────────────────

def _sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet("background:rgba(255,255,255,0.07);border:none;max-height:1px;")
    return f


# ── Settings window ───────────────────────────────────────────────────────────

class SettingsWindow(QDialog):
    """
    Native-frame window (movable, resizable title bar).
    Fast parallel camera detection via CAP_DSHOW.
    Stops the main CameraWorker preview while this window is open,
    then signals back so TrayApp can restart it.
    """
    camera_selected  = pyqtSignal(int)   # user picked a different camera
    preview_released = pyqtSignal()      # emitted on close so worker can restart

    def __init__(self, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self._config  = config
        self._current = config.camera_device

        self._cameras:     dict[int, str]      = {}   # index → name
        self._cam_buttons: dict[int, QPushButton] = {}
        self._cam_cap:     cv2.VideoCapture | None = None
        self._expanded     = False
        self._saved        = False
        self._detect_thread: _DetectThread | None = None

        self._preview_timer = QTimer(self)
        self._preview_timer.timeout.connect(self._update_preview)

        # ── window flags: real native title bar ──────────────────────────────
        self.setWindowTitle("Settings — GestureKey")
        self.setFixedWidth(340)
        self.setMinimumHeight(100)
        self.setModal(False)
        # Keep on top but with a real frame the user can drag
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowTitleHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

        if BASE_STYLE:
            self.setStyleSheet(BASE_STYLE)
        self.setStyleSheet(self.styleSheet() + """
            QDialog {
                background: #141414;
                color: rgba(255,255,255,0.80);
            }
        """)

        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        # Section label
        lbl = QLabel("CAMERA")
        lbl.setStyleSheet(
            f"color:{TEXT_LOW};font-size:9px;font-weight:600;letter-spacing:2px;"
        )
        lay.addWidget(lbl)

        # Preview
        self._preview_lbl = QLabel("Detecting cameras…")
        self._preview_lbl.setFixedHeight(170)
        self._preview_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_lbl.setStyleSheet(
            "background:#000;border-radius:8px;"
            "color:rgba(255,255,255,0.30);font-size:10px;"
        )
        lay.addWidget(self._preview_lbl)

        # Trigger button (collapsed dropdown)
        self._trigger_btn = QPushButton("Detecting cameras…")
        self._trigger_btn.setEnabled(False)
        self._trigger_btn.setStyleSheet(self._trigger_style())
        self._trigger_btn.clicked.connect(self._toggle_expand)
        lay.addWidget(self._trigger_btn)

        # Camera list container (hidden until expanded)
        self._list_widget = QWidget()
        self._list_widget.setStyleSheet("background:transparent;")
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(2)
        self._list_widget.hide()
        lay.addWidget(self._list_widget)

        lay.addWidget(_sep())

        # Set as default button
        self._default_btn = QPushButton("Set as default")
        self._default_btn.setStyleSheet(self._default_btn_style(False))
        self._default_btn.clicked.connect(self._set_default)
        lay.addWidget(self._default_btn)

    # ── styles ────────────────────────────────────────────────────────────────

    def _trigger_style(self) -> str:
        return """
            QPushButton {
                background: rgba(255,255,255,0.05);
                color: rgba(255,255,255,0.55);
                border: none; border-radius: 8px;
                padding: 8px 12px; text-align: left; font-size: 10px;
            }
            QPushButton:hover  { background: rgba(255,255,255,0.09); }
            QPushButton:disabled { color: rgba(255,255,255,0.25); }
        """

    def _cam_btn_style(self, active: bool) -> str:
        bg    = "rgba(255,255,255,0.10)" if active else "transparent"
        color = TEXT_HIGH if active else TEXT_LOW
        return f"""
            QPushButton {{
                background:{bg}; color:{color};
                border:none; border-radius:6px;
                padding:7px 12px; text-align:left; font-size:10px;
            }}
            QPushButton:hover {{ background:rgba(255,255,255,0.08); color:{TEXT_HIGH}; }}
        """

    def _default_btn_style(self, saved: bool) -> str:
        if saved:
            return """
                QPushButton {
                    background: rgba(52,211,153,0.15); color: #34d399;
                    border: 1px solid rgba(52,211,153,0.20);
                    border-radius: 8px; padding: 8px;
                    font-size: 10px; font-weight: 500;
                }
            """
        return """
            QPushButton {
                background: rgba(255,255,255,0.05);
                color: rgba(255,255,255,0.50);
                border: 1px solid rgba(255,255,255,0.05);
                border-radius: 8px; padding: 8px;
                font-size: 10px; font-weight: 500;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.10);
                color: rgba(255,255,255,0.70);
            }
        """

    # ── show / hide ───────────────────────────────────────────────────────────

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Reset list in case cameras changed since last open
        self._clear_camera_list()
        self._cameras.clear()
        self._trigger_btn.setEnabled(False)
        self._trigger_btn.setText("Detecting cameras…")
        self._preview_lbl.setText("Detecting cameras…")
        self._preview_lbl.setPixmap(QPixmap())  # clear old frame
        self._start_detection()

    def closeEvent(self, event) -> None:
        self._stop_preview()
        if self._detect_thread and self._detect_thread.isRunning():
            self._detect_thread.quit()
            self._detect_thread.wait(1000)
        self.preview_released.emit()
        super().closeEvent(event)

    # ── detection ─────────────────────────────────────────────────────────────

    def _start_detection(self) -> None:
        self._detect_thread = _DetectThread(self)
        self._detect_thread.camera_found.connect(self._on_camera_found)
        self._detect_thread.detection_done.connect(self._on_detection_done)
        self._detect_thread.start()

    @pyqtSlot(int, str)
    def _on_camera_found(self, index: int, name: str) -> None:
        """Called for each camera as soon as it's detected (fast feedback)."""
        self._cameras[index] = name

        btn = QPushButton(name)
        is_active = (index == self._current)
        btn.setStyleSheet(self._cam_btn_style(is_active))
        btn.clicked.connect(lambda _, i=index: self._select_camera(i))
        self._list_layout.addWidget(btn)
        self._cam_buttons[index] = btn

        # Update trigger to show first found camera immediately
        if len(self._cameras) == 1 or index == self._current:
            display = self._cameras.get(self._current, name)
            self._trigger_btn.setText(display + " ▼")
            self._trigger_btn.setEnabled(True)

        # Start preview on the current (or first found) camera
        if index == self._current:
            self._start_preview(index)
        elif len(self._cameras) == 1:
            # current not found yet, preview the first available
            self._start_preview(index)

    @pyqtSlot()
    def _on_detection_done(self) -> None:
        if not self._cameras:
            self._trigger_btn.setText("No cameras found")
            self._preview_lbl.setText("No cameras detected")
            return

        # Make sure trigger shows the correct current camera
        name = self._cameras.get(self._current,
               self._cameras[min(self._cameras)])
        self._trigger_btn.setText(name + " ▼")
        self._trigger_btn.setEnabled(True)

        # Refresh button highlight (current might have been found late)
        for idx, btn in self._cam_buttons.items():
            btn.setStyleSheet(self._cam_btn_style(idx == self._current))

    # ── camera list UI ────────────────────────────────────────────────────────

    def _clear_camera_list(self) -> None:
        for i in reversed(range(self._list_layout.count())):
            w = self._list_layout.itemAt(i).widget()
            if w:
                w.deleteLater()
        self._cam_buttons.clear()

    def _toggle_expand(self) -> None:
        if not self._cameras:
            return
        self._expanded = not self._expanded
        self._list_widget.setVisible(self._expanded)
        name = self._trigger_btn.text().rstrip("▲▼").strip()
        self._trigger_btn.setText(name + (" ▲" if self._expanded else " ▼"))
        self.adjustSize()

    def _select_camera(self, index: int) -> None:
        self._current = index
        name = self._cameras.get(index, f"Camera {index}")

        # Collapse list
        self._expanded = False
        self._list_widget.hide()
        self._trigger_btn.setText(name + " ▼")
        self.adjustSize()

        # Refresh highlights
        for idx, btn in self._cam_buttons.items():
            btn.setStyleSheet(self._cam_btn_style(idx == index))

        self._start_preview(index)
        self.camera_selected.emit(index)

        # Reset saved state
        self._saved = False
        self._default_btn.setText("Set as default")
        self._default_btn.setStyleSheet(self._default_btn_style(False))

    # ── preview ───────────────────────────────────────────────────────────────

    def _start_preview(self, index: int) -> None:
        self._stop_preview()
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if cap.isOpened():
            self._cam_cap = cap
            self._preview_lbl.setText("")
            self._preview_timer.start(33)
        else:
            cap.release()
            self._preview_lbl.setText(f"Cannot open camera {index}")

    def _stop_preview(self) -> None:
        self._preview_timer.stop()
        if self._cam_cap is not None:
            self._cam_cap.release()
            self._cam_cap = None

    def _update_preview(self) -> None:
        if self._cam_cap is None:
            return
        ret, frame = self._cam_cap.read()
        if not ret:
            return
        frame     = cv2.flip(frame, 1)
        rgb       = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch  = rgb.shape
        img = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(img).scaled(
            self._preview_lbl.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._preview_lbl.setPixmap(pix)

    # ── save default ──────────────────────────────────────────────────────────

    def _set_default(self) -> None:
        import re, pathlib
        config_path = pathlib.Path(__file__).parent.parent / "app" / "config.py"
        try:
            text = config_path.read_text(encoding="utf-8")
            text = re.sub(
                r"(camera_device\s*:\s*int\s*=\s*)\d+",
                lambda m: f"{m.group(1)}{self._current}",
                text,
            )
            config_path.write_text(text, encoding="utf-8")
            self._saved = True
            self._default_btn.setText("✓ Saved as default")
            self._default_btn.setStyleSheet(self._default_btn_style(True))
            QTimer.singleShot(2000, lambda: (
                self._default_btn.setText("Set as default"),
                self._default_btn.setStyleSheet(self._default_btn_style(False)),
            ))
        except Exception as e:
            print(f"[Settings] Error saving default: {e}")